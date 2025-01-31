import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QHBoxLayout, QFrame)
from PySide6.QtGui import QPalette, QColor

class Color(QWidget):  # Just a simple widget to show color
    def __init__(self, color):
        super().__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tagger")  # Set window title

        central_widget = QWidget()  # Create a central widget to hold everything
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()  # Horizontal layout for panels
        central_widget.setLayout(layout)

        left_panel = Color("lightskyblue")  # Placeholder left panel
        center_panel = Color("lightcoral")   # Placeholder center panel
        right_panel = Color("lightgreen")  # Placeholder right panel

        layout.addWidget(left_panel)
        layout.addWidget(center_panel)
        layout.addWidget(right_panel)

app = QApplication(sys.argv)  # Create the application instance
window = MainWindow()         # Create our main window
window.show()                # Show the window
app.exec()                   # Run the event loop (application starts)