from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

TAG_CATEGORY_COLORS = {
    "0": "#b4c7d9",  # General
    "1": "#f2ac08",  # Artist
    "2": "#c0c0c0",  # Contributor (silver)
    "3": "#d000d0",  # Copyright
    "4": "#00aa00",  # Character
    "5": "#ed5d1f",  # Species
    "6": "#ff3d3d",  # Invalid
    "7": "#ffffff",  # Meta
    "8": "#282",    # Lore
    "9": "#555555"   # New/Unknown category
}

def setup_dark_mode(app):
    """Sets up the application-wide dark mode theme."""
    app.setStyle("Fusion")  # Use the Fusion style for a consistent look.
    dark_palette = QPalette()
    dark_color = QColor(53, 53, 53)
    dark_disabled_color = QColor(127, 127, 127)
    dark_palette.setColor(QPalette.Window, dark_color)
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, dark_color)
    dark_palette.setColor(QPalette.ToolTipBase, Qt.lightGray)
    dark_palette.setColor(QPalette.ToolTipText, Qt.black)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, dark_disabled_color)
    dark_palette.setColor(QPalette.Dark, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    dark_palette.setColor(QPalette.Button, dark_color)
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, dark_disabled_color)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Disabled, QPalette.Highlight, dark_disabled_color)
    dark_palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(dark_palette)