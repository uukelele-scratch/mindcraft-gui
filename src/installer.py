import sys, os, time


from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QFrame,
    QMessageBox,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from utils import set_font_size


class InstallerWorker(QObject):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def run(self):
        self.log.emit("Installation Started")
        time.sleep(1)
        for i in range(5):
            time.sleep(1)
            self.log.emit(f"sleep completed ({i})")
        self.log.emit("Installation Finished")
        self.finished.emit()

class Installer(QMainWindow):
    def __init__(self, parentWindow):
        super().__init__()

        self.parentWindow = parentWindow

        self.setWindowTitle("Mindcraft Installer")
        self.setGeometry(100, 100, 800, 600)

        self.widget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(20)
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        self.header = QWidget()
        self.headerLayout = QVBoxLayout()
        self.headerLayout.setContentsMargins(0, 0, 0, 0)
        self.headerLayout.setSpacing(5)
        self.header.setLayout(self.headerLayout)
        self.layout.addWidget(self.header, stretch=3)
        self.header.setMaximumHeight(100)

        self.title = QLabel("Welcome to the Mindcraft Installer!")
        set_font_size(self.title, 24)
        self.subtitle = QLabel("You're seeing this because this is the first time you're opening the Mindcraft Launcher.")
        set_font_size(self.subtitle, 12)
        self.headerLayout.addWidget(self.title)
        self.headerLayout.addWidget(self.subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.body = QWidget()
        self.bodyLayout = QVBoxLayout()
        self.bodyLayout.setContentsMargins(0, 0, 0, 0)
        self.bodyLayout.setSpacing(10)
        self.body.setLayout(self.bodyLayout)
        self.layout.addWidget(self.body, stretch=7)

        self.progressLabel = QLabel("Installation Details")
        set_font_size(self.progressLabel, 16)
        self.bodyLayout.addWidget(self.progressLabel)

        self.detailLabel = QLabel("Mindcraft Launcher will install to the following path:<br><br>"
                             f"<code>{os.path.dirname(sys.executable)}</code>"
                             "<br><br>This path can't be changed - it's the path that was set up from part 1 of the installer."
                             "<br>Not happy? Close this app, then rerun the original installer."
                            )
        self.detailLabel.setTextFormat(Qt.RichText)
        set_font_size(self.detailLabel, 12)
        self.bodyLayout.addWidget(self.detailLabel)

        self.navigationWidget = QWidget()
        self.navigationLayout = QHBoxLayout()
        self.navigationWidget.setLayout(self.navigationLayout)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setFixedWidth(200)
        self.installButton = QPushButton("Install")
        self.installButton.clicked.connect(self.begin_installation)
        self.installButton.setFixedWidth(200)
        self.navigationLayout.addWidget(self.cancelButton)
        self.navigationLayout.addWidget(self.installButton)

        self.navigationLine = QFrame()
        self.navigationLine.setFrameShape(QFrame.HLine)
        self.navigationLine.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(self.navigationLine)

        self.layout.addWidget(self.navigationWidget)

    def logMessage(self, message: str):
        currentText = self.logText.toMarkdown()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.logText.setMarkdown(f"{currentText}\n**[{timestamp}]**: {message}")

    def begin_installation(self):
        self.cancelButton.setEnabled(False)
        self.installButton.setEnabled(False)
        self.installButton.setText("Finish")
        self.installButton.clicked.disconnect(self.begin_installation)
        self.installButton.clicked.connect(self.finish_installation)
        self.title.setText("Installing...")
        self.subtitle.setText("Please wait.")
        self.progressLabel.setText("Progress")
        self.detailLabel.hide()
        self.logText = QTextEdit()
        self.logText.acceptRichText()
        self.logText.setReadOnly(True)
        self.bodyLayout.addWidget(self.logText)

        self.worker = InstallerWorker()
        self.thread_ = QThread()
        self.worker.moveToThread(self.thread_)
        self.worker.log.connect(self.logMessage)
        self.worker.finished.connect(self.thread_.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.thread_.deleteLater)
        self.worker.finished.connect(lambda: self.installButton.setEnabled(True))
        self.thread_.started.connect(self.worker.run)
        self.thread_.start()

    def finish_installation(self):
        box = QMessageBox()
        box.setText("Installation has finished. Restart the Mindcraft Launcher to continue.")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()
        self.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Installer()
    window.show()
    sys.exit(app.exec_())