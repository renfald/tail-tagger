# keyboard_manager.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit

class KeyboardManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def handle_key_press(self, event, source_widget):
        """Central handler for all key events.

        Args:
            event (QKeyEvent): The key event.
            source_widget (QWidget): The widget that received the key event.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        # Skip handling if focus is in a text input field (QLineEdit or its subclass)
        if isinstance(QApplication.focusWidget(), QLineEdit):
            return False  # Do not handle, let text input handle it

        if event.key() == Qt.Key_Left:
            self.main_window._prev_image()
            return True  # Event handled
        elif event.key() == Qt.Key_Right:
            self.main_window._next_image()
            return True  # Event handled

        # Future: Add panel-specific handling here if needed based on source_widget
        return False  # Event not handled