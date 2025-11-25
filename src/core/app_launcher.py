import os
import psutil
import subprocess
import logging
from pathlib import Path
from typing import Optional
from src.core.utils import get_lang_from_registry, load_locale

try:
    LANG = get_lang_from_registry()
    TEXTS = load_locale(LANG)
except Exception:
    LANG = os.getenv('GEFORCE_LANG', 'en')
    TEXTS = load_locale(LANG)

logger = logging.getLogger('geforce_presence')

class AppLauncher:
    @staticmethod
    def find_geforce_now() -> Optional[str]:
        possible = [
            Path(os.getenv("LOCALAPPDATA", "")) / "NVIDIA Corporation" / "GeForceNOW" / "CEF" / "GeForceNOW.exe"
        ]
        for p in possible:
            if p.exists():
                return str(p)
            
        return None

    @staticmethod
    def _is_process_running_by_name(target_name: str) -> bool:
        try:
            for proc in psutil.process_iter(attrs=['name']):
                name = (proc.info.get('name') or "").lower()
                if name == target_name.lower() or target_name.lower() in name:
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def launch_geforce_now() -> bool:
        if AppLauncher._is_process_running_by_name("GeForceNOW.exe"):
            logger.info(TEXTS.get("already_running", "💡 GeForce NOW is already running"))
            return True
        path = AppLauncher.find_geforce_now()
        if path:
            logger.info(TEXTS.get("launching", "🚀 Launching GeForce NOW..."))
            subprocess.Popen([path])
            return True
        else:
            logger.error(TEXTS.get("geforce_not_found", "GeForce NOW not found in the default installation path."))
            return False

    @staticmethod
    def find_discord() -> Optional[str]:
        p = Path(os.getenv("LOCALAPPDATA", "")) / "Discord" / "Update.exe"
        if p.exists():
            return str(p)
        return None

    @staticmethod
    def launch_discord():
        for proc in psutil.process_iter(attrs=['name']):
            name = (proc.info.get('name') or "").lower()
            if "discord" in name and "update" not in name:
                logger.info(TEXTS.get("already_running_discord", "💡 Discord ya está en ejecución"))
                return
        updater = AppLauncher.find_discord()
        if updater:
            logger.info(TEXTS.get("launching_discord", "🚀 Iniciando Discord..."))
            subprocess.Popen([updater, "--processStart", "Discord.exe"])
        else:
            logger.warning("⚠️ No se encontró Discord instalado en la ruta por defecto.")
