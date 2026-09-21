#!/usr/bin/env python3
"""
writing_guidelines.py — Adaptacion local de writing-guidelines (vercel-labs/agent-skills)
Revisa documentacion y prosa contra las Writing Guidelines de Vercel.
100% local — reglas embebidas, sin internet.

Modo hibrido:
    - Claude Code / agentes: usa .agents/skills/writing-guidelines/SKILL.md
    - Aura/VS Code: este script aplica las reglas localmente

Uso:
    python skills/writing_guidelines.py audit <archivo.md>
    python skills/writing_guidelines.py audit README.md
    python skills/writing_guidelines.py audit-dir docs/
    python skills/writing_guidelines.py reglas
"""

import os
import sys
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import cmd_log

SEP           = "=" * 65
PROYECTO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Reglas — adaptadas de vercel-labs/writing-guidelines
# ---------------------------------------------------------------------------

REGLAS = [
    # VOZ Y TONO
    {
        "id": "WG-V01", "categoria": "Voz", "severidad": "MEDIUM",
        "patron": r'\b(the user|the developer|one can|el usuario debe)\b',
        "mensaje": "Usar segunda persona — 'you/tu' en lugar de 'the user'",
        "fix":     "Reemplazar 'the user' por 'you' o forma directa"
    },
    {
        "id": "WG-V02", "categoria": "Voz", "severidad": "LOW",
        "patron": r'\b(will need to|you will need to|you should)\b',
        "mensaje": "Voz imperativa directa — no 'will need to'",
        "fix":     "Reemplazar 'You will need to click' por 'Click'"
    },
    {
        "id": "WG-V03", "categoria": "Voz", "severidad": "LOW",
        "patron": r'\?$',
        "mensaje": "Pregunta retorica detectada — suena a marketing",
        "fix":     "Convertir en afirmacion directa"
    },
    # PALABRAS PROHIBIDAS
    {
        "id": "WG-B01", "categoria": "Palabras prohibidas", "severidad": "HIGH",
        "patron": r'\b(easy|simple|quick|facil|sencillo|rapido)\b',
        "mensaje": "Palabra prohibida: easy/simple/quick — presiona al lector",
        "fix":     "Reemplazar con descripcion concreta: 'one command', 'default settings'"
    },
    {
        "id": "WG-B02", "categoria": "Palabras prohibidas", "severidad": "MEDIUM",
        "patron": r'\b(very|just|really|basically|actually|simplemente|solo)\b',
        "mensaje": "Relleno: very/just/really/basically — eliminar",
        "fix":     "Eliminar la palabra o reescribir la oracion"
    },
    {
        "id": "WG-B03", "categoria": "Palabras prohibidas", "severidad": "MEDIUM",
        "patron": r'\b(significantly|many|often|typically|generally|usually)\b',
        "mensaje": "Calificador vago — dar cifra concreta",
        "fix":     "Reemplazar por dato especifico: '99.4%' en lugar de 'most'"
    },
    # ESTRUCTURA
    {
        "id": "WG-S01", "categoria": "Estructura", "severidad": "MEDIUM",
        "patron": r'\.{3}$|\.\.\.$',
        "mensaje": "Usar ellipsis unicode (…) no tres puntos (...)",
        "fix":     "Reemplazar '...' por '…'"
    },
    {
        "id": "WG-S02", "categoria": "Estructura", "severidad": "LOW",
        "patron": r'^#{1,6}\s+.{60,}',
        "mensaje": "Heading muy largo — los headings deben ser concisos",
        "fix":     "Acortar el heading a menos de 60 caracteres"
    },
    {
        "id": "WG-S03", "categoria": "Estructura", "severidad": "LOW",
        "patron": r'^(?!#)(?![-*\d]).{200,}$',
        "mensaje": "Parrafo muy largo — dividir en 2-4 oraciones",
        "fix":     "Dividir en parrafos mas cortos"
    },
    # CODIGO
    {
        "id": "WG-C01", "categoria": "Codigo", "severidad": "MEDIUM",
        "patron": r'```(?!\w)',
        "mensaje": "Bloque de codigo sin language tag",
        "fix":     "Agregar lenguaje: ```python, ```bash, ```yaml"
    },
    {
        "id": "WG-C02", "categoria": "Codigo", "severidad": "LOW",
        "patron": r'`<TOKEN>`|`xxx`|`your-token`|`YOUR_TOKEN`',
        "mensaje": "Placeholder generico — usar snake_case descriptivo",
        "fix":     "Usar your_access_token_here en lugar de <TOKEN> o xxx"
    },
    # ENLACES
    {
        "id": "WG-L01", "categoria": "Enlaces", "severidad": "MEDIUM",
        "patron": r'\[(?:here|click here|link|ver aqui|haz clic)\]',
        "mensaje": "Texto de enlace generico — usar texto descriptivo",
        "fix":     "Usar texto que describa el destino: [Ver documentacion de limpieza]"
    },
    {
        "id": "WG-L02", "categoria": "Enlaces", "severidad": "LOW",
        "patron": r'https?://\S+(?<!\))',
        "mensaje": "URL expuesta — envolver en link con texto descriptivo",
        "fix":     "Usar [texto descriptivo](url) en lugar de URL desnuda"
    },
    # TELLTALES DE IA
    {
        "id": "WG-AI01", "categoria": "Telltales IA", "severidad": "MEDIUM",
        "patron": r'^(With this|Now that we|In this section|In conclusion|To summarize)',
        "mensaje": "Transicion de resumen — tipico de IA generada",
        "fix":     "Eliminar y pasar directamente al siguiente punto"
    },
    {
        "id": "WG-AI02", "categoria": "Telltales IA", "severidad": "LOW",
        "patron": r'\b(provides|is configurable|is explicitly|is designed to)\b',
        "mensaje": "Voz de ficha tecnica — tipico de IA generada",
        "fix":     "Reescribir en voz activa y directa"
    },
    {
        "id": "WG-AI03", "categoria": "Telltales IA", "severidad": "LOW",
        "patron": r'\b(leverage|utilize|facilitate|enable|empower)\b',
        "mensaje": "Verbo de marketing/IA — usar verbo simple",
        "fix":     "use en lugar de utilize, help en lugar de facilitate"
    },
    # ENFASIS
    {
        "id": "WG-E01", "categoria": "Enfasis", "severidad": "LOW",
        "patron": r'\*\*[^*]{1,3}\*\*',
        "mensaje": "Bold en texto muy corto — verificar si es necesario",
        "fix":     "Bold solo para elementos UI o hechos criticos"
    },
]

SEVERIDAD_ORDEN = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
SEVERIDAD_TAG   = {"HIGH": "[!!]", "MEDIUM": "[! ]", "LOW": "[. ]"}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _escanear_md(ruta: str) -> list[dict]:
    """Escanea un archivo Markdown contra las Writing Guidelines."""
    hallazgos = []
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
    except (OSError, PermissionError) as e:
        print(f"[writing] No se pudo leer {ruta}: {e}")
        return hallazgos

    en_bloque_codigo = False
    for num, linea in enumerate(lineas, 1):
        # No escanear dentro de bloques de codigo
        if linea.strip().startswith("```"):
            en_bloque_codigo = not en_bloque_codigo
            # WG-C01: verificar language tag
            if en_bloque_codigo:
                for regla in REGLAS:
                    if regla["id"] == "WG-C01":
                        if re.search(regla["patron"], linea, re.IGNORECASE):
                            hallazgos.append(_hacer_hallazgo(regla, ruta, num, linea))
            continue

        if en_bloque_codigo:
            continue

        for regla in REGLAS:
            if regla["id"] == "WG-C01":
                continue  # ya manejado arriba
            if re.search(regla["patron"], linea, re.IGNORECASE | re.MULTILINE):
                hallazgos.append(_hacer_hallazgo(regla, ruta, num, linea))

    return hallazgos


def _hacer_hallazgo(regla: dict, ruta: str, num: int, linea: str) -> dict:
    return {
        "regla_id":  regla["id"],
        "categoria": regla["categoria"],
        "severidad": regla["severidad"],
        "archivo":   os.path.relpath(ruta, PROYECTO_ROOT),
        "linea":     num,
        "codigo":    linea.rstrip()[:100],
        "mensaje":   regla["mensaje"],
        "fix":       regla["fix"],
    }


def _recolectar_md(directorio: str) -> list[str]:
    ignorar = {".git", "__pycache__", "node_modules", ".agents", ".claude"}
    archivos = []
    for raiz, dirs, files in os.walk(directorio):
        dirs[:] = [d for d in dirs if d not in ignorar]
        for f in files:
            if f.endswith(".md"):
                archivos.append(os.path.join(raiz, f))
    return archivos


def _imprimir_hallazgos(hallazgos: list[dict], titulo: str) -> None:
    print(f"\n{SEP}")
    print(f"  WRITING GUIDELINES — {titulo}")
    print(SEP)

    if not hallazgos:
        print("\n  Sin issues detectados.")
        return

    por_archivo: dict[str, list] = {}
    for h in sorted(hallazgos, key=lambda x: (x["archivo"], SEVERIDAD_ORDEN[x["severidad"]])):
        por_archivo.setdefault(h["archivo"], []).append(h)

    total = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for archivo, issues in por_archivo.items():
        print(f"\n  ## {archivo}")
        for h in issues:
            total[h["severidad"]] += 1
            tag = SEVERIDAD_TAG[h["severidad"]]
            print(f"  {h['archivo']}:{h['linea']} {tag} {h['mensaje']}")
            print(f"    Fix: {h['fix']}")
            print(f"    Linea: {h['codigo'][:70]}")

    print(f"\n  RESUMEN: {total['HIGH']} HIGH | {total['MEDIUM']} MEDIUM | {total['LOW']} LOW")
    print(SEP)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_audit(archivo: str) -> None:
    """Audita un archivo Markdown especifico."""
    ruta = archivo if os.path.isabs(archivo) else os.path.join(PROYECTO_ROOT, archivo)
    if not os.path.exists(ruta):
        print(f"[ERROR] Archivo no encontrado: {archivo}")
        return

    hallazgos = _escanear_md(ruta)
    nombre    = os.path.relpath(ruta, PROYECTO_ROOT)
    _imprimir_hallazgos(hallazgos, f"Audit: {nombre}")

    nivel = "resultado" if not any(h["severidad"] == "HIGH" for h in hallazgos) else "nota"
    cmd_log(f"[writing] audit {nombre}: {len(hallazgos)} issues", nivel)


def cmd_audit_dir(directorio: str = ".") -> None:
    """Audita todos los Markdown del proyecto."""
    ruta      = os.path.join(PROYECTO_ROOT, directorio) if not os.path.isabs(directorio) else directorio
    archivos  = _recolectar_md(ruta)

    if not archivos:
        print(f"\n  Sin archivos .md encontrados en: {directorio}")
        return

    print(f"\n  Escaneando {len(archivos)} archivo(s) Markdown...")
    todos = []
    for archivo in archivos:
        todos.extend(_escanear_md(archivo))

    _imprimir_hallazgos(todos, f"Audit directorio: {directorio}")
    cmd_log(f"[writing] audit-dir: {len(archivos)} archivos, {len(todos)} issues", "resultado")


def cmd_reglas() -> None:
    """Muestra todas las reglas disponibles."""
    print(f"\n{SEP}")
    print("  WRITING GUIDELINES — Reglas")
    print(SEP)

    cat_actual = None
    for r in REGLAS:
        if r["categoria"] != cat_actual:
            cat_actual = r["categoria"]
            print(f"\n  [{cat_actual.upper()}]")
        print(f"  {r['id']} {SEVERIDAD_TAG[r['severidad']]} {r['mensaje']}")

    print(f"\n  Total: {len(REGLAS)} reglas")
    print(f"  Fuente: vercel-labs/writing-guidelines")
    print(SEP)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="writing-guidelines: audit Markdown contra Writing Guidelines de Vercel"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_a = sub.add_parser("audit",     help="Auditar un archivo Markdown")
    p_a.add_argument("archivo")

    p_d = sub.add_parser("audit-dir", help="Auditar todos los .md del proyecto")
    p_d.add_argument("directorio", nargs="?", default=".")

    sub.add_parser("reglas", help="Ver todas las reglas")

    args = parser.parse_args()

    if args.cmd == "audit":        cmd_audit(args.archivo)
    elif args.cmd == "audit-dir":  cmd_audit_dir(args.directorio)
    elif args.cmd == "reglas":     cmd_reglas()
    else:                          parser.print_help()


if __name__ == "__main__":
    main()
