import sys
import os
import json
import logging
import winreg
import shutil
import stat
import tempfile
import psutil
import atexit
from pathlib import Path
from typing import Optional, Dict
from dotenv import set_key

logger = logging.getLogger('geforce_presence')

def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        # Assuming src/core/utils.py, so we need to go up two levels to get to root
        # Original was in src/geforce_presence.py (one level deep from root if src is root, or two if project root)
        # Let's assume project root is where main.py will be or one level up.
        # If this file is in src/core/utils.py, __file__.parent is src/core. parent.parent is src. parent.parent.parent is project root.
        # The original code: base = Path(__file__).resolve().parent.parent (from src/geforce_presence.py)
        # If geforce_presence.py was in src/, then parent is src, parent.parent is project root.
        # Here: src/core/utils.py -> parent=core, parent.parent=src, parent.parent.parent=project root.
        base = Path(__file__).resolve().parent.parent.parent
    return base.joinpath(*parts)

# Define common paths
BASE_DIR = resource_path("")      
CONFIG_DIR = resource_path("config")
LOGS_DIR = resource_path("logs")
LANG_DIR = resource_path("lang")
ASSETS_DIR = resource_path("assets")
DRIVER_PATH = resource_path("tools", "msedgedriver.exe")
LOG_FILE = LOGS_DIR / "geforce_presence.log"
ENV_PATH = resource_path(".env")
DISCORD_CACHE_PATH = CONFIG_DIR / "discord_apps_cache.json"
DISCORD_DETECTABLE_URL = "https://discord.com/api/v9/applications/@me"
DISCORD_CACHE_TTL = 60 * 60 * 24  # 1 day
DISCORD_AUTO_APPLY_THRESHOLD = 10
DISCORD_ASK_TIMEOUT = 10
LOCK_FILE = Path(tempfile.gettempdir()) / "geforce_presence.lock"

def get_lang_from_registry(default="en"):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\GeForcePresence")
        lang, _ = winreg.QueryValueEx(key, "lang")
        winreg.CloseKey(key)

        if "spanish" in lang.lower():
            return "es"
        elif "english" in lang.lower():
            return "en"
        else:
            return default
    except Exception:
        return default

def load_locale(lang: str = "en") -> dict:
    path = LANG_DIR / f"{lang}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        return json.loads((LANG_DIR / "en.json").read_text(encoding="utf-8"))
    except Exception:
        return {}

def ensure_env_file(path: Path):
    default_env_content = """CLIENT_ID = '1095416975028650046'
UPDATE_INTERVAL = 10
CONFIG_PATH_FILE = ''
TEST_RICH_URL = 'https://steamcommunity.com/dev/testrichpresence'
STEAM_COOKIE=''
"""
    try:
        if not path.exists():
            path.write_text(default_env_content, encoding="utf-8")
            logger.info(f"✅ .env creado en: {path}")
    except PermissionError:
        appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        appdir = appdata / "geforce_presence"
        appdir.mkdir(parents=True, exist_ok=True)
        alt = appdir / ".env"
        if not alt.exists():
            alt.write_text(default_env_content, encoding="utf-8")
            logger.info(f"⚠️ No se pudo crear .env junto al exe; creado en: {alt}")
        # We might need to update the global ENV_PATH if we change it here, 
        # but for now let's just return the path used.
        return alt
    return path

def ensure_driver_executable(src_path: Path) -> str:
    try:
        if not src_path.exists():
            logger.warning(f"msedgedriver no encontrado en recursos: {src_path}")
            return str(src_path) 
        tmpdir = Path(tempfile.gettempdir()) / "geforce_driver"
        tmpdir.mkdir(parents=True, exist_ok=True)
        dest = tmpdir / src_path.name
        shutil.copy2(str(src_path), str(dest))
        try:
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
        except Exception:
            pass
        return str(dest)
    except Exception as e:
        logger.error(f"Error preparando msedgedriver: {e}")
        return str(src_path)

def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())

            if psutil.pid_exists(pid):
                logger.warning(f"⚠️ Ya existe otra instancia (PID {pid}). Reiniciando...")
                try:
                    # Cierra la instancia anterior (si es posible)
                    p = psutil.Process(pid)
                    p.terminate()
                    p.wait(5)
                    logger.info("✅ Instancia anterior finalizada correctamente.")
                except Exception as e:
                    logger.error(f"No se pudo cerrar la instancia anterior: {e}")
                
                # We don't restart here, we just return False or let the caller handle it.
                # The original code restarted the process.
                # For now, let's just return False if we can't kill it, or True if we killed it.
                # Actually, the original code tries to restart itself.
                # "os.execv(sys.executable, [sys.executable] + sys.argv)"
                # We should probably let the main function handle this logic or keep it here.
                # Let's keep the kill logic but maybe not the restart logic inside utils?
                # If we kill the other instance, we can proceed.
                
                # Wait a bit
                import time
                time.sleep(2)
                
                # If we are here, we killed the other process (or tried to). 
                # We can try to proceed.
            else:
                LOCK_FILE.unlink()
                logger.debug("Lock huérfano eliminado.")
        except Exception:
            try:
                LOCK_FILE.unlink()
            except Exception:
                pass

    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(release_lock)
    return True

def release_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass

def safe_json_load(path: Path) -> Optional[Dict]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando JSON {path}: {e}")
        return None

def save_cookie_to_env(cookie_value: str, env_path: Path):
    try:
        if env_path.exists():
            set_key(str(env_path), "STEAM_COOKIE", cookie_value)
            logger.info("💾 Cookie guardada en .env correctamente.")
        else:
            logger.warning("⚠️ No se encontró el archivo .env para guardar la cookie.")
    except Exception as e:
        logger.error(f"❌ Error guardando cookie en .env: {e}")

def save_json(obj, path: Path):
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(obj, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando JSON {path}: {e}")

