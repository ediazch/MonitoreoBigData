#!/usr/bin/env python3
"""
mem_search.py — Busqueda en la memoria persistente de aura-mem.
Adaptado del mem-search skill de claude-mem (busqueda 3 capas).

Uso:
    python memory/mem_search.py "<query>"
    python memory/mem_search.py "<query>" --tipo <tipo>
    python memory/mem_search.py "<query>" --detalle
    python memory/mem_search.py "<query>" --desde 2026-09-01
    python memory/mem_search.py --recientes
    python memory/mem_search.py --todo

Flujo de 3 capas (adaptado de claude-mem progressive disclosure):
    1. Resultado compacto con IDs  (por defecto)
    2. --detalle: mensaje completo
    3. --todo: toda la memoria sin filtro
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from aura_mem import conectar, _icono

SEP = "-" * 65


# ---------------------------------------------------------------------------
# Busqueda principal
# ---------------------------------------------------------------------------

def buscar(query: str, tipo: str = None, desde: str = None, detalle: bool = False, limit: int = 15) -> None:
    """
    Busqueda FTS5 full-text sobre observaciones.
    Equivalente al 'search' MCP tool de claude-mem.
    Capa 1: resultado compacto (ID + snippet)
    Capa 2: --detalle activa mensaje completo
    """
    conn   = conectar()
    params = [query]
    filtro = ""

    if tipo:
        filtro += " AND o.tipo = ?"
        params.append(tipo)
    if desde:
        filtro += " AND o.fecha >= ?"
        params.append(desde)

    params.append(limit)

    sql = f"""
        SELECT o.id, o.tipo, o.mensaje, o.fecha, o.sesion_id, o.privado
        FROM obs_fts f
        JOIN observaciones o ON f.rowid = o.id
        WHERE obs_fts MATCH ?
        {filtro}
        ORDER BY o.fecha DESC
        LIMIT ?
    """

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        print(f"\n  Sin resultados para: '{query}'")
        print(f"  Prueba con: python memory/mem_search.py --recientes")
        return

    print(f"\n{SEP}")
    print(f"  BUSQUEDA: '{query}' — {len(rows)} resultado(s)")
    print(SEP)

    for r in rows:
        if r["privado"]:
            msg = "[CONTENIDO PRIVADO]"
        elif detalle:
            msg = r["mensaje"]
        else:
            # Capa 1: snippet de 80 chars
            msg = r["mensaje"][:80] + ("..." if len(r["mensaje"]) > 80 else "")

        fecha = r["fecha"][:19].replace("T", " ")
        print(f"  #{r['id']:<4} {_icono(r['tipo'])}[{r['tipo']:<12}] {fecha}")
        print(f"         {msg}")
        if detalle and not r["privado"]:
            print(f"         Sesion: {r['sesion_id']}")
        print()

    print(f"  Usa --detalle para ver mensajes completos.")
    print(SEP)


def mostrar_recientes(limit: int = 10) -> None:
    """Muestra las observaciones mas recientes sin filtro de busqueda."""
    conn = conectar()
    rows = conn.execute(
        "SELECT id, tipo, mensaje, fecha, privado FROM observaciones ORDER BY fecha DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()

    if not rows:
        print("\n  (sin observaciones en memoria)")
        return

    print(f"\n{SEP}")
    print(f"  OBSERVACIONES RECIENTES (ultimas {limit})")
    print(SEP)
    for r in rows:
        msg   = "[PRIVADO]" if r["privado"] else r["mensaje"][:75] + ("..." if len(r["mensaje"]) > 75 else "")
        fecha = r["fecha"][:19].replace("T", " ")
        print(f"  #{r['id']:<4} {_icono(r['tipo'])}[{r['tipo']:<12}] {fecha}")
        print(f"         {msg}")
        print()
    print(SEP)


def mostrar_todo() -> None:
    """
    Capa 3 de claude-mem: get_observations — detalle completo sin filtro.
    Util para revision completa antes de una sesion larga.
    """
    conn  = conectar()
    total = conn.execute("SELECT COUNT(*) FROM observaciones").fetchone()[0]
    rows  = conn.execute(
        "SELECT id, tipo, mensaje, fecha, sesion_id, privado FROM observaciones ORDER BY fecha"
    ).fetchall()
    conn.close()

    print(f"\n{SEP}")
    print(f"  MEMORIA COMPLETA — {total} observaciones")
    print(SEP)

    sesion_actual = None
    for r in rows:
        if r["sesion_id"] != sesion_actual:
            sesion_actual = r["sesion_id"]
            print(f"\n  >>> Sesion: {sesion_actual}")
            print(f"  {'~'*55}")

        if r["privado"]:
            msg = "[CONTENIDO PRIVADO]"
        else:
            msg = r["mensaje"]

        fecha = r["fecha"][:19].replace("T", " ")
        print(f"  #{r['id']:<4} {_icono(r['tipo'])}[{r['tipo']:<10}] {fecha}")
        print(f"         {msg}")

    print(f"\n{SEP}")


def buscar_por_id(obs_id: int) -> None:
    """Recupera una observacion especifica por ID — equivalente a get_observations de claude-mem."""
    conn = conectar()
    row  = conn.execute(
        "SELECT * FROM observaciones WHERE id=?", (obs_id,)
    ).fetchone()
    conn.close()

    if not row:
        print(f"\n  [ERROR] No existe observacion con id={obs_id}")
        return

    print(f"\n{SEP}")
    print(f"  OBSERVACION #{row['id']}")
    print(SEP)
    print(f"  Tipo    : {row['tipo']}")
    print(f"  Fecha   : {row['fecha'][:19].replace('T', ' ')}")
    print(f"  Sesion  : {row['sesion_id']}")
    print(f"  Privado : {'Si' if row['privado'] else 'No'}")
    print(f"\n  Mensaje:")
    print(f"  {row['mensaje']}")
    print(SEP)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="mem_search: busqueda en memoria persistente aura-mem",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("query", nargs="?", help="Texto a buscar")
    parser.add_argument("--tipo",     help="Filtrar por tipo de observacion")
    parser.add_argument("--desde",    help="Filtrar desde fecha (YYYY-MM-DD)")
    parser.add_argument("--detalle",  action="store_true", help="Mostrar mensaje completo")
    parser.add_argument("--limit",    type=int, default=15, help="Maximo de resultados")
    parser.add_argument("--recientes",action="store_true", help="Ver ultimas 10 observaciones")
    parser.add_argument("--todo",     action="store_true", help="Ver toda la memoria (capa 3)")
    parser.add_argument("--id",       type=int, help="Ver observacion especifica por ID")

    args = parser.parse_args()

    if args.id:
        buscar_por_id(args.id)
    elif args.recientes:
        mostrar_recientes()
    elif args.todo:
        mostrar_todo()
    elif args.query:
        buscar(args.query, tipo=args.tipo, desde=args.desde, detalle=args.detalle, limit=args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
