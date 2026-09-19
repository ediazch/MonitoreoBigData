#!/usr/bin/env python3
"""
task_observer.py — Adaptacion local de task-observer (rebelytics/one-skill-to-rule-them-all)
Observa la sesion de trabajo, detecta patrones y sugiere mejoras a skills existentes.
Se integra con aura-mem para persistir observaciones automaticamente.

Modo hibrido:
    - Claude Code: usa .claude/skills/task-observer/SKILL.md (automatico)
    - Aura/VS Code: usa este script (manual o via watcher)

Uso:
    python skills/task_observer.py observar "<que hiciste>"
    python skills/task_observer.py sugerir
    python skills/task_observer.py patrones
    python skills/task_observer.py revisar
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import conectar, cmd_log

SEP = "=" * 65
OBS_DIR = os.path.join(os.path.dirname(__file__), "..", "memory", "skill_observations")

# ---------------------------------------------------------------------------
# Patrones que task-observer detecta (adaptados del SKILL.md original)
# ---------------------------------------------------------------------------
PATRONES_CONOCIDOS = {
    "repeticion": {
        "descripcion": "Misma accion ejecutada 3+ veces — candidato a skill",
        "umbral": 3,
    },
    "correccion": {
        "descripcion": "Output corregido manualmente — skill necesita mejora",
        "umbral": 1,
    },
    "gap": {
        "descripcion": "Tarea sin skill que la cubra — candidato a skill nuevo",
        "umbral": 1,
    },
    "error_recurrente": {
        "descripcion": "Mismo error 2+ veces — documentar solucion como skill",
        "umbral": 2,
    },
}

SKILLS_DISPONIBLES = [
    "aura-mem", "graphify", "task-observer", "impeccable",
    "superpowers", "find-skills", "test-driven-development",
    "systematic-debugging", "writing-plans", "brainstorming",
]


# ---------------------------------------------------------------------------
# Comandos principales
# ---------------------------------------------------------------------------

def cmd_observar(descripcion: str) -> None:
    """
    Registra una observacion de trabajo en aura-mem y en el log de task-observer.
    Equivalente al observation-log de one-skill-to-rule-them-all.
    """
    ahora   = datetime.now().isoformat()
    entrada = {
        "fecha":       ahora,
        "descripcion": descripcion,
        "tipo":        _clasificar_observacion(descripcion),
    }

    # Guardar en aura-mem
    tipo_mem = "decision" if "decid" in descripcion.lower() else "nota"
    cmd_log(f"[task-observer] {descripcion}", tipo_mem)

    # Guardar en log propio de task-observer
    os.makedirs(OBS_DIR, exist_ok=True)
    log_file = os.path.join(OBS_DIR, f"{datetime.now().strftime('%Y-%m')}.json")
    observaciones = _leer_log(log_file)
    observaciones.append(entrada)
    _escribir_log(log_file, observaciones)

    print(f"\n[task-observer] Observacion registrada:")
    print(f"  Tipo : {entrada['tipo']}")
    print(f"  Desc : {descripcion}")
    print(f"  Fecha: {ahora[:19].replace('T',' ')}")


def cmd_sugerir() -> None:
    """
    Analiza observaciones acumuladas y sugiere mejoras a skills.
    Equivalente al 'proposed skill updates' de one-skill-to-rule-them-all.
    """
    conn = conectar()
    obs  = conn.execute(
        "SELECT tipo, mensaje, fecha FROM observaciones ORDER BY fecha DESC LIMIT 50"
    ).fetchall()
    conn.close()

    if not obs:
        print("\n[task-observer] Sin observaciones suficientes para sugerir mejoras.")
        return

    print(f"\n{SEP}")
    print("  TASK-OBSERVER — Sugerencias de mejora")
    print(SEP)

    # Detectar errores recurrentes
    errores = [o for o in obs if o["tipo"] == "error"]
    if len(errores) >= 2:
        print(f"\n  [!] ERRORES RECURRENTES ({len(errores)} encontrados):")
        print(f"      Sugerencia: crear skill 'manejo-errores-{_fecha_corta()}'")
        for e in errores[:3]:
            print(f"      - {e['mensaje'][:80]}")

    # Detectar gaps (acciones sin skill)
    notas = [o for o in obs if o["tipo"] == "nota"]
    autos = [o for o in notas if "[AUTO]" in o["mensaje"]]
    if len(autos) >= 5:
        archivos = Counter(
            o["mensaje"].split(":")[-1].strip()[:30]
            for o in autos if ":" in o["mensaje"]
        )
        mas_comunes = archivos.most_common(3)
        print(f"\n  [>] ARCHIVOS MAS MODIFICADOS (posible skill faltante):")
        for archivo, cnt in mas_comunes:
            print(f"      - {archivo} ({cnt} modificaciones)")
        print(f"      Sugerencia: documentar workflow de '{mas_comunes[0][0] if mas_comunes else 'archivo'}' como skill")

    # Detectar fases completadas sin documentar
    fases = [o for o in obs if o["tipo"] == "fase"]
    if fases:
        print(f"\n  [F] FASES COMPLETADAS ({len(fases)}) — bien documentadas en aura-mem")

    # Skills sugeridos
    print(f"\n  [*] SKILLS RECOMENDADOS PARA ESTE PROYECTO:")
    sugeridos = _sugerir_skills_por_contexto(obs)
    for s in sugeridos:
        print(f"      - {s['skill']}: {s['razon']}")

    print(SEP)


def cmd_patrones() -> None:
    """
    Detecta patrones en el historial de observaciones.
    Equivalente al analisis de patrones de one-skill-to-rule-them-all.
    """
    conn = conectar()
    obs  = conn.execute(
        "SELECT tipo, mensaje, fecha, sesion_id FROM observaciones ORDER BY fecha"
    ).fetchall()
    conn.close()

    if not obs:
        print("\n[task-observer] Sin datos suficientes para detectar patrones.")
        return

    print(f"\n{SEP}")
    print("  TASK-OBSERVER — Patrones detectados")
    print(SEP)

    # Patron 1: distribucion por tipo
    conteo = Counter(o["tipo"] for o in obs)
    print(f"\n  DISTRIBUCION DE ACTIVIDAD:")
    total = len(obs)
    for tipo, cnt in conteo.most_common():
        pct   = round(cnt / total * 100)
        barra = "#" * min(pct, 30)
        print(f"  {tipo:<14} {cnt:>4} obs  {barra} {pct}%")

    # Patron 2: actividad por hora del dia
    horas = Counter(
        datetime.fromisoformat(o["fecha"]).hour
        for o in obs
    )
    hora_pico = max(horas, key=horas.get) if horas else 0
    print(f"\n  HORA DE MAYOR ACTIVIDAD: {hora_pico:02d}:00 — {horas.get(hora_pico,0)} observaciones")

    # Patron 3: sesiones
    sesiones = len(set(o["sesion_id"] for o in obs))
    promedio = round(total / sesiones, 1) if sesiones else 0
    print(f"\n  SESIONES TOTALES     : {sesiones}")
    print(f"  PROMEDIO OBS/SESION  : {promedio}")

    # Patron 4: gaps detectados
    instalaciones = [o for o in obs if o["tipo"] == "instalacion"]
    if instalaciones:
        print(f"\n  HERRAMIENTAS INSTALADAS ({len(instalaciones)}):")
        for i in instalaciones:
            print(f"  - {i['mensaje'][:70]}")

    print(SEP)


def cmd_revisar() -> None:
    """
    Revision semanal de skills — equivalente al weekly-review de one-skill-to-rule-them-all.
    Sugiere que skills actualizar, cuales estan obsoletos y cuales crear.
    """
    conn  = conectar()
    desde = (datetime.now() - timedelta(days=7)).isoformat()
    obs   = conn.execute(
        "SELECT tipo, mensaje, fecha FROM observaciones WHERE fecha >= ? ORDER BY fecha",
        (desde,)
    ).fetchall()
    conn.close()

    print(f"\n{SEP}")
    print("  TASK-OBSERVER — Revision semanal de skills")
    print(f"  Periodo: ultimos 7 dias | {len(obs)} observaciones")
    print(SEP)

    if not obs:
        print("\n  Sin actividad en los ultimos 7 dias.")
        print(SEP)
        return

    # Skills usados esta semana
    print(f"\n  SKILLS ACTIVOS ESTA SEMANA:")
    for skill in SKILLS_DISPONIBLES:
        usos = sum(1 for o in obs if skill.lower() in o["mensaje"].lower())
        if usos > 0:
            print(f"  [+] {skill:<30} {usos} referencias")

    # Acciones sin skill
    sin_skill = [o for o in obs if not any(
        s.lower() in o["mensaje"].lower() for s in SKILLS_DISPONIBLES
    )]
    if sin_skill:
        print(f"\n  ACTIVIDAD SIN SKILL ASIGNADO ({len(sin_skill)} obs):")
        print(f"      -> Considerar crear skills para estas areas")
        for o in sin_skill[:5]:
            print(f"      - [{o['tipo']}] {o['mensaje'][:70]}")

    # Recomendacion final
    print(f"\n  RECOMENDACION:")
    if len(obs) > 20:
        print(f"  Alta actividad — ejecutar 'python memory/compresor.py --auto' para comprimir")
    if any(o["tipo"] == "error" for o in obs):
        print(f"  Errores detectados — revisar skill 'systematic-debugging'")
    if not any("test" in o["mensaje"].lower() for o in obs):
        print(f"  Sin actividad de testing — aplicar skill 'test-driven-development'")

    print(SEP)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clasificar_observacion(texto: str) -> str:
    texto_lower = texto.lower()
    if any(w in texto_lower for w in ["error", "fallo", "bug", "problema"]):
        return "correccion"
    if any(w in texto_lower for w in ["repeti", "siempre", "cada vez"]):
        return "repeticion"
    if any(w in texto_lower for w in ["no hay skill", "falta", "sin skill"]):
        return "gap"
    return "observacion"


def _sugerir_skills_por_contexto(obs: list) -> list[dict]:
    sugeridos = []
    mensajes  = " ".join(o["mensaje"].lower() for o in obs)

    if "test" not in mensajes and "prueba" not in mensajes:
        sugeridos.append({
            "skill": "test-driven-development",
            "razon": "No se detecta actividad de testing en las observaciones"
        })
    if "git" in mensajes and "commit" in mensajes:
        sugeridos.append({
            "skill": "using-git-worktrees",
            "razon": "Actividad git detectada — worktrees mejoran el flujo"
        })
    if "diseno" in mensajes or "dashboard" in mensajes or "html" in mensajes:
        sugeridos.append({
            "skill": "impeccable",
            "razon": "Actividad de UI detectada — impeccable mejora el diseno"
        })
    if "error" in mensajes:
        sugeridos.append({
            "skill": "systematic-debugging",
            "razon": "Errores detectados — usar metodologia sistematica"
        })
    return sugeridos


def _leer_log(path: str) -> list:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def _escribir_log(path: str, datos: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def _fecha_corta() -> str:
    return datetime.now().strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="task-observer: adaptacion hibrida para Aura")
    sub    = parser.add_subparsers(dest="cmd")

    p_obs = sub.add_parser("observar", help="Registrar una observacion de trabajo")
    p_obs.add_argument("descripcion", help="Que hiciste o que notaste")

    sub.add_parser("sugerir",  help="Sugerir mejoras a skills basado en observaciones")
    sub.add_parser("patrones", help="Detectar patrones en el historial")
    sub.add_parser("revisar",  help="Revision semanal de skills")

    args = parser.parse_args()

    if args.cmd == "observar":
        cmd_observar(args.descripcion)
    elif args.cmd == "sugerir":
        cmd_sugerir()
    elif args.cmd == "patrones":
        cmd_patrones()
    elif args.cmd == "revisar":
        cmd_revisar()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
