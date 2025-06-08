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
    QLabel,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import json
from datetime import datetime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("mindcraft-ce")
        self.setGeometry(100, 100, 800, 600)

        self.widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.widget.setLayout(self.main_layout)
        self.setCentralWidget(self.widget)

        config_path = os.path.join(os.path.dirname(sys.executable), "config.json")

        if not os.path.exists(config_path): # No config = Initial run
            print("[ WARN ] Config file does not exist. Initial run detected. Launching installer...")
            from installer import Installer
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.installer = Installer(self)
            self.hide()
            self.installer.show()
            return


        print("[ INFO ] Config file found. Initializing main application UI.")
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.details_layout = QHBoxLayout()

        self.creation_time_label = QLabel("This installation was installed on " + datetime.fromtimestamp(self.config["installed_time"]).strftime('%Y-%m-%d %H:%M:%S'))
        self.details_layout.addWidget(self.creation_time_label)

        self.main_layout.addLayout(self.details_layout, stretch=1)
        self.main_layout.addStretch(10)  # Push everything else downward



        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    window = MainWindow()
    sys.exit(app.exec_())