# classifier_manager.py
import os
import time
import json
import torch
import timm
import safetensors.torch
from PIL import Image
from timm.models import VisionTransformer # Explicit import for type hinting
from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool

# Import the transformation function
from transformations import get_transform

class ClassifierManager(QObject):
    analysis_started = Signal()
    analysis_finished = Signal(list) # Will emit list of (tag, score) tuples
    error_occurred = Signal(str)


    def __init__(self, model_id="vit_so400m", use_gpu=True, parent=None): # Added use_gpu flag
        """
        Initializes the ClassifierManager.

        Args:
            model_id (str): Identifier for the model to load (maps to folder name).
            use_gpu (bool): Flag to attempt using GPU if available.
            parent (QObject): Parent QObject for signal-slot connections.
        """
        super().__init__(parent)
        self.model_id = model_id
        self.use_gpu_preference = use_gpu
        self.device = None # Will be set during model load

        # Construct paths based on model_id
        base_path = os.path.dirname(__file__) # Gets directory of classifier_manager.py
        model_dir = os.path.join(base_path, "classifiers", self.model_id)
        # --- TODO: Adjust model filename if needed ---
        self.model_path = os.path.join(model_dir, "JTP_PILOT-e4-vit_so400m_patch14_siglip_384.safetensors")
        self.tags_path = os.path.join(model_dir, "tags.json")
        # ---

        self.model: VisionTransformer | None = None # Type hint for the model
        self.allowed_tags: list[str] | None = None
        self.transform = get_transform() # Get the transformation pipeline

        self.thread_pool = QThreadPool.globalInstance()
        print(f"Using thread pool with max threads: {self.thread_pool.maxThreadCount()}")

        print(f"ClassifierManager initialized for model '{model_id}'.")
        print(f" - Model path: {self.model_path}")
        print(f" - Tags path: {self.tags_path}")

    def _ensure_loaded(self):
        """Loads model and tags if they haven't been loaded yet."""
        if self.model is None or self.allowed_tags is None:
            print("Model and/or tags not loaded. Loading now...")
            self._load_model_and_tags()
        # else:
            # print("Model and tags already loaded.") # Optional debug

    def _load_model_and_tags(self):
        """Loads the model and associated tags file."""
        load_start_time = time.time()
        print(f"Starting model and tag loading...")

        # --- Determine Device ---
        if self.use_gpu_preference and torch.cuda.is_available():
            self.device = torch.device("cuda")
            print("CUDA (GPU) is available and selected.")
        else:
            self.device = torch.device("cpu")
            if self.use_gpu_preference:
                print("CUDA (GPU) not available or not selected, using CPU.")
            else:
                print("CPU selected.")

        # --- Load Tags ---
        try:
            with open(self.tags_path, "r", encoding='utf-8') as f:
                tags_data: dict[str, int] = json.load(f)
                self.allowed_tags = list(tags_data.keys()) # Store the list of tag names
                print(f"Loaded {len(self.allowed_tags)} tags from {self.tags_path}")
        except FileNotFoundError:
            print(f"ERROR: Tags file not found at {self.tags_path}")
            # Handle error appropriately - maybe raise exception?
            self.allowed_tags = None
            return # Stop loading if tags are missing
        except Exception as e:
            print(f"ERROR loading tags.json: {e}")
            self.allowed_tags = None
            return

        # --- Load Model ---
        try:
            print("Creating ViT model structure...")
            # Explicitly match the structure from BatchTagger.py
            self.model = timm.create_model(
                "vit_so400m_patch14_siglip_384.webli", # Make sure this matches BatchTagger
                pretrained=False,
                num_classes=len(self.allowed_tags), # Set num_classes based on loaded tags
            )
            print(f"Loading model weights from {self.model_path}...")
            state_dict = safetensors.torch.load_file(self.model_path, device=str(self.device)) # Load directly to device if possible
            self.model.load_state_dict(state_dict)
            self.model.eval() # Set to evaluation mode
            self.model.to(self.device) # Ensure model is on the correct device
            print(f"Model loaded successfully to {self.device}.")

            # Apply performance optimizations if applicable
            if self.device.type == 'cuda' and torch.cuda.get_device_capability()[0] >= 7:
                self.model.to(dtype=torch.float16) # Use float16
                print("Applied float16 optimization.")
            # Note: channels_last is often handled automatically or less critical for inference speed compared to FP16

        except FileNotFoundError:
            print(f"ERROR: Model file not found at {self.model_path}")
            self.model = None # Ensure model is None on error
            # Also invalidate tags? Or keep them loaded? Let's invalidate for safety.
            self.allowed_tags = None
            return
        except Exception as e:
            print(f"ERROR loading model: {e}")
            self.model = None
            self.allowed_tags = None
            return

        load_end_time = time.time()
        print(f"Model and tags loaded in {load_end_time - load_start_time:.2f} seconds.")

    # --- Synchronous analysis method for testing Phase 1 ---
    def request_analysis(self, image_path: str):
        """
        Requests ASYNCHRONOUS image analysis.
        Performs preprocessing on main thread, dispatches inference/postprocessing
        to a background thread. Emits signals for results/errors.

        Args:
            image_path (str): Path to the image file.
        """
        print(f"\n--- Requesting Asynchronous Analysis for: {os.path.basename(image_path)} ---")
        self._ensure_loaded() # Make sure model and tags are loaded

        if self.model is None or self.allowed_tags is None:
            error_msg = "Cannot analyze, model or tags failed to load."
            print(f"ERROR: {error_msg}")
            self.error_occurred.emit(error_msg) # Emit error signal
            return

        try:
            # --- Preprocessing (on main thread) ---
            print("MainThread: Loading and preprocessing image...")
            start_preprocess = time.time()
            image = Image.open(image_path).convert("RGBA")
            tensor = self.transform(image)
            # Add batch dimension and move to device
            tensor = tensor.unsqueeze(0).to(self.device)

            # Apply dtype optimization if needed
            if self.device.type == 'cuda' and torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 7:
                try:
                    model_dtype = next(self.model.parameters()).dtype
                    if model_dtype == torch.float16:
                        print("MainThread: Converting input tensor to float16...")
                        tensor = tensor.to(dtype=torch.float16)
                except StopIteration:
                    print("Warning: Could not determine model parameter dtype.")
            end_preprocess = time.time()
            print(f"MainThread: Preprocessing took {end_preprocess - start_preprocess:.3f} seconds.")

            # --- Dispatch Worker ---
            print("MainThread: Dispatching worker to thread pool...")
            # Create worker instance - pass necessary data
            # TODO: Make threshold configurable later
            worker = AnalysisWorker(
                image_tensor=tensor,
                model=self.model,
                device=self.device, # Pass device just in case, though maybe not needed
                allowed_tags=self.allowed_tags,
                threshold=0.3 # Hardcoded threshold for now
            )

            # Connect worker signals to manager's SLOTS (methods)
            # These slots will then emit the manager's SIGNALS
            worker.signals.finished.connect(self._handle_worker_result)
            worker.signals.error.connect(self._handle_worker_error)

            # Emit the analysis_started signal *before* starting the thread
            self.analysis_started.emit()
            print("MainThread: Emitted analysis_started signal.")

            # Start the worker
            self.thread_pool.start(worker)
            print("MainThread: Worker started.")

        except FileNotFoundError:
            error_msg = f"Image file not found at {image_path}"
            print(f"ERROR: {error_msg}")
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_msg = f"ERROR during preprocessing or dispatch: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)

    # --- Slots to receive results from worker ---
    @Slot(list)
    def _handle_worker_result(self, results):
        print("MainThread: Received analysis_finished signal from worker.")
        self.analysis_finished.emit(results) # Relay the signal

    @Slot(str)
    def _handle_worker_error(self, error_message):
        print(f"MainThread: Received error signal from worker: {error_message}")
        self.error_occurred.emit(error_message) # Relay the signal

# --- Helper Class for Signals from Worker Thread ---
class WorkerSignals(QObject):
    finished = Signal(list) # Emits list of (tag, score)
    error = Signal(str)


# --- Analysis Worker (Runs on Background Thread) ---
class AnalysisWorker(QRunnable):
    def __init__(self, image_tensor, model, device, allowed_tags, threshold):
        super().__init__()
        self.signals = WorkerSignals()
        self.tensor = image_tensor # Preprocessed tensor (already on correct device & dtype)
        self.model = model
        self.device = device # Needed? Tensor is already on device. Model too. Maybe not needed here.
        self.allowed_tags = allowed_tags
        self.threshold = threshold # Set the threshold (e.g., 0.3)

    @Slot() # Decorator indicating this is the entry point for the runnable
    def run(self):
        try:
            # --- Inference (already done in background thread) ---
            print("Worker: Running inference...")
            start_inference = time.time()
            with torch.no_grad():
                # Model expects batch dimension, tensor should already have it
                logits = self.model(self.tensor)
            end_inference = time.time()
            print(f"Worker: Inference took {end_inference - start_inference:.3f} seconds.")

            # --- Post-processing ---
            print("Worker: Post-processing results...")
            # 1. Apply Sigmoid (get probabilities 0-1)
            probabilities = torch.nn.functional.sigmoid(logits[0]) # Remove batch dim

            # 2. Thresholding (find indices above threshold)
            # Move probabilities to CPU for numpy operations if needed, or keep on GPU
            probabilities_cpu = probabilities.cpu() # Move to CPU for thresholding/indexing
            indices = torch.where(probabilities_cpu > self.threshold)[0]
            values = probabilities_cpu[indices] # Get corresponding scores

            # 3. Map indices to tags and store scores
            results = []
            for i in range(indices.size(0)):
                tag_index = indices[i].item()
                if 0 <= tag_index < len(self.allowed_tags):
                    tag_name = self.allowed_tags[tag_index]
                    score = values[i].item()
                    results.append((tag_name, score))
                else:
                    print(f"Warning: Index {tag_index} out of bounds for allowed_tags.")


            # 4. Sort by score (descending)
            results.sort(key=lambda x: x[1], reverse=True)

            print(f"Worker: Found {len(results)} tags above threshold {self.threshold}.")
            # 5. Emit results
            self.signals.finished.emit(results)

        except Exception as e:
            print(f"Worker: ERROR during analysis - {e}")
            import traceback
            traceback.print_exc() # Print detailed traceback
            self.signals.error.emit(str(e))