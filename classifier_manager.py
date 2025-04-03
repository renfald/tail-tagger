# classifier_manager.py
import os
import time
import json
import torch
import timm
import safetensors.torch
from PIL import Image
from timm.models import VisionTransformer # Explicit import for type hinting

# Import the transformation function
from transformations import get_transform

class ClassifierManager:
    def __init__(self, model_id="vit_so400m", use_gpu=True): # Added use_gpu flag
        """
        Initializes the ClassifierManager.

        Args:
            model_id (str): Identifier for the model to load (maps to folder name).
            use_gpu (bool): Flag to attempt using GPU if available.
        """
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
    def analyze_image_sync(self, image_path: str):
        """
        Performs SYNCHRONOUS image analysis (for testing purposes).
        Loads model/tags if needed, preprocesses, runs inference.

        Args:
            image_path (str): Path to the image file.

        Returns:
            torch.Tensor | None: Raw logits tensor if successful, None otherwise.
        """
        print(f"\n--- Starting Synchronous Analysis for: {os.path.basename(image_path)} ---")
        self._ensure_loaded() # Make sure model and tags are loaded

        if self.model is None or self.allowed_tags is None:
            print("ERROR: Cannot analyze, model or tags failed to load.")
            return None

        try:
            # --- Preprocessing ---
            print("Loading and preprocessing image...")
            start_preprocess = time.time()
            # Match ImageDataset logic: Load -> RGBA -> Transform
            image = Image.open(image_path).convert("RGBA")
            tensor = self.transform(image)
            # Add batch dimension and move to device
            tensor = tensor.unsqueeze(0).to(self.device)

            # Apply dtype optimization if needed (matching model's dtype)
            if self.device.type == 'cuda' and torch.cuda.get_device_capability()[0] >= 7:
                try:
                    # Get the dtype of the first parameter (assuming all parameters are the same type)
                    model_dtype = next(self.model.parameters()).dtype
                    if model_dtype == torch.float16:
                        print("Model is float16, converting input tensor...") # Add print for confirmation
                        tensor = tensor.to(dtype=torch.float16)
                    # else: # Optional: print if model is not float16
                    #    print(f"Model dtype is {model_dtype}, tensor remains unchanged.")
                except StopIteration:
                    # Handle case where model has no parameters (shouldn't happen here)
                    print("Warning: Could not determine model parameter dtype.")

            end_preprocess = time.time()
            print(f"Preprocessing took {end_preprocess - start_preprocess:.3f} seconds.")

            # --- Inference ---
            print("Running inference...")
            start_inference = time.time()
            with torch.no_grad(): # Ensure gradients are off
                logits = self.model(tensor)
            end_inference = time.time()
            print(f"Inference took {end_inference - start_inference:.3f} seconds.")
            print(f"Output logits shape: {logits.shape}")
            print(f"Output logits sample (first 5): {logits[0, :5]}") # Print sample output

            return logits # Return raw logits for this phase

        except FileNotFoundError:
            print(f"ERROR: Image file not found at {image_path}")
            return None
        except Exception as e:
            print(f"ERROR during image analysis: {e}")
            return None
        finally:
            print("--- Synchronous Analysis Complete ---")