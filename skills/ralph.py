#!/usr/bin/env python3
"""
ralph.py — Adaptacion local de ralph-wiggum (anthropics/claude-code)
Loop iterativo de tareas automaticas para el proyecto.
Ejecuta una tarea repetidamente hasta que se cumpla el criterio de exito.

Modo hibrido:
    - Claude Code: usa .claude/skills/ralph-wiggum/ con Stop hooks nativos
    - Aura/VS Code: este script implementa el loop en Python puro

Uso:
    python skills/ralph.py run "<tarea>" --until "<criterio>" --max <N>
    python skills/ralph.py run-tests --until-green --max 10
    python skills/ralph.py run-script <script.py> --until "<texto>" --max 5
    python skills/ralph.py status
    python skills/ralph.py cancelar
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import cmd_log

SEP         = "=" * 65
ESTADO_FILE = os.path.join(os.path.dirname(__file__), "..", ".plan", "ralph_estado.json")
PROYECTO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Estado del loop
# ---------------------------------------------------------------------------

def _guardar_estado(estado: dict) -> None:
    os.makedirs(os.path.dirname(ESTADO_FILE), exist_ok=True)
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)


def _cargar_estado() -> dict | None:
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


def _limpiar_estado() -> None:
    if os.path.exists(ESTADO_FILE):
        os.remove(ESTADO_FILE)


# ---------------------------------------------------------------------------
# Ejecutor de iteraciones
# ---------------------------------------------------------------------------

def _ejecutar_comando(comando: str) -> tuple[int, str]:
    """Ejecuta un comando shell y retorna (codigo_salida, output)."""
    try:
        result = subprocess.run(
            comando, shell=True, capture_output=True,
            text=True, cwd=PROYECTO_ROOT, timeout=120
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT: comando excedio 120 segundos"
    except Exception as e:
        return -1, f"ERROR: {e}"


def _criterio_cumplido(output: str, criterio: str, codigo: int) -> bool:
    """Verifica si el criterio de exito se cumple."""
    if criterio == "EXIT_0":
        return codigo == 0
    if criterio == "TESTS_GREEN":
        return "passed" in output.lower() and "failed" not in output.lower() and "error" not in output.lower()
    return criterio.lower() in output.lower()


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_run(tarea: str, criterio: str, max_iter: int = 10, delay: int = 2) -> None:
    """
    Ejecuta una tarea en loop hasta que el criterio se cumpla.
    Equivalente al /ralph-loop de claude-code.
    """
    estado = {
        "tarea":       tarea,
        "criterio":    criterio,
        "max_iter":    max_iter,
        "iteracion":   0,
        "inicio":      datetime.now().isoformat(),
        "activo":      True,
        "historial":   [],
    }
    _guardar_estado(estado)

    print(f"\n{SEP}")
    print(f"  RALPH — Loop iterativo iniciado")
    print(f"  Tarea   : {tarea}")
    print(f"  Criterio: {criterio}")
    print(f"  Max iter: {max_iter}")
    print(SEP)

    cmd_log(f"[ralph] loop iniciado: {tarea[:60]} | criterio: {criterio}", "decision")

    for i in range(1, max_iter + 1):
        estado["iteracion"] = i
        _guardar_estado(estado)

        print(f"\n  [{i}/{max_iter}] Ejecutando...")
        codigo, output = _ejecutar_comando(tarea)

        # Mostrar output resumido
        lineas = output.splitlines()
        for linea in lineas[-10:]:
            print(f"  | {linea}")

        # Verificar criterio
        if _criterio_cumplido(output, criterio, codigo):
            print(f"\n  CRITERIO CUMPLIDO en iteracion {i}")
            cmd_log(f"[ralph] COMPLETADO en {i} iteraciones: {tarea[:60]}", "fase")
            estado["activo"] = False
            estado["resultado"] = "completado"
            _guardar_estado(estado)
            _limpiar_estado()
            break

        estado["historial"].append({
            "iteracion": i,
            "codigo": codigo,
            "output_resumen": output[-200:],
        })
        _guardar_estado(estado)

        if i < max_iter:
            print(f"\n  Criterio no cumplido. Reintentando en {delay}s...")
            time.sleep(delay)
    else:
        print(f"\n  Max iteraciones ({max_iter}) alcanzado sin cumplir criterio.")
        cmd_log(f"[ralph] TIMEOUT: {max_iter} iteraciones sin exito: {tarea[:60]}", "error")
        estado["activo"]   = False
        estado["resultado"] = "timeout"
        _guardar_estado(estado)

    print(SEP)


def cmd_run_tests(max_iter: int = 10) -> None:
    """
    Loop especializado para tests — corre pytest hasta que todos pasen.
    El caso de uso mas comun de ralph en este proyecto.
    """
    print(f"\n{SEP}")
    print("  RALPH — Loop TDD: ejecutar tests hasta que pasen")
    print(SEP)

    cmd_run(
        tarea    = "python -m pytest tests/ -v --tb=short",
        criterio = "TESTS_GREEN",
        max_iter = max_iter,
        delay    = 1
    )


def cmd_run_script(script: str, criterio: str, max_iter: int = 5) -> None:
    """Ejecuta un script Python en loop hasta que el output contenga el criterio."""
    cmd_run(
        tarea    = f"python {script}",
        criterio = criterio,
        max_iter = max_iter,
        delay    = 2
    )


def cmd_status() -> None:
    """Muestra el estado del loop actual."""
    estado = _cargar_estado()

    print(f"\n{SEP}")
    print("  RALPH — Estado del loop")
    print(SEP)

    if not estado:
        print("\n  Sin loop activo.")
        print("\n  EJEMPLOS DE USO:")
        print(f"  # Correr tests hasta que todos pasen (max 10 intentos):")
        print(f"  python skills/ralph.py run-tests --max 10")
        print()
        print(f"  # Loop personalizado:")
        print(f'  python skills/ralph.py run "python analisis_relacion.py" --until "662" --max 5')
        print()
        print(f"  # Loop sobre un script:")
        print(f'  python skills/ralph.py run-script src/limpieza.py --until "OK" --max 3')
    else:
        print(f"\n  Estado    : {'ACTIVO' if estado.get('activo') else 'FINALIZADO'}")
        print(f"  Tarea     : {estado['tarea']}")
        print(f"  Criterio  : {estado['criterio']}")
        print(f"  Iteracion : {estado['iteracion']} / {estado['max_iter']}")
        print(f"  Inicio    : {estado['inicio'][:19]}")
        print(f"  Resultado : {estado.get('resultado', 'en progreso')}")

        if estado.get("historial"):
            print(f"\n  HISTORIAL:")
            for h in estado["historial"][-3:]:
                print(f"  [{h['iteracion']}] codigo={h['codigo']} | {h['output_resumen'][-60:]}")

    print(SEP)


def cmd_cancelar() -> None:
    """Cancela el loop activo."""
    if os.path.exists(ESTADO_FILE):
        _limpiar_estado()
        print("\n  Loop cancelado.")
        cmd_log("[ralph] loop cancelado manualmente", "nota")
    else:
        print("\n  Sin loop activo para cancelar.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ralph: loop iterativo de tareas para Aura")
    sub    = parser.add_subparsers(dest="cmd")

    p_r = sub.add_parser("run",        help="Ejecutar tarea en loop hasta criterio")
    p_r.add_argument("tarea")
    p_r.add_argument("--until", default="EXIT_0", help="Criterio de exito (texto en output o EXIT_0 o TESTS_GREEN)")
    p_r.add_argument("--max",   type=int, default=10, help="Maximo de iteraciones")
    p_r.add_argument("--delay", type=int, default=2,  help="Segundos entre iteraciones")

    p_t = sub.add_parser("run-tests",  help="Loop hasta que todos los tests pasen")
    p_t.add_argument("--max", type=int, default=10)

    p_s = sub.add_parser("run-script", help="Loop sobre un script Python")
    p_s.add_argument("script")
    p_s.add_argument("--until", default="EXIT_0")
    p_s.add_argument("--max",   type=int, default=5)

    sub.add_parser("status",   help="Ver estado del loop")
    sub.add_parser("cancelar", help="Cancelar loop activo")

    args = parser.parse_args()

    if args.cmd == "run":
        cmd_run(args.tarea, args.until, args.max, args.delay)
    elif args.cmd == "run-tests":
        cmd_run_tests(args.max)
    elif args.cmd == "run-script":
        cmd_run_script(args.script, args.until, args.max)
    elif args.cmd == "status":
        cmd_status()
    elif args.cmd == "cancelar":
        cmd_cancelar()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
