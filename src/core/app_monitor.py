import psutil
import subprocess
import logging

logger = logging.getLogger('geforce_presence')

class AppMonitor:
    @staticmethod
    def is_process_running(name: str) -> bool:
        for proc in psutil.process_iter(attrs=['name']):
            if name.lower() in (proc.info['name'] or "").lower():
                return True
        return False

    @staticmethod
    def kill_process(name: str):
        for proc in psutil.process_iter(attrs=['name']):
            if name.lower() in (proc.info['name'] or "").lower():
                try:
                    proc.kill()
                    logger.info(f"💀 Proceso {name} cerrado.")
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logger.error(f"⚠️ No se pudo cerrar {name}: {e}")

    @staticmethod
    def monitor_geforce_and_dumb():
        if not AppMonitor.is_process_running("GeForceNOW.exe"):
            AppMonitor.kill_process("dumb.exe")

    @staticmethod
    def launch_dumb(path_dumb: str):
        AppMonitor.kill_process("dumb.exe")
        subprocess.Popen([path_dumb])
        logger.info("🚀 dumb.exe iniciado.")
