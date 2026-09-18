#!/usr/bin/env python3
"""
aura_mem.py — Motor principal de memoria persistente para MonitoreoBigData.
Adaptado de los conceptos de claude-mem (thedotmack/claude-mem).

Uso:
    python memory/aura_mem.py log "<mensaje>" [--tipo <tipo>]
    python memory/aura_mem.py list [--tipo <tipo>] [--limit N]
    python memory/aura_mem.py resumen
    python memory/aura_mem.py borrar <id>
    python memory/aura_mem.py exportar

Tipos de observacion (tomados de claude-mem):
    decision    - Decisiones de arquitectura o diseno
    fase        - Completar una fase del plan de trabajo
    bugfix      - Bug encontrado y solucionado
    nota        - Nota general de contexto
    error       - Error encontrado (sin solucion aun)
    instalacion - Herramienta o skill instalado
    resultado   - Resultado de analisis o ejecucion
"""

import sqlite3
import argparse
import os
import sys
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
DB_PATH    = os.path.join(os.path.dirname(__file__), "memory.db")
TIPOS_VALIDOS = {"decision", "fase", "bugfix", "nota", "error", "instalacion", "resultado"}
PRIVATE_TAG   = "<private>"


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

def conectar() -> sqlite3.Connection:
    """Conecta a SQLite y crea tablas si no existen."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _inicializar(conn)
    return conn


def _inicializar(conn: sqlite3.Connection) -> None:
    """Crea esquema inicial. FTS5 para busqueda full-text (igual que claude-mem)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS observaciones (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo      TEXT    NOT NULL DEFAULT 'nota',
            mensaje   TEXT    NOT NULL,
            sesion_id TEXT    NOT NULL,
            proyecto  TEXT    NOT NULL DEFAULT 'MonitoreoBigData',
            fecha     TEXT    NOT NULL,
            privado   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sesiones (
            id        TEXT PRIMARY KEY,
            inicio    TEXT NOT NULL,
            fin       TEXT,
            resumen   TEXT,
            num_obs   INTEGER DEFAULT 0
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS obs_fts
        USING fts5(mensaje, tipo, sesion_id, content=observaciones, content_rowid=id);

        CREATE TRIGGER IF NOT EXISTS obs_ai AFTER INSERT ON observaciones BEGIN
            INSERT INTO obs_fts(rowid, mensaje, tipo, sesion_id)
            VALUES (new.id, new.mensaje, new.tipo, new.sesion_id);
        END;

        CREATE TRIGGER IF NOT EXISTS obs_ad AFTER DELETE ON observaciones BEGIN
            INSERT INTO obs_fts(obs_fts, rowid, mensaje, tipo, sesion_id)
            VALUES ('delete', old.id, old.mensaje, old.tipo, old.sesion_id);
        END;
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Sesion activa
# ---------------------------------------------------------------------------

def _sesion_activa(conn: sqlite3.Connection) -> str:
    """Retorna el ID de sesion activa o crea una nueva."""
    sesion_file = os.path.join(os.path.dirname(__file__), ".sesion_activa")
    if os.path.exists(sesion_file):
        with open(sesion_file) as f:
            sid = f.read().strip()
        row = conn.execute("SELECT id FROM sesiones WHERE id=? AND fin IS NULL", (sid,)).fetchone()
        if row:
            return sid

    # Crear nueva sesion
    sid   = datetime.now().strftime("SES-%Y%m%d-%H%M%S")
    ahora = datetime.now().isoformat()
    conn.execute("INSERT INTO sesiones (id, inicio) VALUES (?, ?)", (sid, ahora))
    conn.commit()
    with open(sesion_file, "w") as f:
        f.write(sid)
    return sid


# ---------------------------------------------------------------------------
# Operaciones principales
# ---------------------------------------------------------------------------

def cmd_log(mensaje: str, tipo: str = "nota") -> None:
    """Guarda una observacion. Filtra contenido <private>."""
    if tipo not in TIPOS_VALIDOS:
        print(f"[ERROR] Tipo invalido: '{tipo}'. Validos: {', '.join(sorted(TIPOS_VALIDOS))}")
        sys.exit(1)

    privado = 1 if PRIVATE_TAG in mensaje else 0
    if privado:
        mensaje = mensaje.replace(PRIVATE_TAG, "[PRIVADO]")

    conn  = conectar()
    sid   = _sesion_activa(conn)
    ahora = datetime.now().isoformat()

    conn.execute(
        "INSERT INTO observaciones (tipo, mensaje, sesion_id, fecha, privado) VALUES (?, ?, ?, ?, ?)",
        (tipo, mensaje, sid, ahora, privado)
    )
    conn.execute(
        "UPDATE sesiones SET num_obs = num_obs + 1 WHERE id = ?", (sid,)
    )
    conn.commit()
    conn.close()

    icono = _icono(tipo)
    print(f"{icono} [{tipo.upper()}] Guardado en sesion {sid}")
    print(f"   {mensaje[:100]}{'...' if len(mensaje) > 100 else ''}")


def cmd_list(tipo: str = None, limit: int = 20, mostrar_privados: bool = False) -> None:
    """Lista observaciones recientes."""
    conn = conectar()
    query = "SELECT id, tipo, mensaje, fecha, sesion_id, privado FROM observaciones"
    params = []
    if tipo:
        query += " WHERE tipo = ?"
        params.append(tipo)
    query += " ORDER BY fecha DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print("  (sin observaciones guardadas)")
        return

    print(f"\n{'ID':<5} {'TIPO':<12} {'FECHA':<22} {'MENSAJE'}")
    print(f"{'-'*5} {'-'*12} {'-'*22} {'-'*50}")
    for r in rows:
        if r["privado"] and not mostrar_privados:
            msg = "[CONTENIDO PRIVADO]"
        else:
            msg = r["mensaje"][:60] + ("..." if len(r["mensaje"]) > 60 else "")
        fecha = r["fecha"][:19].replace("T", " ")
        icono = _icono(r["tipo"])
        print(f"{r['id']:<5} {icono}{r['tipo']:<11} {fecha:<22} {msg}")


def cmd_resumen() -> None:
    """Muestra resumen estadistico de la memoria — concepto de progressive disclosure de claude-mem."""
    conn = conectar()

    total  = conn.execute("SELECT COUNT(*) FROM observaciones").fetchone()[0]
    sesiones = conn.execute("SELECT COUNT(*) FROM sesiones").fetchone()[0]

    print(f"\n{'='*60}")
    print(f"  AURA-MEM — Resumen de Memoria del Proyecto")
    print(f"{'='*60}")
    print(f"  Total observaciones : {total}")
    print(f"  Total sesiones      : {sesiones}")
    print()

    # Por tipo
    print(f"  {'TIPO':<15} {'CANTIDAD':>10}  {'BARRA'}")
    print(f"  {'-'*15} {'-'*10}  {'-'*20}")
    rows = conn.execute(
        "SELECT tipo, COUNT(*) as cnt FROM observaciones GROUP BY tipo ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        barra = "#" * min(r["cnt"], 20)
        print(f"  {_icono(r['tipo'])}{r['tipo']:<14} {r['cnt']:>10}  {barra}")

    # Ultimas sesiones
    print(f"\n  ULTIMAS SESIONES:")
    print(f"  {'-'*55}")
    sesiones_rows = conn.execute(
        "SELECT id, inicio, fin, num_obs, resumen FROM sesiones ORDER BY inicio DESC LIMIT 5"
    ).fetchall()
    for s in sesiones_rows:
        estado = "ACTIVA" if not s["fin"] else "cerrada"
        inicio = s["inicio"][:19].replace("T", " ")
        print(f"  [{estado}] {s['id']} | {inicio} | {s['num_obs']} obs")
        if s["resumen"]:
            print(f"    Resumen: {s['resumen'][:80]}")

    conn.close()
    print(f"{'='*60}\n")


def cmd_exportar() -> None:
    """Exporta toda la memoria a JSON — util para backup o migracion."""
    conn  = conectar()
    rows  = conn.execute("SELECT * FROM observaciones ORDER BY fecha").fetchall()
    datos = [dict(r) for r in rows]
    conn.close()

    export_path = os.path.join(os.path.dirname(__file__), "memory_export.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"  Exportado: {len(datos)} observaciones -> {export_path}")


def cmd_borrar(obs_id: int) -> None:
    """Elimina una observacion por ID."""
    conn = conectar()
    row  = conn.execute("SELECT id, mensaje FROM observaciones WHERE id=?", (obs_id,)).fetchone()
    if not row:
        print(f"[ERROR] No existe observacion con id={obs_id}")
        conn.close()
        return
    conn.execute("DELETE FROM observaciones WHERE id=?", (obs_id,))
    conn.commit()
    conn.close()
    print(f"  Eliminada observacion #{obs_id}: {row['mensaje'][:60]}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _icono(tipo: str) -> str:
    return {
        "decision":    "[>] ",
        "fase":        "[F] ",
        "bugfix":      "[B] ",
        "nota":        "[N] ",
        "error":       "[!] ",
        "instalacion": "[I] ",
        "resultado":   "[R] ",
    }.get(tipo, "[ ] ")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="aura-mem: memoria persistente para MonitoreoBigData",
        formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd")

    # log
    p_log = sub.add_parser("log", help="Guardar una observacion")
    p_log.add_argument("mensaje", help="Texto de la observacion")
    p_log.add_argument("--tipo", default="nota", choices=sorted(TIPOS_VALIDOS),
                       help="Tipo de observacion (default: nota)")

    # list
    p_list = sub.add_parser("list", help="Listar observaciones")
    p_list.add_argument("--tipo", choices=sorted(TIPOS_VALIDOS), help="Filtrar por tipo")
    p_list.add_argument("--limit", type=int, default=20, help="Maximo de resultados")

    # resumen
    sub.add_parser("resumen", help="Ver resumen estadistico de la memoria")

    # exportar
    sub.add_parser("exportar", help="Exportar toda la memoria a JSON")

    # borrar
    p_del = sub.add_parser("borrar", help="Eliminar observacion por ID")
    p_del.add_argument("id", type=int, help="ID de la observacion")

    args = parser.parse_args()

    if args.cmd == "log":
        cmd_log(args.mensaje, args.tipo)
    elif args.cmd == "list":
        cmd_list(tipo=args.tipo, limit=args.limit)
    elif args.cmd == "resumen":
        cmd_resumen()
    elif args.cmd == "exportar":
        cmd_exportar()
    elif args.cmd == "borrar":
        cmd_borrar(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
