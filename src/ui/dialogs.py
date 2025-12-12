from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QListWidget, QHBoxLayout, QMessageBox, QWidget)
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt, QSize
from src.core.utils import ASSETS_DIR
from src.core.utils import get_lang_from_registry, load_locale
import os
import logging
try:
    LANG = get_lang_from_registry()
    TEXTS = load_locale(LANG)
except Exception:
    LANG = os.getenv('GEFORCE_LANG', 'en')
    TEXTS = load_locale(LANG)

logger = logging.getLogger('geforce_presence')


# ---- ESTILOS GLOBALES ----
GAMING_STYLESHEET = """
    QDialog {
        background-color: #0d0e10;
        border: 2px solid #1b1f23;
        border-radius: 14px;
    }

    QLabel {
        font-size: 14px;
        font-family: "Segoe UI";
        color: #e0e0e0;
        padding-bottom: 4px;
    }
    
    QLabel#title_label {
        font-size: 18px;
        font-weight: bold;
        color: #ffffff;
        padding-bottom: 8px;
    }

    QLineEdit, QSpinBox {
        padding: 8px;
        font-size: 14px;
        border: 1px solid #2c2f33;
        border-radius: 6px;
        background: #1a1b1d;
        color: #ffffff;
        font-family: "Segoe UI";
        font-weight: bold;
    }

    QLineEdit:focus, QSpinBox:focus {
        border: 2px solid #454C55;
    }

    QPushButton {
        background-color: #045D0E;
        color: #FFFFFF;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 14px;
        font-family: "Segoe UI";
        font-weight: bold;
    }

    QPushButton:hover {
        background-color: #12881F;
    }
    
    QPushButton:pressed {
        background-color: #03420a;
    }

    QPushButton#secondary {
        background-color: #2c2f33;
        color: #e6e6e6;
    }

    QPushButton#secondary:hover {
        background-color: #3c3f43;
    }

    /* LIST WIDGET & SCROLLBARS */
    QListWidget {
        background: #131416;
        border: 1px solid #1f2428;
        border-radius: 8px;
        padding: 6px;
        font-size: 13px;
        font-family: Consolas, monospace;
        color: #cfcfcf;
    }

    QListWidget::item {
        padding: 8px;
        border-radius: 4px;
        color: #dfdfdf;
    }

    QListWidget::item:selected {
        background-color: #00e676;
        color: #0e0f11;
        font-weight: bold;
    }

    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 4px 0;
    }
    QScrollBar::handle:vertical {
        background: #383a3d;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: #4a4d50;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0; 
        background: none; 
    }
"""

class GamingMessageBox(QDialog):
    def __init__(self, title, text, icon_type="info", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "geforce.ico")))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(GAMING_STYLESHEET)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 20)
        layout.setSpacing(20)
        
        # Icon & Text Row (Optional: add an icon label if desired, skipping for simplicity to match style)
        self.lbl_text = QLabel(text)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setAlignment(Qt.AlignCenter)
        self.lbl_text.setStyleSheet("font-size: 15px;")
        layout.addWidget(self.lbl_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self.reject)
        
        if icon_type == "question":
            self.ok_btn.setText(TEXTS.get("yes", "Yes"))
            self.cancel_btn.setText(TEXTS.get("no", "No"))
            btn_layout.addWidget(self.ok_btn)
            btn_layout.addWidget(self.cancel_btn)
        else:
            # Info / Warning
            btn_layout.addStretch()
            btn_layout.addWidget(self.ok_btn)
            btn_layout.addStretch()
            
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        # Auto size
        self.adjustSize()

    @staticmethod
    def show_info(parent, title, text):
        dlg = GamingMessageBox(title, text, "info", parent)
        dlg.exec_()
        
    @staticmethod
    def show_warning(parent, title, text):
        dlg = GamingMessageBox(title, text, "warning", parent)
        dlg.exec_()

    @staticmethod
    def show_question(parent, title, text):
        dlg = GamingMessageBox(title, text, "question", parent)
        return dlg.exec_() == QDialog.Accepted

class GamingInputDialog(QDialog):
    def __init__(self, title, label_text, value=0, min_val=0, max_val=100, step=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "geforce.ico")))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(GAMING_STYLESHEET)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 20)
        layout.setSpacing(15)
        
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        
        from PyQt5.QtWidgets import QSpinBox
        self.spin = QSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setValue(value)
        self.spin.setSingleStep(step)
        self.spin.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.spin)
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setFixedSize(300, 180)

    @staticmethod
    def get_int(parent, title, label, value=0, min_val=0, max_val=100, step=1):
        dlg = GamingInputDialog(title, label, value, min_val, max_val, step, parent)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.spin.value(), True
        return value, False


class AskGameDialog(QDialog):
    def __init__(self, parent=None, title=TEXTS.get("force_game", "Force Game"),
                 message=TEXTS.get("game_name", "GAME NAME:")):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "geforce.ico")))
        self.setFixedSize(420, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # ---- 🎮 ESTILO GAMING OSCURO ----
        self.setStyleSheet(GAMING_STYLESHEET)

        # ---- LAYOUT ----
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 15)
        layout.setSpacing(15)

        # Centrado del label
        self.label = QLabel(message)
        self.label.setObjectName("title_label")
        self.label.setAlignment(Qt.AlignCenter)  
        layout.addWidget(self.label)

        self.entry = QLineEdit()
        layout.addWidget(self.entry)

        # Botones más compactos
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.ok_btn = QPushButton(TEXTS.get("ok", "OK"))
        self.cancel_btn = QPushButton(TEXTS.get("cancel", "Cancel"))
        self.cancel_btn.setObjectName("secondary")

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # ---- 🎞️ ANIMATED BACKGROUND ----
        self.bg_label = QLabel(self)
        self.gif = QMovie(str(ASSETS_DIR / "nvidia.gif"))
        self.bg_label.setMovie(self.gif)
        self.bg_label.setScaledContents(True)
        self.gif.start()
        # Ensure it stays behind
        self.bg_label.lower()

    def resizeEvent(self, event):
        if hasattr(self, 'bg_label'):
            self.bg_label.resize(self.size())
        super().resizeEvent(event)

    def get_game_name(self):
        return self.entry.text()


class MatchSelectionDialog(QDialog):
    def __init__(self, game_key, candidates, parent=None):
        super().__init__(parent)

        self.setWindowTitle(TEXTS.get("apply_discord_match", "Discord Match"))
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "geforce.ico")))
        self.setMinimumWidth(540)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.candidates = candidates
        self.selected_match = None

        # ---- 🎮 ESTILO GAMING OSCURO ----
        self.setStyleSheet(GAMING_STYLESHEET)

        # ---- LAYOUT ----
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(15)

        lbl = QLabel(
            TEXTS.get(
                "ask_discord_match",
                f"Se encontró un posible juego: '{game_key}'.\nSelecciona la coincidencia correcta:"
            )
        )
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        for c in candidates:
            exe = c.get("exe") or ""
            text = f"{c['name']}  ({c['score']:.2f})  [{exe}]  id={c.get('id') or '—'}"
            self.list_widget.addItem(text)

        layout.addWidget(self.list_widget)

        # ---- BOTONES ----
        btn_layout = QHBoxLayout()

        self.confirm_btn = QPushButton(TEXTS.get("confirm", "Confirmar"))
        self.confirm_btn.clicked.connect(self.on_confirm)

        self.ignore_btn = QPushButton(TEXTS.get("ignore", "Ignorar"))
        self.ignore_btn.setObjectName("secondary")
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
            QMessageBox.warning(
                self,
                TEXTS.get("selection_required", "Selección requerida"),
                TEXTS.get("selection_required_msg", "Por favor selecciona una opción de la lista.")
            )
