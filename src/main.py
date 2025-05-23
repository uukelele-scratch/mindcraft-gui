import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mindcraft")
        self.setGeometry(100, 100, 800, 600)

        self.widget = QWidget()
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        if not os.path.exists(os.path.join(os.path.dirname(sys.executable), "config.json")): # No config = Initial run
            print("[ WARN ] Config file does not exist. Initial run detected. Launching installer...")
            from installer import Installer
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.installer = Installer(self)
            self.hide()
            self.installer.show()
        else:
            self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    window = MainWindow()
    sys.exit(app.exec_())