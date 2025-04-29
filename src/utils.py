from PyQt5.QtWidgets import (
    QWidget,
)
from PyQt5.QtGui import QFont

def set_font_size(item: QWidget, size: int | float):
    item.setFont(QFont(QFont().family(), size))

import subprocess, sys, traceback, shutil, requests, os, io

def stream_command(log_func, command, cwd=None, shell=True):
    """
    Runs a command using Popen, streams its combined stdout/stderr, and returns success status.
    """
    cmd_str = ' '.join(command) if isinstance(command, list) else command
    log_func(f"Streaming command: {cmd_str}" + (f" in {cwd}" if cwd else ""))
    process = None # Initialize process to None
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            # Use text mode with error handling for decoding
            # bufsize=1 ensures line buffering (more immediate output)
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        # Read line by line from the process's stdout
        # The loop will end when the process closes its stdout stream (usually at exit)
        for line in process.stdout:
             # Strip trailing newline/whitespace before logging
            log_func(line.rstrip())

        # Wait for the process to terminate completely
        process.wait()

        # Check the return code after the process has finished
        if process.returncode == 0:
            log_func(f"Command finished successfully (Return Code: {process.returncode}).")
            return True
        else:
            log_func(f"ERROR: Command failed (Return Code: {process.returncode}).")
            return False

    except FileNotFoundError:
        cmd_name = cmd_str.split()[0] if cmd_str else "Unknown"
        log_func(f"ERROR: Command not found - ensure the program '{cmd_name}' is installed and in PATH.")
        return False # Indicate failure
    except Exception as e:
        log_func(f"ERROR: An unexpected error occurred while streaming command: {cmd_str}")
        log_func(f"Error details: {e}")
        log_func(traceback.format_exc())
        # Ensure process is terminated if it's still running after an exception
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5) # Give it a chance to terminate
                log_func("Terminated hanging process due to exception.")
            except Exception as term_e:
                 log_func(f"Error trying to terminate process: {term_e}")
        return False # Indicate failure

def run_command(log_func, command, cwd=None, shell=True, check=True, text=True):
    """Runs a command using subprocess and logs output/errors."""
    cmd_str = ' '.join(command) if isinstance(command, list) else command
    log_func(f"Running command: {cmd_str}" + (f" in {cwd}" if cwd else ""))
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=shell,
            check=check,
            text=text,
            stderr=subprocess.PIPE, # Always capture stderr for logging
            stdout=subprocess.PIPE, # Always capture stdout for logging
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0 # Hide console window on Windows
        )
        # Log stdout if it's not empty
        stdout_log = result.stdout.strip() if result.stdout else ""
        if stdout_log:
            log_func(f"Command stdout:\n---\n{stdout_log}\n---")

        # Log stderr if it's not empty
        stderr_log = result.stderr.strip() if result.stderr else ""
        if stderr_log:
             # Log stderr even on success, as some tools write informational messages here
            log_func(f"Command stderr:\n---\n{stderr_log}\n---")

        # If check=True, CalledProcessError will be raised below if returncode != 0
        log_func(f"Command finished successfully (Return Code: {result.returncode}).")
        return result # Return the result object
    except subprocess.CalledProcessError as e:
        log_func(f"ERROR: Command failed: {cmd_str}")
        log_func(f"Return code: {e.returncode}")
        # Log captured output from the exception object
        stdout_log = e.stdout.strip() if e.stdout else ""
        if stdout_log:
            log_func(f"stdout:\n---\n{stdout_log}\n---")
        stderr_log = e.stderr.strip() if e.stderr else ""
        if stderr_log:
            log_func(f"stderr:\n---\n{stderr_log}\n---")
        raise # Re-raise the exception to be caught by the worker's main try/except
    except FileNotFoundError:
        # Extract the command name attempt
        cmd_name = cmd_str.split()[0] if cmd_str else "Unknown"
        log_func(f"ERROR: Command not found - ensure the program '{cmd_name}' is installed and in PATH.")
        raise
    except Exception as e:
        log_func(f"ERROR: An unexpected error occurred while running command: {cmd_str}")
        log_func(f"Error details: {e}")
        log_func(traceback.format_exc()) # Log detailed traceback
        raise

def is_tool_installed(log_func, tool_name, version_flag="--version"):
    """Checks if a tool is installed and accessible in PATH, logs results."""
    log_func(f"Checking if '{tool_name}' is installed...")
    tool_path = shutil.which(tool_name)
    if not tool_path:
        log_func(f"'{tool_name}' not found in PATH.")
        return False
    else:
        log_func(f"'{tool_name}' found at: {tool_path}")
        # Optionally, run the version command to be more certain
        if version_flag is not None: # Allow skipping version check if None
            try:
                cmd_to_run = f'"{tool_path}" {version_flag}' if version_flag else f'"{tool_path}"'
                 # Use capture_output=True, check=True
                run_command(log_func, cmd_to_run, shell=True, check=True, capture_output=True)
                log_func(f"'{tool_name}' version check successful.")
                return True
            except Exception as e:
                # Log the error from run_command (it already logs details)
                log_func(f"'{tool_name}' found, but version check failed. Assuming usable but may have issues.")
                # Depending on strictness, could return False here
                return True # Let's assume it's okay if `which` found it
        else:
            log_func(f"'{tool_name}' found (skipping version check).")
            return True
        
def download_file(log_func, url, destination_path):
    """Downloads a file from a URL to a destination path, logs progress/errors."""
    log_func(f"Attempting to download {url} to {destination_path}...")
    try:
        response = requests.get(url, stream=True, timeout=30) # Add timeout
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        bytes_downloaded = 0
        last_logged_mb = -1
        chunk_size=8192
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    # Log progress roughly every MB
                    current_mb = bytes_downloaded // (1024 * 1024)
                    if current_mb > last_logged_mb:
                        if total_size > 0:
                            percent = (bytes_downloaded / total_size) * 100
                            log_func(f"Downloaded {current_mb} MB / {total_size // (1024*1024)} MB ({percent:.1f}%)")
                        else:
                            log_func(f"Downloaded {current_mb} MB...")
                        last_logged_mb = current_mb

        log_func(f"Download complete ({bytes_downloaded // (1024*1024)} MB). File saved to {destination_path}")
        return True
    except requests.exceptions.Timeout:
        log_func(f"ERROR: Timeout occurred while downloading {url}")
    except requests.exceptions.RequestException as e:
        log_func(f"ERROR: Failed to download {url}: {e}")
    except IOError as e:
        log_func(f"ERROR: Could not write file {destination_path}: {e}")
    except Exception as e:
        log_func(f"ERROR: An unexpected error occurred during download: {e}")
        log_func(traceback.format_exc())

    # Clean up partial download if it exists
    if os.path.exists(destination_path):
        try:
            os.remove(destination_path)
            log_func(f"Cleaned up partial download: {destination_path}")
        except OSError as e:
            log_func(f"WARNING: Could not remove partial download {destination_path}: {e}")
    return False