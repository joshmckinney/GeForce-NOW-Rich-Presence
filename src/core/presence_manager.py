import time
import logging
import psutil
import subprocess
import tempfile
import shutil
import difflib
import re
import threading
import sys
from pathlib import Path
from typing import Optional, Dict, List

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from pypresence import Presence
from src.core.utils import safe_json_load, save_json, CONFIG_DIR, BASE_DIR, DISCORD_CACHE_PATH, DISCORD_DETECTABLE_URL, DISCORD_CACHE_TTL, DISCORD_AUTO_APPLY_THRESHOLD, DISCORD_ASK_TIMEOUT
from src.core.steam_scraper import SteamScraper, find_steam_appid_by_name
from src.core.cookie_manager import CookieManager

# Import win32 libs inside methods or here if safe
try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None
    win32process = None

logger = logging.getLogger('geforce_presence')

class PresenceManager(QObject):
    # Signals to communicate with UI
    log_message = pyqtSignal(str, str) # level, message
    request_match_selection = pyqtSignal(str, list) # game_key, candidates
    
    def __init__(self, client_id: str, games_map: dict, cookie_manager: CookieManager, test_rich_url: str, texts: Dict,
                 update_interval: int = 10, keep_alive: bool = False):
        super().__init__()
        self.client_id = client_id
        self.games_map = games_map
        self.cookie_manager = cookie_manager
        self.test_rich_url = test_rich_url
        self.texts = texts
        self.update_interval = update_interval
        self.keep_alive = keep_alive
        
        self.fake_proc = None
        self.fake_exec_path = None
        self.last_log_message = None
        self.rpc = None
        
        self.scraper = SteamScraper(self.cookie_manager.env_cookie, test_rich_url)

        self.last_game = None
        self.forced_game = None
        self._last_forced_game = None
        self._force_stop_time = 0
        
        self._connect_rpc()
        
        # Timer for the main loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_presence)
        
    def start_monitoring(self):
        logger.info("🟢 Iniciando monitor de presencia...")
        self.timer.start(self.update_interval * 1000)

    def stop_monitoring(self):
        self.timer.stop()
        self.close()

    def _connect_rpc(self, client_id: Optional[str] = None):
        try:
            if self.rpc:
                try:
                    self.rpc.close()
                except Exception:
                    pass
            client_id = client_id or self.client_id
            self.rpc = Presence(client_id)
            self.rpc.connect()
            logger.info(f"✅ Conectado a Discord RPC con client_id={client_id}")
        except Exception as e:
            logger.error(f"❌ Error conectando a Discord RPC: {e}")
            self.rpc = None

    def stop_force_game(self):
        """Detiene el forzado de juego y vuelve a la detección automática"""
        if self.forced_game:
            forced_game_name = self.forced_game.get('name', 'Unknown')
            logger.info(f"🧹 Deteniendo forzado de juego: {forced_game_name}")
            
            self._last_forced_game = self.forced_game.copy()
            self.forced_game = None
            self.last_game = None
            
            self.close_fake_executable()
            
            try:
                if self.rpc:
                    self.rpc.close()
            except Exception:
                pass
            
            self.client_id = "1095416975028650046"  # Client ID por defecto
            self._connect_rpc(self.client_id)
            
            self._force_stop_time = time.time()
            
            logger.info("🔄 Volviendo a detección automática de juegos")

    def _disconnect_rpc_temporarily(self):
        try:
            if self.rpc:
                self.rpc.close()
                self.rpc = None
                logger.info("📴 RPC desconectado temporalmente (modo forzar juego activo).")
        except Exception as e:
            logger.debug(f"Error al desconectar RPC temporalmente: {e}")

    def wait_for_file_release(self, path: Path, timeout: float = 3.0) -> bool:
        start = time.time()
        if not path.exists():
            return True
        while time.time() - start < timeout:
            try:
                with open(path, "rb"):
                    return True
            except PermissionError:
                time.sleep(0.1)
            except Exception:
                return False
        return False

    def close_fake_executable(self):
        try:
            temp_dir_str = str(Path(tempfile.gettempdir()) / "discord_fake_game").lower()
            closed_any = False
            if self.fake_proc and self.fake_proc.poll() is None:
                logger.info(f"🛑 Cerrando ejecutable falso (PID {self.fake_proc.pid})")
                self.fake_proc.terminate()
                try:
                    self.fake_proc.wait(timeout=3)
                except Exception:
                    self.fake_proc.kill()
                closed_any = True
            for proc in psutil.process_iter(["exe", "pid"]):
                exe = proc.info.get("exe")
                if exe and exe.lower().startswith(temp_dir_str):
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    closed_any = True
            if closed_any:
                time.sleep(0.35)
                logger.info("✅ Ejecutable falso cerrado")
                
        except Exception as e:
            logger.error(f"❌ Error cerrando ejecutable falso: {e}")
        finally:
            self.fake_proc = None
            self.fake_exec_path = None

    def launch_fake_executable(self, executable_path: str):
        try:
            temp_dir = Path(tempfile.gettempdir()) / "discord_fake_game"
            exec_full_path = temp_dir / executable_path
            exec_full_path.parent.mkdir(parents=True, exist_ok=True)

            if self.fake_exec_path == exec_full_path and self.fake_proc and self.fake_proc.poll() is None:
                logger.debug(f"🚀 Ejecutable ya en ejecución: {exec_full_path}")
                return
            dumb_path = BASE_DIR / "tools" / "dumb.exe"
            if not dumb_path.exists():
                logger.error(f"❌ dumb.exe no encontrado en {dumb_path}")
                return
            if not exec_full_path.exists():
                shutil.copy2(dumb_path, exec_full_path)
            else:
                if not self.wait_for_file_release(exec_full_path, timeout=3.0):
                    logger.error(f"❌ El archivo {exec_full_path} sigue bloqueado por otro proceso")
                    return
            logger.info(f"🚀 Ejecutando ejecutable falso: {exec_full_path}")
            proc = subprocess.Popen([str(exec_full_path)], cwd=str(exec_full_path.parent))
            self.fake_proc = proc
            self.fake_exec_path = exec_full_path
        except Exception as e:
            logger.error(f"❌ Error creando/ejecutando ejecutable falso: {e}")

    def _fetch_discord_apps_cached(self):
        try:
            if DISCORD_CACHE_PATH.exists():
                data = safe_json_load(DISCORD_CACHE_PATH)
                if data and isinstance(data, dict):
                    ts = data.get("_ts", 0)
                    if time.time() - ts < DISCORD_CACHE_TTL:
                        return data.get("apps", [])

            import requests
            resp = requests.get(DISCORD_DETECTABLE_URL, timeout=15)
            if resp.status_code == 200:
                apps = resp.json()
                to_save = {"_ts": int(time.time()), "apps": apps}
                try:
                    save_json(to_save, DISCORD_CACHE_PATH)
                except Exception:
                    pass
                return apps
        except Exception as e:
            logger.debug(f"Error obteniendo detectable de Discord: {e}")
        return []

    def _find_discord_matches(self, game_name: str, max_candidates: int = 5):
        apps = self._fetch_discord_apps_cached()
        candidates = []
        gnl = (game_name or "").lower()
        for app in apps:
            name = app.get("name", "") or ""
            aliases = app.get("aliases", []) or []
            score_name = difflib.SequenceMatcher(None, gnl, name.lower()).ratio()
            score_alias = 0.0
            for a in aliases:
                s = difflib.SequenceMatcher(None, gnl, (a or "").lower()).ratio()
                if s > score_alias:
                    score_alias = s
            score = max(score_name, score_alias)
            if score > 0.35:
                exe = None
                for e in app.get("executables", []) or []:
                    if e.get("os") == "win32" and e.get("name"):
                        exe = e.get("name")
                        break
                candidates.append({
                    "name": name,
                    "id": app.get("id"),
                    "exe": exe,
                    "score": score,
                    "aliases": aliases
                })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:max_candidates]

    def _apply_discord_match(self, game_key: str, match: dict):
        try:
            if not match or "id" not in match:
                return False
            config_path = CONFIG_DIR / "games_config_merged.json"
            games_config = safe_json_load(config_path) or {}

            entry = games_config.get(game_key, {}) or {}

            if match.get("exe"):
                entry.setdefault("executable_path", match["exe"])
            if match.get("id"):
                entry.setdefault("client_id", match["id"])
            games_config[game_key] = entry
            save_json(games_config, config_path)
            self.games_map = games_config
            logger.info(f"✅ Discord match aplicado para '{game_key}': id={match.get('id')}, exe={match.get('exe')}")
            return True
        except Exception as e:
            logger.error(f"❌ Error aplicando discord match: {e}")
            return False

    def _ask_discord_match_for_new_game(self, game_key: str):
        try:
            candidates = self._find_discord_matches(game_key, max_candidates=6)
            if not candidates:
                logger.info(f"ℹ️ No se encontraron matches en Discord para '{game_key}'")
                return
            top = candidates[0]
            logger.debug(f"Discord top candidate for '{game_key}': {top.get('name')} (score={top.get('score'):.2f})")
            
            if top.get("score", 0) >= DISCORD_AUTO_APPLY_THRESHOLD:
                applied = self._apply_discord_match(game_key, top)
                if applied:
                    logger.info(f"🔁 Aplicado automaticamente match Discord: {top.get('name')} (score {top.get('score'):.2f})")
                return

            # Emit signal to request user selection in UI
            self.request_match_selection.emit(game_key, candidates)
            
        except Exception as e:
            logger.debug(f"Error en ask_discord_match_for_new_game: {e}")

    # Slot to receive the selected match from UI
    def on_match_selected(self, game_key: str, match: dict):
        if match:
             self._apply_discord_match(game_key, match)
        else:
             logger.info(f"ℹ️ Usuario ignoró match Discord para '{game_key}'")

    def check_presence(self):
        try:
            if not self.is_geforce_running():
                if getattr(self, "forced_game", None):
                    logger.info("Modo forzado desactivado ...")
                    self.forced_game = None
                if self.last_game is not None:
                    logger.info("⚠️ GeForce NOW no está en ejecución — limpiando presencia.")
                    try:
                        if self.rpc: self.rpc.clear()
                    except Exception:
                        pass
                    self.close_fake_executable()
                    self.last_game = None
                    self.last_log_message = None
                return

            game = self.find_active_game()
            self.update_presence(game)

        except Exception as e:
            if str(e) not in (
                "'NoneType' object has no attribute 'get'",
                "cannot access local variable 'title' where it is not associated with a value",
            ):
                logger.error(f"❌ Error inesperado en el loop principal: {e}")
            try:
                if self.rpc: self.rpc.clear()
            except Exception:
                pass
            self.close_fake_executable()

    def find_active_game(self) -> Optional[dict]:
        try:
            if not win32gui:
                logger.error("win32gui not available")
                return None
                
            hwnds = []
            win32gui.EnumWindows(lambda h, p: p.append(h) if win32gui.IsWindowVisible(h) else None, hwnds)
            last_title = getattr(self, "_last_window_title", None)
            title = None
            for hwnd in hwnds:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc_name = psutil.Process(pid).name().lower()
                except Exception:
                    continue
                if "geforcenow" not in proc_name:
                    continue
                title = win32gui.GetWindowText(hwnd)
                if title == last_title:
                    pass
                else:
                    setattr(self, "_last_window_title", title)
                if title == None:
                    self.log_once("⚠️ GeForce NOW no está abierto")

                clean = re.sub(r'\s*(en|on|in|via)?\s*GeForce\s*NOW.*$', '', title, flags=re.IGNORECASE).strip()
                clean = re.sub(r'[®™]', '', clean).strip()
                
                last_clean = getattr(self, "_last_clean_title", None)
                if clean != last_clean:
                    setattr(self, "_last_clean_title", clean)
                appid = None 
                for game_name, info in self.games_map.items():
                    if clean.lower() == game_name.lower():
                        if not info.get("steam_appid"):
                            appid = find_steam_appid_by_name(clean)
                            if appid:
                                info["steam_appid"] = appid
                                config_path = CONFIG_DIR / "games_config_merged.json"
                                games_config = safe_json_load(config_path) or {}
                                games_config[game_name]["steam_appid"] = appid
                                save_json(games_config, config_path)
                                logger.info(f"✅ Steam AppID actualizado en JSON para: {game_name} -> {appid}")
                                self.games_map = games_config
                        return info
                appid = find_steam_appid_by_name(clean)
                new_game = {
                    "name": clean,
                    "steam_appid": appid,
                    "image": "steam"
                }
                self.games_map[clean] = new_game
                config_path = CONFIG_DIR / "games_config_merged.json"
                games_config = safe_json_load(config_path) or {}
                games_config[clean] = new_game
                save_json(games_config, config_path)
                updated = self.games_map.get(clean)
                if updated:
                    new_game = updated
                logger.info(f"🆕 Juego agregado a config: {clean} (AppID: {appid})")
                self.games_map = games_config

                try:
                    threading.Thread(
                        target=self._ask_discord_match_for_new_game,
                        args=(clean,),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.debug(f"no se pudo iniciar hilo de discord-match: {e}")
                return new_game

            return {'name': title, 'image': 'geforce_default', 'client_id': self.client_id}
        except Exception as e:
            if str(e) == "cannot access local variable 'title' where it is not associated with a value":
                self.log_once(f"⚠️ GeForce NOW está cerrado")
            else:
                logger.error(f"⚠️ Error detectando juego activo: {e}")

    def log_once(self, msg, level="info"):
        if msg != self.last_log_message:
            getattr(logger, level)(msg)
            self.last_log_message = msg

    def is_geforce_running(self) -> bool:
        try:
            for proc in psutil.process_iter(attrs=['name']):
                name = (proc.info.get('name') or "").lower()
                if "geforcenow" in name:
                    return True
        except Exception as e:
            logger.debug(f"Error comprobando procesos: {e}")
        return False
    
    def clear_forced_game(self):
        if self.forced_game:
            logger.info(f"🧹 Modo forzado desactivado: {self.forced_game.get('name')}")
            self.forced_game = None

    def update_presence(self, game_info: Optional[dict]):
        if getattr(self, "forced_game", None):
            game_info = self.forced_game
            current_time = time.time()
            if not hasattr(self, "_last_forced_log") or current_time - self._last_forced_log > 300:
                logger.info(f"🔧 Modo forzado activo: {self.forced_game.get('name')}")
                self._last_forced_log = current_time

        if (hasattr(self, "_force_stop_time") and 
            getattr(self, "_last_forced_game", None) and 
            game_info and 
            game_info.get("name") == self._last_forced_game.get("name")):
            
            current_time = time.time()
            if current_time - self._force_stop_time < 10:
                logger.debug(f"⏸️  Evitando reconexión automática a {game_info.get('name')} tras detener forzado")
                try:
                    if self.rpc: self.rpc.clear()
                except Exception:
                    pass
                self.last_game = None
                return

        current_game = game_info or None
        game_changed = not self.is_same_game(self.last_game, current_game)
        
        status, group_size = None, None
        if current_game and current_game.get("steam_appid"):
            status, group_size = self.scraper.get_rich_presence()
        
        if current_game and current_game.get("name") in self.games_map:
            defaults = self.games_map[current_game["name"]]
            merged = {**defaults, **current_game}
            current_game = merged

        if current_game and current_game.get("name") is None:
            self.log_once("🛑 GeForce NOW está cerrado")
            self.close_fake_executable()
            try:
                if self.rpc: self.rpc.clear()
            except Exception:
                pass
            self.last_game = None
            return

        if game_changed:
            self.close_fake_executable()
            if current_game and current_game.get("executable_path"):
                self.launch_fake_executable(current_game["executable_path"])

        if not current_game:
            if self.last_game is not None:
                try:
                    if self.rpc: self.rpc.clear()
                except Exception:
                    pass
                self.last_game = None
            return

        client_id = current_game.get("client_id") or self.client_id
        
        should_change_client = True
        if (hasattr(self, "_force_stop_time") and 
            getattr(self, "_last_forced_game", None) and 
            current_game and 
            current_game.get("name") == self._last_forced_game.get("name")):
            
            current_time = time.time()
            if current_time - self._force_stop_time < 10:
                should_change_client = False
                client_id = self.client_id

        if self.rpc and getattr(self.rpc, "client_id", None) != client_id and should_change_client:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
            if client_id:
                self._connect_rpc(client_id)
                self.log_once(f"🔁 Cambiado client_id a {client_id}")

        def split_status(s):
            for sep in ["|", " - ", ":", "›", ">"]:
                if sep in s:
                    a, b = s.split(sep, 1)
                    return a.strip(), b.strip()
            return s.strip(), None

        details, state = (split_status(status) if status else (None, None))
        
        if group_size is not None:
            if group_size == 1:
                state = self.texts.get("playing_solo", "Playing solo")
            else:
                state = self.texts.get("playing_in_group", f"On a Group")
        
        rn = (current_game.get('name') or '').strip().lower()
        if rn in ["geforce now", "games", ""]:
            try:
                if self.rpc: self.rpc.clear()
            except:
                pass
            self.last_game = None
            return

        party_size_data = None
        if group_size is not None:
            party_size_data = [group_size, 4]
        elif current_game.get("party_size"):
            party_size_data = current_game.get("party_size")

        presence_data = {
            "details": details,
            "state": state,
            "large_image": current_game.get('image', 'steam'),
            "large_text": current_game.get('name'),
            "small_image": current_game.get("icon_key") if current_game.get("icon_key") else None
        }
        
        if party_size_data:
            presence_data["party_size"] = party_size_data

        try:
            if self.rpc:
                self.rpc.update(**{k: v for k, v in presence_data.items() if v})
        except Exception as e:
            msg = str(e).lower()
            logger.error(f"❌ Error actualizando Presence: {e}")
            if "pipe was closed" in msg or "socket.send()" in msg:
                try:
                    time.sleep(5) 
                    self._connect_rpc(client_id)
                    logger.info("🔁 Reconectado con Discord RPC tras error de socket")
                except Exception as e2:
                    logger.error(f"❌ Falló la reconexión a Discord RPC: {e2}")

        self.last_game = dict(current_game) if isinstance(current_game, dict) else current_game
        
        if (hasattr(self, "_force_stop_time") and 
            time.time() - self._force_stop_time >= 10):
            if hasattr(self, "_last_forced_game"):
                del self._last_forced_game
            if hasattr(self, "_force_stop_time"):
                del self._force_stop_time

    def is_same_game(self, g1: Optional[dict], g2: Optional[dict]) -> bool:
        if g1 is None and g2 is None:
            return True
        if (g1 is None) != (g2 is None):
            return False
        for k in ("client_id", "executable_path", "name"):
            if g1.get(k) != g2.get(k):
                return False
        return True
    
    def close(self):
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
                self.close_fake_executable()
                logger.info("🔴 Discord RPC cerrado correctamente.")
            except Exception:
                pass
