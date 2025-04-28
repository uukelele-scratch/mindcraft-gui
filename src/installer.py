import sys, os, time
import zipfile
import shutil
import traceback # For detailed error logging
import json

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

from utils import set_font_size, run_command, is_tool_installed, download_file

# --- Installation Configuration ---
NODE_VERSION = "v22.15.0"
NODE_INSTALLER_URL = f"https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-x64.msi"
NODE_INSTALLER_FILENAME = f"node-{NODE_VERSION}-x64.msi"

GIT_INSTALLER_URL = "https://github.com/git-for-windows/git/releases/download/v2.49.0.windows.1/Git-2.49.0-64-bit.exe" # Example: v2.44.0 - Update if needed
GIT_INSTALLER_FILENAME = "Git-2.49.0-64-bit.exe"
GIT_WINGET_ID = "Git.Git"

PROJECT_ZIP_URL = "https://github.com/kolbytn/mindcraft/archive/refs/heads/main.zip"
PROJECT_ZIP_FILENAME = "mindcraft.zip"
PROJECT_EXTRACTED_FOLDER_NAME = "mindcraft-main" # Default name GitHub uses

# --- Worker Class ---

class InstallerWorker(QObject):
    log = pyqtSignal(str)
    finished = pyqtSignal(bool) # Signal success (True) or failure (False)

    def run(self):
        self.log.emit("Installation process started.")
        success = False # Assume failure unless explicitly set to True
        path = os.path.dirname(sys.executable)
        installer_dir = os.path.join(path, "installers") # Subdir for downloads

        try:
            # --- Ensure Target Directory Exists ---
            self.log.emit(f"Ensuring base directory exists: {path}")
            os.makedirs(path, exist_ok=True)

            # --- Create Installer Subdirectory ---
            self.log.emit(f"Ensuring installer directory exists: {installer_dir}")
            os.makedirs(installer_dir, exist_ok=True)

            # --- Change to Target Directory (optional, but helps with relative paths) ---
            # We'll use absolute paths mostly, so less critical, but good practice
            original_cwd = os.getcwd()
            os.chdir(path)
            self.log.emit(f"Changed working directory to: {path}")


            # --- 1. Install Git ---
            self.log.emit("\n--- Checking/Installing Git ---")
            if not is_tool_installed(self.log.emit, "git"):
                git_installer_path = os.path.join(installer_dir, GIT_INSTALLER_FILENAME)
                winget_available = shutil.which("winget") is not None

                if winget_available:
                    self.log.emit("Winget detected. Attempting Git installation via winget (may require admin rights)...")
                    try:
                        # Winget might pop UAC. --accept flags are crucial for automation.
                        run_command(self.log.emit, f'winget install --id {GIT_WINGET_ID} -e --source winget --accept-package-agreements --accept-source-agreements')
                        # Short delay and re-check
                        time.sleep(5)
                        if is_tool_installed(self.log.emit, "git"):
                            self.log.emit("Git installed successfully via winget.")
                        else:
                            self.log.emit("Git installation via winget may have failed or requires a shell restart. Will try manual download.")
                            winget_available = False # Fallback
                    except Exception as e:
                        # Error logged by run_command
                        self.log.emit(f"Winget installation failed. Falling back to manual download.")
                        winget_available = False # Fallback

                if not winget_available and not is_tool_installed(self.log.emit, "git"): # Check again if winget failed
                    self.log.emit("Attempting manual Git installation...")
                    if download_file(self.log.emit, GIT_INSTALLER_URL, git_installer_path):
                        self.log.emit(f"Running Git installer: {git_installer_path} (may require admin rights)...")
                        # Use absolute path for the installer
                        run_command(self.log.emit, [git_installer_path, "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"])
                        self.log.emit("Git installation command finished. NOTE: A shell or PC restart might be needed for PATH changes to take effect.")
                        time.sleep(10) # Give installer more time
                        if not is_tool_installed(self.log.emit, "git"):
                            self.log.emit("WARNING: Git installed, but 'git' command might not be in PATH yet. Restart shell/PC if subsequent steps fail.")
                    else:
                        self.log.emit("ERROR: Failed to download Git installer. Cannot proceed with Git-dependent steps if needed.")
                        # Decide if this is fatal. For mindcraft, probably not essential immediately.
                        # raise RuntimeError("Git download failed.") # Make it fatal if needed
            else:
                self.log.emit("Git is already installed or was installed previously.")


            # --- 2. Install Node.js ---
            self.log.emit("\n--- Checking/Installing Node.js ---")
            # Check both node and npm. Use None for npm version flag as it doesn't have --version easily.
            if not is_tool_installed(self.log.emit, "node") or not is_tool_installed(self.log.emit, "npm", None):
                node_installer_path = os.path.join(installer_dir, NODE_INSTALLER_FILENAME)
                self.log.emit("Node.js or npm not found. Attempting installation...")
                if download_file(self.log.emit, NODE_INSTALLER_URL, node_installer_path):
                    self.log.emit(f"Running Node.js MSI installer: {node_installer_path} (may require admin rights)...")
                    # msiexec needs full path, quoting handles spaces. Use absolute path.
                    msi_command = [
                        "msiexec.exe",
                        "/i",
                        f'"{node_installer_path}"', # Quote path
                        "/quiet", "/qn", # More silent flags
                        "/norestart"
                    ]
                    # Use shell=True for the quoted path and command line parsing
                    run_command(self.log.emit, " ".join(msi_command), shell=True)
                    self.log.emit("Node.js installation command finished. MSI installer should update PATH.")
                    self.log.emit("NOTE: A shell or PC restart might be needed for PATH changes to take full effect.")
                    time.sleep(15) # MSI installs can take longer to finalize PATH/registry

                    # Re-check after install attempt
                    if not is_tool_installed(self.log.emit, "node") or not is_tool_installed(self.log.emit, "npm", None):
                        self.log.emit("WARNING: Node/npm installed, but commands might not be in PATH yet. Restart shell/PC if subsequent steps fail.")
                        # Maybe try adding Node path manually here if desperate - complex and risky.
                    else:
                         self.log.emit("Node.js and npm verified after installation attempt.")

                else:
                    self.log.emit("ERROR: Failed to download Node.js installer. Cannot proceed.")
                    raise RuntimeError("Node.js download failed.")
            else:
                self.log.emit("Node.js and npm seem to be installed.")


            # --- 3. Download and Extract Project ---
            self.log.emit("\n--- Downloading and Extracting Mindcraft Project ---")
            # Use the base path for downloads and extractions now
            project_zip_path = os.path.join(path, PROJECT_ZIP_FILENAME)
            project_extracted_path = os.path.join(path, PROJECT_EXTRACTED_FOLDER_NAME)

            # Clean up previous download/extraction robustly
            if os.path.exists(project_zip_path):
                self.log.emit(f"Removing existing file: {project_zip_path}")
                try:
                    os.remove(project_zip_path)
                except OSError as e:
                    self.log.emit(f"WARNING: Could not remove existing zip file {project_zip_path}: {e}")
            if os.path.exists(project_extracted_path):
                self.log.emit(f"Removing existing directory: {project_extracted_path}")
                try:
                    shutil.rmtree(project_extracted_path)
                    self.log.emit(f"Removed directory successfully.")
                except OSError as e:
                    self.log.emit(f"WARNING: Could not remove existing directory {project_extracted_path}: {e}. Attempting to continue...")


            if download_file(self.log.emit, PROJECT_ZIP_URL, project_zip_path):
                self.log.emit(f"Extracting {project_zip_path} to {path}...")
                try:
                    with zipfile.ZipFile(project_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(path)
                    self.log.emit("Extraction complete.")
                    # Verify extraction
                    if not os.path.isdir(project_extracted_path):
                        raise RuntimeError(f"Extraction seemed complete, but expected folder '{project_extracted_path}' not found!")
                    self.log.emit(f"Verified extracted folder: {project_extracted_path}")

                except zipfile.BadZipFile:
                    self.log.emit(f"ERROR: Downloaded file {project_zip_path} is not a valid zip file.")
                    raise # Stop execution
                except Exception as e:
                    self.log.emit(f"ERROR: Failed to extract zip file: {e}")
                    self.log.emit(traceback.format_exc())
                    raise # Stop execution
                finally:
                    # Clean up the downloaded zip file
                    if os.path.exists(project_zip_path):
                        self.log.emit(f"Removing downloaded zip file: {project_zip_path}")
                        try:
                             os.remove(project_zip_path)
                        except OSError as e:
                            self.log.emit(f"WARNING: Could not remove zip file {project_zip_path}: {e}")
            else:
                self.log.emit("ERROR: Failed to download project zip file. Cannot proceed.")
                raise RuntimeError("Project download failed.")


            # --- 4. NPM Install ---
            self.log.emit("\n--- Running npm install ---")
            if os.path.isdir(project_extracted_path):
                # Ensure npm is available before trying to run it
                if is_tool_installed(self.log.emit, "npm", None):
                    self.log.emit(f"Running 'npm install' in {project_extracted_path}...")
                    # Use shell=True for npm on Windows. Set cwd. Capture output for logging.
                    run_command(self.log.emit, "npm install", cwd=project_extracted_path, shell=True, capture_output=True)
                    self.log.emit("'npm install' completed.")
                else:
                    self.log.emit("ERROR: npm command not found. Cannot run 'npm install'. Please ensure Node.js installed correctly and restart if necessary.")
                    raise RuntimeError("npm not found, cannot run install.")
            else:
                self.log.emit(f"ERROR: Project directory '{project_extracted_path}' not found. Cannot run 'npm install'.")
                raise RuntimeError("Project directory missing.")


            # --- 5. Rename keys.example.json ---
            self.log.emit("\n--- Renaming keys.example.json ---")
            example_key_file = os.path.join(project_extracted_path, "keys.example.json")
            final_key_file = os.path.join(project_extracted_path, "keys.json")

            if os.path.exists(example_key_file):
                if os.path.exists(final_key_file):
                     self.log.emit(f"'{final_key_file}' already exists. Skipping rename.")
                else:
                    try:
                        self.log.emit(f"Renaming '{example_key_file}' to '{final_key_file}'")
                        os.rename(example_key_file, final_key_file)
                        self.log.emit("Rename successful.")
                    except OSError as e:
                        self.log.emit(f"ERROR: Failed to rename key file: {e}")
                        # Decide if this is critical - maybe just warn
                        self.log.emit("WARNING: Could not rename key file. Manual rename might be required.")
            else:
                self.log.emit(f"Warning: '{example_key_file}' not found. Cannot rename.")
                if os.path.exists(final_key_file):
                    self.log.emit(f"'{final_key_file}' already exists.")


            # --- 6. Create config.json file to store information ---
            self.log.emit("\n--- Adding config.json to store launcher options ---")
            with open(os.path.join(path, "config.json"), mode="w") as config:
                config.write(json.dumps({"downloaded": time.time(), "settings": {}}))


            # --- Success ---
            self.log.emit("\n--- Installation process completed successfully! ---")
            success = True

        except Exception as e:
            self.log.emit(f"\n--- FATAL ERROR DURING INSTALLATION ---")
            self.log.emit(f"Error Type: {type(e).__name__}")
            self.log.emit(f"Error Message: {e}")
            self.log.emit("Detailed traceback:")
            self.log.emit(traceback.format_exc())
            self.log.emit("Installation failed. Please check the logs.")
            success = False

        finally:
            # Return to original directory if changed
            if 'original_cwd' in locals() and os.getcwd() != original_cwd:
                try:
                    os.chdir(original_cwd)
                    self.log.emit(f"Returned to original directory: {original_cwd}")
                except Exception as e:
                     self.log.emit(f"WARNING: Could not return to original directory {original_cwd}: {e}")

            # Emit finished signal with success status
            self.finished.emit(success)


class Installer(QMainWindow):
    def __init__(self, parentWindow=None): # Allow running standalone
        super().__init__()

        self.parentWindow = parentWindow
        self.thread_ = None # Initialize thread attribute
        self.worker = None # Initialize worker attribute

        self.setWindowTitle("Mindcraft Installer")
        self.setGeometry(100, 100, 800, 600) # Increased height slightly for log

        self.widget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10) # Reduced spacing slightly
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        self.header = QWidget()
        self.headerLayout = QVBoxLayout()
        self.headerLayout.setContentsMargins(0, 0, 0, 0)
        self.headerLayout.setSpacing(5)
        self.header.setLayout(self.headerLayout)
        # self.layout.addWidget(self.header) # Removed stretch, use fixed height
        self.header.setMaximumHeight(100)

        self.title = QLabel("Welcome to the Mindcraft Setup!") # Changed title slightly
        set_font_size(self.title, 24)
        self.subtitle = QLabel("This will install necessary components (Node.js, Git) and download Mindcraft.")
        set_font_size(self.subtitle, 12)
        self.headerLayout.addWidget(self.title)
        self.headerLayout.addWidget(self.subtitle)
        self.layout.addWidget(self.header) # Add header here

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.body = QWidget()
        self.bodyLayout = QVBoxLayout()
        self.bodyLayout.setContentsMargins(0, 10, 0, 0) # Add some top margin
        self.bodyLayout.setSpacing(10)
        self.body.setLayout(self.bodyLayout)
        self.layout.addWidget(self.body, stretch=1) # Add stretch here for body

        self.progressLabel = QLabel("Installation Details")
        set_font_size(self.progressLabel, 16)
        self.bodyLayout.addWidget(self.progressLabel)

        install_path = os.path.dirname(sys.executable)
        self.detailLabel = QLabel(f"Mindcraft will be set up in the following location:<br>"
                             f"<code>{install_path}</code>"
                             "<br><br><b>Important:</b> This setup may require <b>Administrator privileges</b> "
                             "to install Node.js and Git system-wide. If the installation fails, "
                             "please close this application and run it again as an Administrator."
                             "<br><br>Click 'Install' to begin."
                            )
        self.detailLabel.setTextFormat(Qt.RichText)
        self.detailLabel.setWordWrap(True) # Ensure text wraps
        set_font_size(self.detailLabel, 12)
        self.bodyLayout.addWidget(self.detailLabel)
        self.bodyLayout.addStretch(1) # Add stretch within body

        # Log text area - create it now but hide it initially
        self.logText = QTextEdit()
        self.logText.setFont(QFont("Courier New", 9)) # Monospaced font for logs
        self.logText.setReadOnly(True)
        self.logText.setVisible(False) # Initially hidden
        self.bodyLayout.addWidget(self.logText, stretch=1) # Add stretch factor


        self.navigationWidget = QWidget()
        self.navigationLayout = QHBoxLayout()
        self.navigationLayout.addStretch(1) # Push buttons to the right
        self.navigationWidget.setLayout(self.navigationLayout)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.close) # Simple close on cancel
        self.cancelButton.setFixedWidth(150) # Adjusted width

        self.installButton = QPushButton("Install")
        self.installButton.clicked.connect(self.begin_installation)
        self.installButton.setDefault(True) # Make it the default button
        self.installButton.setFixedWidth(150) # Adjusted width

        self.navigationLayout.addWidget(self.cancelButton)
        self.navigationLayout.addWidget(self.installButton)

        self.navigationLine = QFrame()
        self.navigationLine.setFrameShape(QFrame.HLine)
        self.navigationLine.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(self.navigationLine)

        self.layout.addWidget(self.navigationWidget)

    def logMessage(self, message: str):
        """Appends a timestamped message to the log QTextEdit."""
        # Ensure logText is visible when the first message arrives
        if not self.logText.isVisible():
            self.logText.setVisible(True)
            self.detailLabel.hide() # Hide the initial detail label
            self.progressLabel.setText("Installation Progress") # Update label

        timestamp = time.strftime('%H:%M:%S', time.localtime())
        # Use appendPlainText for efficiency and automatic newline
        self.logText.append(f"[{timestamp}] {message}")
        # Ensure the latest messages are visible
        self.logText.verticalScrollBar().setValue(self.logText.verticalScrollBar().maximum())


    def begin_installation(self):
        """Starts the installation process in a worker thread."""
        self.cancelButton.setEnabled(False) # Disable cancel during install
        self.installButton.setEnabled(False) # Disable install button
        self.installButton.setText("Installing...") # Change button text

        # Update UI elements for installation phase
        self.title.setText("Installing Mindcraft...")
        self.subtitle.setText("Please wait, this may take several minutes...")

        # Setup and start the worker thread
        self.thread_ = QThread(self) # Pass self as parent
        self.worker = InstallerWorker()
        self.worker.moveToThread(self.thread_)

        # Connect signals from worker to slots in the main thread
        self.worker.log.connect(self.logMessage)
        self.worker.finished.connect(self.on_installation_finished) # Connect to new slot

        # Connections for thread cleanup
        self.thread_.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread_.quit)
        # Use lambda to ensure deleteLater is called after the event loop processes quit()
        self.worker.finished.connect(lambda: self.worker.deleteLater())
        self.thread_.finished.connect(lambda: self.thread_.deleteLater())

        self.thread_.start()
        self.logMessage("Worker thread started.") # Log thread start


    def on_installation_finished(self, success):
        """Handles the completion of the installation process."""
        self.logMessage(f"Worker thread finished. Success: {success}")

        # Update button state and text based on success
        self.installButton.setEnabled(True)
        if success:
            self.installButton.setText("Finish")
            self.title.setText("Installation Successful!")
            self.subtitle.setText("You can now close this installer.")
            # Disconnect old action, connect new one
            try:
                self.installButton.clicked.disconnect(self.begin_installation)
            except TypeError: # Already disconnected or never connected
                 pass
            try: # Make sure finish isn't connected multiple times
                 self.installButton.clicked.disconnect(self.finish_installation)
            except TypeError:
                 pass
            self.installButton.clicked.connect(self.finish_installation)
            # Automatically focus the finish button
            self.installButton.setDefault(True)
            self.installButton.setFocus()
        else:
            self.installButton.setText("Close") # Change text to Close on failure
            self.title.setText("Installation Failed")
            self.subtitle.setText("There has been an error installing. Please report it to https://github.com/uukelele-scratch/mindcraft-gui/issues/new")
             # Disconnect old action, connect close action
            try:
                self.installButton.clicked.disconnect(self.begin_installation)
            except TypeError:
                 pass
            try: # Make sure close isn't connected multiple times
                 self.installButton.clicked.disconnect(self.close)
            except TypeError:
                 pass
            self.installButton.clicked.connect(self.close) # Button now closes window

        # Re-enable cancel button only if installation failed? Optional.
        # If successful, they should click Finish.
        if not success:
             self.cancelButton.setEnabled(True)

        # Clean up references
        self.thread_ = None
        self.worker = None


    def finish_installation(self):
        """Called when 'Finish' is clicked after successful installation."""
        box = QMessageBox(self)
        box.setWindowTitle("Installation Complete")
        box.setIcon(QMessageBox.Information)
        box.setText("Mindcraft setup has finished successfully.")
        box.setInformativeText("You may need to restart the main Mindcraft Launcher if it was already open.")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()
        self.close() # Close the installer window
        # Do not quit the entire application here if it's part of a larger app
        # QApplication.quit() # Only use this if the installer is standalone


    def closeEvent(self, event):
        """Handle window close event, especially during installation."""
        if self.thread_ and self.thread_.isRunning():
            reply = QMessageBox.question(self, 'Confirm Exit',
                                         "Installation is in progress. Are you sure you want to cancel and exit?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # Attempt to stop the thread gracefully - might not work if tasks are blocking
                # This is complex; usually, you just warn the user.
                # For simplicity, we'll just allow exit. Resources might be left half-installed.
                self.logMessage("WARNING: Installation cancelled by closing the window.")
                # We should ideally wait for the thread to finish after requesting quit,
                # but for simplicity here, we just accept the event.
                # self.thread_.quit()
                # self.thread_.wait(1000) # Wait a bit
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    # Important: For PyInstaller --noconsole mode, redirect stdout/stderr
    # to prevent errors if background processes print anything unexpectedly.
    # You might redirect to files or use a more robust logging setup.
    # Example redirection (optional, use with caution):
    # if getattr(sys, 'frozen', False): # Only if running as compiled executable
    #     log_dir = os.path.dirname(sys.executable)
    #     sys.stdout = open(os.path.join(log_dir, "installer_stdout.log"), "w")
    #     sys.stderr = open(os.path.join(log_dir, "installer_stderr.log"), "w")

    app = QApplication(sys.argv)

    # Apply a style maybe? (Optional)
    # app.setStyle("Fusion")

    # --- Font setup (Example - adjust as needed) ---
    default_font = QFont("Segoe UI", 10) # Use a common Windows font
    app.setFont(default_font)

    window = Installer()
    window.show()
    sys.exit(app.exec_())