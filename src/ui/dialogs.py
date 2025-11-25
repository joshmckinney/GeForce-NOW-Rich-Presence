from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QListWidget, QHBoxLayout, QMessageBox, QWidget)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from src.core.utils import ASSETS_DIR

class AskGameDialog(QDialog):
    def __init__(self, parent=None, title=TEXTS.get("tray_force_game", "Forzar juego"), message=TEXTS.get("game_name", "Nombre del juego:")):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "geforce.ico")))
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        
        self.label = QLabel(message)
        layout.addWidget(self.label)
        
        self.entry = QLineEdit()
        layout.addWidget(self.entry)
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton(TEXTS.get("ok", "Aceptar"))
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton(TEXTS.get("cancel", "Cancelar"))
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def get_game_name(self):
        return self.entry.text()

class MatchSelectionDialog(QDialog):
    def __init__(self, game_key, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTS.get("apply_discord_match", "Coincidencia Discord: {game_key}"))
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "geforce.ico")))
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.candidates = candidates
        self.selected_match = None
        
        layout = QVBoxLayout()
        
        lbl = QLabel(TEXTS.get("ask_discord_match", "Se encontró un nuevo juego: '{game_key}'.\nSelecciona la coincidencia correcta (si alguna):"))
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        for c in candidates:
            exe = c.get("exe") or ""
            text = f"{c['name']}  ({c['score']:.2f})  [{exe}]  id={c.get('id') or '—'}"
            self.list_widget.addItem(text)
        
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton(TEXTS.get("confirm", "Confirmar"))
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.ignore_btn = QPushButton(TEXTS.get("ignore", "Ignorar"))
        self.ignore_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.ignore_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def on_confirm(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.selected_match = self.candidates[row]
            self.accept()
        else:
            QMessageBox.warning(self, TEXTS.get("selection_required", "Selección requerida"), TEXTS.get("selection_required_msg", "Por favor selecciona una opción de la lista."))

