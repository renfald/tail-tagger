from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox
from PySide6.QtCore import Qt, QRunnable, QThreadPool, Signal, QObject


class WorkerSignals(QObject):
    """Signals for the bulk operation worker thread."""
    progress = Signal(str, int, int, str)  # phase, current, total, message
    finished = Signal(dict)  # results
    error = Signal(str)  # error message


class BulkOperationWorker(QRunnable):
    """Worker thread for executing bulk operations."""

    def __init__(self, operation_func, *args, **kwargs):
        """Initialize the worker.

        Args:
            operation_func: The bulk operation function to run
            *args, **kwargs: Arguments to pass to the operation function
        """
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """Execute the bulk operation."""
        try:
            # Add progress callback to kwargs
            self.kwargs['progress_callback'] = self._progress_callback

            # Execute the operation
            result = self.operation_func(*self.args, **self.kwargs)

            # Emit completion
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

    def _progress_callback(self, phase, current, total, message):
        """Callback for progress updates."""
        self.signals.progress.emit(phase, current, total, message)


class BulkOperationDialog(QDialog):
    """Dialog that shows progress during bulk tag operations."""

    def __init__(self, parent, operation_type, tag_name, position=None):
        """Initialize the bulk operation dialog.

        Args:
            parent: Parent widget
            operation_type (str): 'add_front', 'add_end', or 'remove'
            tag_name (str): Name of the tag being operated on
            position (str, optional): 'front' or 'end' for add operations
        """
        super().__init__(parent)
        self.operation_type = operation_type
        self.tag_name = tag_name
        self.position = position
        self.result = None

        self._setup_ui()
        self.setModal(True)

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Bulk Operation")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Operation description
        operation_desc = self._get_operation_description()
        self.desc_label = QLabel(operation_desc)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # Status message
        self.status_label = QLabel("Preparing...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Details label (shows current/total)
        self.details_label = QLabel("")
        self.details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.details_label)

        self.setLayout(layout)

    def _get_operation_description(self):
        """Get a human-readable description of the operation."""
        tag_display = self.tag_name.replace('_', ' ')

        if self.operation_type == 'add_front':
            return f"Adding tag '{tag_display}' to the beginning of all images..."
        elif self.operation_type == 'add_end':
            return f"Adding tag '{tag_display}' to the end of all images..."
        elif self.operation_type == 'remove':
            return f"Removing tag '{tag_display}' from all images..."
        else:
            return "Processing..."

    def execute_operation(self, bulk_manager, folder_path):
        """Execute the bulk operation.

        Args:
            bulk_manager (BulkOperationsManager): Manager to perform the operation
            folder_path (str): Path to the image folder

        Returns:
            dict: Operation results
        """
        # Determine which operation to run
        if self.operation_type == 'add_front':
            operation_func = bulk_manager.add_tag_to_all
            args = (folder_path, self.tag_name, 'front')
        elif self.operation_type == 'add_end':
            operation_func = bulk_manager.add_tag_to_all
            args = (folder_path, self.tag_name, 'end')
        elif self.operation_type == 'remove':
            operation_func = bulk_manager.remove_tag_from_all
            args = (folder_path, self.tag_name)
        else:
            return {'success': False, 'error': 'Unknown operation type'}

        # Create and configure worker
        worker = BulkOperationWorker(operation_func, *args)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)

        # Start the worker
        QThreadPool.globalInstance().start(worker)

        # Show dialog and wait for completion
        self.exec()

        return self.result

    def _on_progress(self, phase, current, total, message):
        """Handle progress updates.

        Args:
            phase (str): 'init' or 'process'
            current (int): Current progress
            total (int): Total items
            message (str): Status message
        """
        self.status_label.setText(message)

        if total > 0:
            progress_percent = int((current / total) * 100)
            self.progress_bar.setValue(progress_percent)
            self.details_label.setText(f"{current} / {total}")
        else:
            self.progress_bar.setValue(0)
            self.details_label.setText("")

    def _on_finished(self, result):
        """Handle operation completion.

        Args:
            result (dict): Operation results
        """
        self.result = result
        self.close()

        # Show results dialog
        if result.get('success'):
            self._show_success_message(result)
        else:
            self._show_error_message(result.get('error', 'Unknown error'))

    def _on_error(self, error_msg):
        """Handle operation error.

        Args:
            error_msg (str): Error message
        """
        self.result = {'success': False, 'error': error_msg}
        self.close()
        self._show_error_message(error_msg)

    def _show_success_message(self, result):
        """Show success message with results.

        Args:
            result (dict): Operation results
        """
        tag_display = self.tag_name.replace('_', ' ')

        if self.operation_type in ['add_front', 'add_end']:
            added = result.get('added_count', 0)
            moved = result.get('moved_count', 0)
            total = result.get('total_images', 0)

            position = "beginning" if self.operation_type == 'add_front' else "end"

            message = f"Tag '{tag_display}' added to {position} of all images.\n\n"
            message += f"Total images: {total}\n"
            message += f"Newly added: {added}\n"
            message += f"Moved to {position}: {moved}"

        elif self.operation_type == 'remove':
            removed = result.get('removed_count', 0)
            total = result.get('total_images', 0)

            message = f"Tag '{tag_display}' removed from all images.\n\n"
            message += f"Total images: {total}\n"
            message += f"Removed from: {removed} images"
        else:
            message = "Operation completed successfully."

        QMessageBox.information(self, "Bulk Operation Complete", message)

    def _show_error_message(self, error_msg):
        """Show error message.

        Args:
            error_msg (str): Error message
        """
        QMessageBox.critical(
            self,
            "Bulk Operation Failed",
            f"An error occurred during the bulk operation:\n\n{error_msg}"
        )
