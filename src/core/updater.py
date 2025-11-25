import sys
import os
import logging
import requests
import subprocess
import tempfile
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from src.version import VERSION
from src.utils.i18n import t

logger = logging.getLogger('geforce_presence')

GITHUB_RELEASES_URL = "https://api.github.com/repos/KarmaDevz/GeForce-NOW-Rich-Presence/releases/latest"

def parse_version(v_str):
    """Simple semantic version parser (e.g., '1.0.0' -> (1, 0, 0))"""
    try:
        return tuple(map(int, v_str.lstrip('v').split('.')))
    except Exception:
        return (0, 0, 0)

class UpdateWorker(QThread):
    check_finished = pyqtSignal(bool, str, str, str) # has_update, version, url, release_notes
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal(str) # path to installer
    error_occurred = pyqtSignal(str)

    def __init__(self, mode="check", download_url=None):
        super().__init__()
        self.mode = mode
        self.download_url = download_url

    def run(self):
        if self.mode == "check":
            self.check_updates()
        elif self.mode == "download":
            self.download_update()

    def check_updates(self):
        try:
            logger.info("Checking for updates...")
            response = requests.get(GITHUB_RELEASES_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            latest_version_str = data.get("tag_name", "v0.0.0")
            latest_version = parse_version(latest_version_str)
            current_version = parse_version(VERSION)

            logger.info(f"Current version: {VERSION}, Latest version: {latest_version_str}")

            if latest_version > current_version:
                # Find .exe asset
                exe_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        exe_url = asset["browser_download_url"]
                        break
                
                if exe_url:
                    self.check_finished.emit(True, latest_version_str, exe_url, data.get("body", ""))
                else:
                    logger.warning("New version found but no .exe asset.")
                    self.check_finished.emit(False, "", "", "")
            else:
                self.check_finished.emit(False, "", "", "")

        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            self.error_occurred.emit(str(e))

    def download_update(self):
        try:
            logger.info(f"Downloading update from {self.download_url}")
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            tmp_dir = Path(tempfile.gettempdir()) / "geforce_update"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            installer_path = tmp_dir / "installer.exe"

            with open(installer_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_progress.emit(progress)

            self.download_finished.emit(str(installer_path))

        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            self.error_occurred.emit(str(e))

class UpdateDialog(QDialog):
    def __init__(self, version, url, release_notes, parent=None):
        super().__init__(parent)
        self.version = version
        self.url = url
        self.setWindowTitle(t.get("update_available_title", "Update Available"))
        self.setFixedSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()

        lbl_title = QLabel(f"<b>{t.get('new_version_found', 'New version found:')} {version}</b>")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_notes = QLabel(t.get("release_notes", "Release Notes:"))
        layout.addWidget(lbl_notes)

        self.notes_box = QLabel(release_notes)
        self.notes_box.setWordWrap(True)
        self.notes_box.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        self.notes_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.notes_box)
        
        layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_update = QPushButton(t.get("update_now", "Update Now"))
        self.btn_update.clicked.connect(self.start_download)
        self.btn_cancel = QPushButton(t.get("cancel", "Cancel"))
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.worker = None

    def start_download(self):
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = UpdateWorker(mode="download", download_url=self.url)
        self.worker.download_progress.connect(self.progress_bar.setValue)
        self.worker.download_finished.connect(self.install_update)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def install_update(self, installer_path):
        try:
            logger.info(f"Launching installer: {installer_path}")
            # Launch installer and exit
            subprocess.Popen([installer_path], shell=True)
            sys.exit(0)
        except Exception as e:
            self.on_error(f"Failed to launch installer: {e}")

    def on_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.btn_update.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(False)

class Updater:
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.worker = None

    def check_for_updates(self, silent=True):
        self.worker = UpdateWorker(mode="check")
        self.worker.check_finished.connect(lambda has_update, ver, url, notes: self.on_check_finished(has_update, ver, url, notes, silent))
        self.worker.start()

    def on_check_finished(self, has_update, version, url, notes, silent):
        if has_update:
            dialog = UpdateDialog(version, url, notes, self.parent_widget)
            dialog.exec_()
        elif not silent:
            QMessageBox.information(self.parent_widget, t.get("no_updates", "No Updates"), t.get("latest_version_msg", "You are using the latest version."))
