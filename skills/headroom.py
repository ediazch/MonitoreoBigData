#!/usr/bin/env python3
"""
headroom.py — Adaptacion local de headroom (headroomlabs-ai/headroom)
Comprime prompts, logs, JSON y outputs antes de procesarlos.
20-95% menos tokens. 100% local, sin enviar datos a ningun servidor.

Modo hibrido:
    - headroom-ai libreria: instalada via pip, funciona directo
    - Aura/VS Code: este wrapper integra headroom con aura-mem y el proyecto

Uso:
    python skills/headroom.py comprimir "<texto o ruta>"
    python skills/headroom.py comprimir-archivo <ruta>
    python skills/headroom.py comprimir-json <ruta.json>
    python skills/headroom.py comprimir-log <ruta.log>
    python skills/headroom.py stats
    python skills/headroom.py demo
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import cmd_log

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Motor de compresion — usa headroom-ai si esta disponible, fallback local
# ---------------------------------------------------------------------------

def _comprimir_con_headroom(texto: str) -> dict:
    """Intenta usar headroom-ai, fallback a compresor local."""
    try:
        from headroom import compress
        mensajes = [{"role": "user", "content": texto}]
        resultado = compress(mensajes)
        texto_comprimido = resultado.messages[0]["content"]
        tokens_antes  = len(texto.split())
        tokens_despues = len(texto_comprimido.split())
        return {
            "original":    texto,
            "comprimido":  texto_comprimido,
            "tokens_antes": tokens_antes,
            "tokens_despues": tokens_despues,
            "reduccion_pct": round((1 - tokens_despues / max(tokens_antes, 1)) * 100, 1),
            "motor": "headroom-ai"
        }
    except Exception:
        return _comprimir_local(texto)


def _comprimir_local(texto: str) -> dict:
    """Fallback: compresion local usando compresor.py de aura-mem."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
    from compresor import _comprimir_con_sumy, _comprimir_con_reglas

    tokens_antes = len(texto.split())
    num_frases   = max(2, int(tokens_antes * 0.3 / 10))

    if tokens_antes > 30:
        comprimido = _comprimir_con_sumy(texto, num_frases)
    else:
        comprimido = _comprimir_con_reglas(texto, num_frases)

    tokens_despues = len(comprimido.split())
    return {
        "original":      texto,
        "comprimido":    comprimido,
        "tokens_antes":  tokens_antes,
        "tokens_despues": tokens_despues,
        "reduccion_pct": round((1 - tokens_despues / max(tokens_antes, 1)) * 100, 1),
        "motor": "sumy-local"
    }


def _comprimir_json_local(datos: dict | list) -> dict:
    """Comprime JSON eliminando campos vacios, nulos y redundantes."""
    if isinstance(datos, list):
        return [_comprimir_json_local(item) for item in datos if item]
    if isinstance(datos, dict):
        return {
            k: _comprimir_json_local(v)
            for k, v in datos.items()
            if v is not None and v != "" and v != [] and v != {}
        }
    return datos


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_comprimir(texto: str) -> None:
    """Comprime un texto y muestra estadisticas."""
    print(f"\n{SEP}")
    print("  HEADROOM — Compresion de texto")
    print(SEP)

    resultado = _comprimir_con_headroom(texto)
    _imprimir_resultado(resultado)
    cmd_log(
        f"[headroom] texto comprimido: {resultado['reduccion_pct']}% reduccion ({resultado['motor']})",
        "resultado"
    )


def cmd_comprimir_archivo(ruta: str) -> None:
    """Comprime el contenido de un archivo."""
    if not os.path.exists(ruta):
        print(f"[ERROR] Archivo no encontrado: {ruta}")
        return

    with open(ruta, encoding="utf-8", errors="replace") as f:
        contenido = f.read()

    print(f"\n{SEP}")
    print(f"  HEADROOM — Compresion de archivo: {os.path.basename(ruta)}")
    print(SEP)

    resultado = _comprimir_con_headroom(contenido)
    _imprimir_resultado(resultado)

    # Guardar version comprimida
    base, ext = os.path.splitext(ruta)
    salida = f"{base}_comprimido{ext}"
    with open(salida, "w", encoding="utf-8") as f:
        f.write(resultado["comprimido"])

    print(f"\n  Guardado en: {salida}")
    cmd_log(f"[headroom] archivo comprimido: {ruta} -> {resultado['reduccion_pct']}% reduccion", "resultado")


def cmd_comprimir_json(ruta: str) -> None:
    """Comprime un archivo JSON eliminando campos vacios/nulos."""
    if not os.path.exists(ruta):
        print(f"[ERROR] Archivo no encontrado: {ruta}")
        return

    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    tam_antes = os.path.getsize(ruta)
    comprimido = _comprimir_json_local(datos)

    base, ext = os.path.splitext(ruta)
    salida = f"{base}_comprimido{ext}"
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(comprimido, f, ensure_ascii=False, separators=(",", ":"))

    tam_despues = os.path.getsize(salida)
    reduccion   = round((1 - tam_despues / max(tam_antes, 1)) * 100, 1)

    print(f"\n{SEP}")
    print(f"  HEADROOM — Compresion JSON: {os.path.basename(ruta)}")
    print(SEP)
    print(f"  Tamano antes  : {tam_antes:,} bytes")
    print(f"  Tamano despues: {tam_despues:,} bytes")
    print(f"  Reduccion     : {reduccion}%")
    print(f"  Guardado en   : {salida}")
    print(SEP)

    cmd_log(f"[headroom] JSON comprimido: {ruta} -> {reduccion}% reduccion", "resultado")


def cmd_comprimir_log(ruta: str) -> None:
    """Comprime un archivo de log extrayendo solo lineas de error/warning."""
    if not os.path.exists(ruta):
        print(f"[ERROR] Archivo no encontrado: {ruta}")
        return

    with open(ruta, encoding="utf-8", errors="replace") as f:
        lineas = f.readlines()

    # Filtrar solo lineas relevantes (como hace headroom SmartCrusher)
    palabras_clave = {"error", "warning", "critical", "fatal", "exception",
                      "traceback", "failed", "assert", "timeout"}
    relevantes = [
        l for l in lineas
        if any(kw in l.lower() for kw in palabras_clave)
    ]

    total_antes   = len(lineas)
    total_despues = len(relevantes)
    reduccion     = round((1 - total_despues / max(total_antes, 1)) * 100, 1)

    print(f"\n{SEP}")
    print(f"  HEADROOM — Compresion de log: {os.path.basename(ruta)}")
    print(SEP)
    print(f"  Lineas antes  : {total_antes:,}")
    print(f"  Lineas despues: {total_despues:,}")
    print(f"  Reduccion     : {reduccion}%")
    print(f"\n  LINEAS RELEVANTES:")
    for l in relevantes[:20]:
        print(f"  {l.rstrip()}")
    if len(relevantes) > 20:
        print(f"  ... y {len(relevantes) - 20} mas")
    print(SEP)

    cmd_log(f"[headroom] log comprimido: {ruta} -> {reduccion}% reduccion ({total_despues} lineas criticas)", "resultado")


def cmd_stats() -> None:
    """Muestra estadisticas de uso de headroom en el proyecto."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
    from aura_mem import conectar

    conn = conectar()
    obs  = conn.execute(
        "SELECT mensaje FROM observaciones WHERE mensaje LIKE '%headroom%' ORDER BY fecha DESC"
    ).fetchall()
    conn.close()

    print(f"\n{SEP}")
    print("  HEADROOM — Estadisticas de uso")
    print(SEP)

    try:
        from headroom import compress
        print("  Motor primario : headroom-ai (instalado)")
    except Exception:
        print("  Motor primario : sumy-local (fallback)")

    print(f"  Usos registrados en aura-mem: {len(obs)}")

    reducciones = []
    for o in obs:
        import re
        match = re.search(r'(\d+\.?\d*)%', o["mensaje"])
        if match:
            reducciones.append(float(match.group(1)))

    if reducciones:
        print(f"  Reduccion promedio: {round(sum(reducciones)/len(reducciones), 1)}%")
        print(f"  Mejor reduccion   : {max(reducciones)}%")

    print(f"\n  COMO USAR EN EL PROYECTO:")
    print(f"  python skills/headroom.py comprimir-archivo src/limpieza.py")
    print(f"  python skills/headroom.py comprimir-json graphify-out/graph.json")
    print(SEP)


def cmd_demo() -> None:
    """Demuestra la compresion con datos reales del proyecto."""
    texto_demo = """
    Analisis ODS vs CSV completado con 662 coincidencias de 666 registros totales.
    La cobertura del CSV sobre el ODS es del 99.4 por ciento.
    Se encontraron 4 registros solo en el CSV que no tienen referencia en el estimador.
    Se encontraron 35 registros solo en el ODS que no fueron cubiertos por los casos de prueba QA.
    El tipo de documento 13 PPT tiene una cobertura critica de solo el 50 por ciento.
    Los tipos 1 CC, 3 CE, 4 TI, 5 PAS, 9 RC y 12 PEP tienen cobertura del 100 por ciento.
    Se recomienda ampliar los casos de prueba para el tipo 13 PPT urgentemente.
    """

    print(f"\n{SEP}")
    print("  HEADROOM — Demo con datos reales del proyecto")
    print(SEP)
    resultado = _comprimir_con_headroom(texto_demo.strip())
    _imprimir_resultado(resultado)


def _imprimir_resultado(r: dict) -> None:
    print(f"\n  Motor         : {r['motor']}")
    print(f"  Tokens antes  : {r['tokens_antes']:,}")
    print(f"  Tokens despues: {r['tokens_despues']:,}")
    print(f"  Reduccion     : {r['reduccion_pct']}%")
    print(f"\n  ORIGINAL ({r['tokens_antes']} tokens):")
    print(f"  {r['original'][:200]}{'...' if len(r['original']) > 200 else ''}")
    print(f"\n  COMPRIMIDO ({r['tokens_despues']} tokens):")
    print(f"  {r['comprimido'][:200]}{'...' if len(r['comprimido']) > 200 else ''}")
    print(SEP)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="headroom: compresion de tokens para Aura")
    sub    = parser.add_subparsers(dest="cmd")

    p_c  = sub.add_parser("comprimir",         help="Comprimir texto")
    p_c.add_argument("texto")

    p_ca = sub.add_parser("comprimir-archivo",  help="Comprimir archivo de texto/codigo")
    p_ca.add_argument("ruta")

    p_cj = sub.add_parser("comprimir-json",     help="Comprimir archivo JSON")
    p_cj.add_argument("ruta")

    p_cl = sub.add_parser("comprimir-log",      help="Comprimir archivo de log")
    p_cl.add_argument("ruta")

    sub.add_parser("stats", help="Estadisticas de uso")
    sub.add_parser("demo",  help="Demo con datos del proyecto")

    args = parser.parse_args()

    if args.cmd == "comprimir":          cmd_comprimir(args.texto)
    elif args.cmd == "comprimir-archivo": cmd_comprimir_archivo(args.ruta)
    elif args.cmd == "comprimir-json":    cmd_comprimir_json(args.ruta)
    elif args.cmd == "comprimir-log":     cmd_comprimir_log(args.ruta)
    elif args.cmd == "stats":             cmd_stats()
    elif args.cmd == "demo":              cmd_demo()
    else:                                 parser.print_help()


if __name__ == "__main__":
    main()
