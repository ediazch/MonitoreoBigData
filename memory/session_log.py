#!/usr/bin/env python3
"""
session_log.py — Gestion de sesiones de trabajo para aura-mem.
Adaptado del concepto SessionStart/SessionEnd de claude-mem.

Uso:
    python memory/session_log.py start              <- inicia sesion y muestra contexto previo
    python memory/session_log.py end                <- cierra sesion y genera resumen
    python memory/session_log.py status             <- muestra sesion activa
    python memory/session_log.py historial          <- muestra todas las sesiones
"""

import sqlite3
import os
import sys
from datetime import datetime

# Reutilizamos el motor de aura_mem
sys.path.insert(0, os.path.dirname(__file__))
from aura_mem import conectar, _sesion_activa, _icono, cmd_resumen
from compresor import comprimir_sesion, comprimir_automatico, UMBRAL_COMPRIMIR

SESION_FILE = os.path.join(os.path.dirname(__file__), ".sesion_activa")
SEP = "=" * 60


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_start() -> None:
    """
    Inicia una nueva sesion de trabajo.
    Muestra contexto de sesiones anteriores (como SessionStart hook de claude-mem).
    """
    conn = conectar()

    # Cerrar sesion previa si existe y esta abierta
    if os.path.exists(SESION_FILE):
        with open(SESION_FILE) as f:
            sid_prev = f.read().strip()
        row = conn.execute("SELECT id FROM sesiones WHERE id=? AND fin IS NULL", (sid_prev,)).fetchone()
        if row:
            _cerrar_sesion(conn, sid_prev, auto=True)

    # Crear nueva sesion
    sid   = datetime.now().strftime("SES-%Y%m%d-%H%M%S")
    ahora = datetime.now().isoformat()
    conn.execute("INSERT INTO sesiones (id, inicio) VALUES (?, ?)", (sid, ahora))
    conn.commit()
    with open(SESION_FILE, "w") as f:
        f.write(sid)

    print(f"\n{SEP}")
    print(f"  AURA-MEM — Nueva Sesion Iniciada")
    print(f"  ID     : {sid}")
    print(f"  Inicio : {ahora[:19].replace('T', ' ')}")
    print(SEP)

    # Mostrar contexto previo relevante (progressive disclosure de claude-mem)
    _mostrar_contexto_previo(conn)
    conn.close()


def cmd_end(resumen_manual: str = None) -> None:
    """
    Cierra la sesion activa y genera un resumen automatico.
    Equivalente al SessionEnd hook de claude-mem.
    """
    conn = conectar()

    if not os.path.exists(SESION_FILE):
        print("[ERROR] No hay sesion activa. Ejecuta: python memory/session_log.py start")
        conn.close()
        return

    with open(SESION_FILE) as f:
        sid = f.read().strip()

    row = conn.execute("SELECT id, inicio, num_obs FROM sesiones WHERE id=?", (sid,)).fetchone()
    if not row:
        print(f"[ERROR] Sesion {sid} no encontrada en base de datos.")
        conn.close()
        return

    _cerrar_sesion(conn, sid, resumen_manual=resumen_manual)
    conn.close()

    # Eliminar archivo de sesion activa
    os.remove(SESION_FILE)
    print(f"\n  Sesion {sid} cerrada correctamente.")


def cmd_status() -> None:
    """Muestra el estado de la sesion activa."""
    conn = conectar()

    if not os.path.exists(SESION_FILE):
        print("\n  No hay sesion activa.")
        print("  Inicia una con: python memory/session_log.py start")
        conn.close()
        return

    with open(SESION_FILE) as f:
        sid = f.read().strip()

    row = conn.execute(
        "SELECT id, inicio, num_obs FROM sesiones WHERE id=?", (sid,)
    ).fetchone()

    if not row:
        print(f"\n  Sesion {sid} registrada pero no encontrada en DB.")
        conn.close()
        return

    inicio = row["inicio"][:19].replace("T", " ")
    ahora  = datetime.now()
    inicio_dt = datetime.fromisoformat(row["inicio"])
    duracion = ahora - inicio_dt
    minutos  = int(duracion.total_seconds() // 60)

    print(f"\n{SEP}")
    print(f"  SESION ACTIVA")
    print(f"  ID          : {row['id']}")
    print(f"  Inicio      : {inicio}")
    print(f"  Duracion    : {minutos} minutos")
    print(f"  Observaciones registradas: {row['num_obs']}")
    print(SEP)

    # Ultimas 5 observaciones de esta sesion
    obs = conn.execute(
        "SELECT tipo, mensaje, fecha FROM observaciones WHERE sesion_id=? ORDER BY fecha DESC LIMIT 5",
        (sid,)
    ).fetchall()

    if obs:
        print("\n  ULTIMAS OBSERVACIONES DE ESTA SESION:")
        for o in obs:
            fecha = o["fecha"][:19].replace("T", " ")
            msg   = o["mensaje"][:55] + ("..." if len(o["mensaje"]) > 55 else "")
            print(f"  {_icono(o['tipo'])}[{o['tipo']:<12}] {fecha} | {msg}")

    conn.close()


def cmd_historial() -> None:
    """Lista todas las sesiones registradas."""
    conn  = conectar()
    rows  = conn.execute(
        "SELECT id, inicio, fin, num_obs, resumen FROM sesiones ORDER BY inicio DESC LIMIT 20"
    ).fetchall()
    conn.close()

    if not rows:
        print("\n  (sin sesiones registradas)")
        return

    print(f"\n{SEP}")
    print(f"  HISTORIAL DE SESIONES")
    print(SEP)
    print(f"  {'SESION':<22} {'INICIO':<20} {'OBS':>5}  {'ESTADO':<10}  RESUMEN")
    print(f"  {'-'*22} {'-'*20} {'-'*5}  {'-'*10}  {'-'*30}")

    for s in rows:
        estado  = "ACTIVA  " if not s["fin"] else "cerrada "
        inicio  = s["inicio"][:19].replace("T", " ")
        resumen = (s["resumen"] or "")[:40]
        print(f"  {s['id']:<22} {inicio:<20} {s['num_obs']:>5}  {estado:<10}  {resumen}")

    print(SEP)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _cerrar_sesion(conn: sqlite3.Connection, sid: str, resumen_manual: str = None, auto: bool = False) -> None:
    """Genera resumen y cierra la sesion."""
    obs = conn.execute(
        "SELECT tipo, mensaje FROM observaciones WHERE sesion_id=? ORDER BY fecha",
        (sid,)
    ).fetchall()

    if resumen_manual:
        resumen = resumen_manual
    else:
        resumen = _generar_resumen_local(obs)

    ahora = datetime.now().isoformat()
    conn.execute(
        "UPDATE sesiones SET fin=?, resumen=? WHERE id=?",
        (ahora, resumen, sid)
    )
    conn.commit()

    tag = "[AUTO-CERRADA]" if auto else "[CERRADA]"
    print(f"\n{SEP}")
    print(f"  {tag} Sesion: {sid}")
    print(f"  Observaciones guardadas: {len(obs)}")
    print(f"  Resumen inicial: {resumen}")
    print(SEP)

    # Compresion automatica si supera el umbral
    if len(obs) >= UMBRAL_COMPRIMIR:
        print(f"\n[compresor] {len(obs)} obs >= umbral ({UMBRAL_COMPRIMIR}) — comprimiendo automaticamente...")
        comprimir_sesion(sid, verbose=True)
    else:
        print(f"[compresor] {len(obs)} obs < umbral ({UMBRAL_COMPRIMIR}) — sin compresion necesaria.")


def _generar_resumen_local(obs: list) -> str:
    """
    Genera resumen sin API key.
    Concepto adaptado de la compresion semantica de claude-mem
    pero implementado localmente con conteo y extraccion de keywords.
    """
    if not obs:
        return "Sesion sin observaciones registradas."

    conteo = {}
    for o in obs:
        conteo[o["tipo"]] = conteo.get(o["tipo"], 0) + 1

    partes = []
    if conteo.get("fase"):
        partes.append(f"{conteo['fase']} fase(s) completada(s)")
    if conteo.get("resultado"):
        partes.append(f"{conteo['resultado']} resultado(s) registrado(s)")
    if conteo.get("bugfix"):
        partes.append(f"{conteo['bugfix']} bug(s) resuelto(s)")
    if conteo.get("instalacion"):
        partes.append(f"{conteo['instalacion']} herramienta(s) instalada(s)")
    if conteo.get("decision"):
        partes.append(f"{conteo['decision']} decision(es) tomada(s)")
    if conteo.get("error"):
        partes.append(f"{conteo['error']} error(es) pendiente(s)")
    if conteo.get("nota"):
        partes.append(f"{conteo['nota']} nota(s) general(es)")

    total = len(obs)
    resumen_tipos = ", ".join(partes) if partes else "observaciones generales"
    return f"{total} obs: {resumen_tipos}."


def _mostrar_contexto_previo(conn: sqlite3.Connection) -> None:
    """
    Muestra contexto de sesiones anteriores al iniciar.
    Implementa el concepto de 'progressive disclosure' de claude-mem:
    primero resumen, luego detalle si se necesita.
    """
    # Ultimas 3 sesiones cerradas
    sesiones = conn.execute(
        "SELECT id, inicio, resumen, num_obs FROM sesiones WHERE fin IS NOT NULL ORDER BY inicio DESC LIMIT 3"
    ).fetchall()

    if not sesiones:
        print("\n  Primera sesion del proyecto. No hay contexto previo.")
        return

    print("\n  CONTEXTO DE SESIONES ANTERIORES (ultimas 3):")
    print(f"  {'-'*55}")
    for s in sesiones:
        inicio = s["inicio"][:10]
        print(f"  [{inicio}] {s['id']} | {s['num_obs']} obs")
        if s["resumen"]:
            print(f"    -> {s['resumen']}")

    # Observaciones criticas recientes (decision + bugfix no resuelto)
    criticas = conn.execute("""
        SELECT tipo, mensaje, fecha FROM observaciones
        WHERE tipo IN ('decision', 'error')
        ORDER BY fecha DESC LIMIT 5
    """).fetchall()

    if criticas:
        print(f"\n  ITEMS CRITICOS RECIENTES:")
        print(f"  {'-'*55}")
        for o in criticas:
            fecha = o["fecha"][:10]
            msg   = o["mensaje"][:60] + ("..." if len(o["mensaje"]) > 60 else "")
            print(f"  {_icono(o['tipo'])}[{fecha}] {msg}")

    print(f"\n  Usa 'python memory/mem_search.py <query>' para buscar contexto especifico.")
    print(SEP)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="session_log: gestion de sesiones aura-mem")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("start",    help="Iniciar nueva sesion de trabajo")
    p_end = sub.add_parser("end", help="Cerrar sesion activa con resumen")
    p_end.add_argument("--resumen", default=None, help="Resumen manual de la sesion")
    sub.add_parser("status",   help="Ver sesion activa actual")
    sub.add_parser("historial",help="Ver historial de sesiones")

    args = parser.parse_args()

    if args.cmd == "start":
        cmd_start()
    elif args.cmd == "end":
        cmd_end(resumen_manual=args.resumen)
    elif args.cmd == "status":
        cmd_status()
    elif args.cmd == "historial":
        cmd_historial()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
