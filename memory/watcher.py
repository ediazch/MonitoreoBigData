#!/usr/bin/env python3
"""
watcher.py — File watcher automatico para aura-mem.
Monitorea cambios en el proyecto y los registra en memoria sin intervencion manual.

Uso (lo lanza VS Code automaticamente via tasks.json):
    python memory/watcher.py

Detiene con Ctrl+C — genera resumen de sesion al salir.
"""

import sys
import os
import time
import threading
import subprocess
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Auto-instalar watchdog si no esta disponible
# ---------------------------------------------------------------------------
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("[aura-mem] Instalando watchdog...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog", "--quiet"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

sys.path.insert(0, os.path.dirname(__file__))
from aura_mem import conectar, _sesion_activa, cmd_log
from session_log import cmd_start, cmd_end

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
PROYECTO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INACTIVIDAD_MINUTOS = 30  # cerrar sesion tras N minutos sin actividad

# Extensiones a monitorear
EXTENSIONES_WATCH = {".py", ".yaml", ".yml", ".csv", ".ipynb", ".json", ".txt", ".md"}

# Carpetas a ignorar
IGNORAR_DIRS = {
    "memory", ".git", "__pycache__", ".pytest_cache",
    "graphify-out", ".vscode", ".agents", ".claude",
    "node_modules", ".impeccable"
}

# Archivos a ignorar
IGNORAR_ARCHIVOS = {"memory.db", "memory_export.json", ".sesion_activa"}

# Buffer para no registrar el mismo archivo 2 veces en menos de 5 segundos
_buffer_cambios: dict[str, float] = {}
_buffer_lock = threading.Lock()
BUFFER_SEGUNDOS = 5

# Ultima actividad registrada
_ultima_actividad = datetime.now()
_ultima_actividad_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Handler de eventos
# ---------------------------------------------------------------------------

class AuraMemHandler(FileSystemEventHandler):

    def on_modified(self, event):
        if not event.is_directory:
            self._procesar(event.src_path, "modificado")

    def on_created(self, event):
        if not event.is_directory:
            self._procesar(event.src_path, "creado")

    def on_deleted(self, event):
        if not event.is_directory:
            self._procesar(event.src_path, "eliminado")

    def on_moved(self, event):
        if not event.is_directory:
            self._procesar(event.dest_path, "renombrado")

    def _procesar(self, ruta: str, accion: str) -> None:
        # Normalizar ruta
        ruta = os.path.normpath(ruta)
        nombre = os.path.basename(ruta)
        ext    = os.path.splitext(nombre)[1].lower()

        # Filtros
        if ext not in EXTENSIONES_WATCH:
            return
        if nombre in IGNORAR_ARCHIVOS:
            return
        partes = ruta.replace("\\", "/").split("/")
        if any(d in IGNORAR_DIRS for d in partes):
            return

        # Buffer anti-duplicados
        ahora = time.time()
        clave = f"{ruta}:{accion}"
        with _buffer_lock:
            if ahora - _buffer_cambios.get(clave, 0) < BUFFER_SEGUNDOS:
                return
            _buffer_cambios[clave] = ahora

        # Ruta relativa para el log
        try:
            ruta_rel = os.path.relpath(ruta, PROYECTO_ROOT)
        except ValueError:
            ruta_rel = nombre

        # Determinar tipo segun extension y accion
        tipo = _tipo_por_extension(ext, ruta_rel)
        mensaje = f"[AUTO] {accion.upper()}: {ruta_rel}"

        # Registrar en memoria
        try:
            cmd_log(mensaje, tipo)
        except Exception as e:
            print(f"[aura-mem] Error registrando: {e}")

        # Actualizar ultima actividad
        with _ultima_actividad_lock:
            global _ultima_actividad
            _ultima_actividad = datetime.now()

        print(f"[aura-mem] {datetime.now().strftime('%H:%M:%S')} | {tipo.upper():<12} | {ruta_rel}")


# ---------------------------------------------------------------------------
# Monitor de inactividad
# ---------------------------------------------------------------------------

def _monitor_inactividad():
    """
    Thread que cierra y reabre sesion tras N minutos de inactividad.
    Simula el SessionEnd hook de claude-mem.
    """
    while True:
        time.sleep(60)  # revisar cada minuto
        with _ultima_actividad_lock:
            diferencia = datetime.now() - _ultima_actividad
        if diferencia > timedelta(minutes=INACTIVIDAD_MINUTOS):
            print(f"\n[aura-mem] {INACTIVIDAD_MINUTOS} min sin actividad — cerrando sesion automaticamente...")
            try:
                cmd_end(resumen_manual=f"Sesion cerrada por inactividad ({INACTIVIDAD_MINUTOS} min)")
                time.sleep(2)
                cmd_start()
            except Exception as e:
                print(f"[aura-mem] Error en ciclo de sesion: {e}")
            # Resetear timer
            with _ultima_actividad_lock:
                global _ultima_actividad
                _ultima_actividad = datetime.now()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tipo_por_extension(ext: str, ruta: str) -> str:
    if "test" in ruta.lower():
        return "nota"
    if ext in {".py"}:
        return "resultado"
    if ext in {".yaml", ".yml"}:
        return "decision"
    if ext in {".csv", ".ipynb"}:
        return "resultado"
    if ext in {".json"}:
        return "nota"
    return "nota"


def _registrar_contexto_git() -> None:
    """Registra el ultimo commit de git al iniciar el watcher."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%h %s"],
            capture_output=True, text=True, cwd=PROYECTO_ROOT
        )
        if result.returncode == 0 and result.stdout.strip():
            cmd_log(f"[AUTO] Ultimo commit al iniciar: {result.stdout.strip()}", "nota")
    except Exception:
        pass


def _registrar_rama_activa() -> None:
    """Registra la rama activa de git."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=PROYECTO_ROOT
        )
        if result.returncode == 0 and result.stdout.strip():
            rama = result.stdout.strip()
            cmd_log(f"[AUTO] Rama activa: {rama}", "nota")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  AURA-MEM WATCHER — Iniciando...")
    print(f"  Proyecto : {PROYECTO_ROOT}")
    print(f"  Inactividad auto-close: {INACTIVIDAD_MINUTOS} min")
    print("=" * 60)

    # Iniciar sesion automaticamente
    cmd_start()

    # Registrar contexto git inicial
    _registrar_contexto_git()
    _registrar_rama_activa()

    # Iniciar monitor de inactividad en background
    t = threading.Thread(target=_monitor_inactividad, daemon=True)
    t.start()

    # Iniciar file watcher
    handler  = AuraMemHandler()
    observer = Observer()
    observer.schedule(handler, PROYECTO_ROOT, recursive=True)
    observer.start()

    print(f"\n  Monitoreando cambios en: {PROYECTO_ROOT}")
    print("  Presiona Ctrl+C para detener.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[aura-mem] Deteniendo watcher...")
        observer.stop()
        observer.join()
        cmd_end(resumen_manual="Sesion cerrada manualmente por el usuario (Ctrl+C)")
        print("[aura-mem] Sesion guardada. Hasta luego.")


if __name__ == "__main__":
    main()
