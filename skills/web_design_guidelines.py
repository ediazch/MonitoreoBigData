#!/usr/bin/env python3
"""
web_design_guidelines.py — Adaptacion local de web-design-guidelines (vercel-labs/agent-skills)
Audita archivos HTML/CSS contra las Web Interface Guidelines de Vercel.
100% local — las reglas estan embebidas, sin necesidad de internet.

Modo hibrido:
    - Claude Code / agentes: usa .agents/skills/web-design-guidelines/SKILL.md
    - Aura/VS Code: este script aplica las reglas localmente

Uso:
    python skills/web_design_guidelines.py audit <archivo.html>
    python skills/web_design_guidelines.py audit dashboard.html
    python skills/web_design_guidelines.py audit-dir .             <- todos los HTML del proyecto
    python skills/web_design_guidelines.py reglas                  <- ver todas las reglas
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
# Reglas — adaptadas de vercel-labs/web-interface-guidelines
# ---------------------------------------------------------------------------

REGLAS = [
    # ACCESIBILIDAD
    {
        "id": "WIG-A01", "categoria": "Accesibilidad", "severidad": "HIGH",
        "patron": r'<button(?![^>]*aria-label)[^>]*>\s*<(?:svg|i|img|span class=["\'][^"\']*icon)',
        "mensaje": "Boton con solo icono necesita aria-label",
        "fix":     'Agregar aria-label="Descripcion de la accion" al button'
    },
    {
        "id": "WIG-A02", "categoria": "Accesibilidad", "severidad": "HIGH",
        "patron": r'<input(?![^>]*(?:aria-label|<label))[^>]*>',
        "mensaje": "Input sin label o aria-label",
        "fix":     "Agregar <label for='id'> o aria-label al input"
    },
    {
        "id": "WIG-A03", "categoria": "Accesibilidad", "severidad": "MEDIUM",
        "patron": r'<img(?![^>]*alt=)[^>]*>',
        "mensaje": "Imagen sin atributo alt",
        "fix":     'Agregar alt="descripcion" (o alt="" si es decorativa)'
    },
    {
        "id": "WIG-A04", "categoria": "Accesibilidad", "severidad": "MEDIUM",
        "patron": r'<div\s+onclick|<span\s+onclick',
        "mensaje": "div/span con onclick — usar <button> para acciones",
        "fix":     "Reemplazar <div onclick> por <button>"
    },
    # FOCUS
    {
        "id": "WIG-F01", "categoria": "Focus", "severidad": "HIGH",
        "patron": r'outline:\s*none|outline:\s*0(?!\s*px)',
        "mensaje": "outline:none sin reemplazo de focus-visible",
        "fix":     "Agregar :focus-visible con ring alternativo"
    },
    {
        "id": "WIG-F02", "categoria": "Focus", "severidad": "MEDIUM",
        "patron": r'outline-none(?!.*focus-visible)',
        "mensaje": "outline-none sin focus-visible de reemplazo",
        "fix":     "Usar focus-visible:ring-2 como reemplazo"
    },
    # ANIMACION
    {
        "id": "WIG-AN01", "categoria": "Animacion", "severidad": "MEDIUM",
        "patron": r'transition:\s*all',
        "mensaje": "transition:all — listar propiedades explicitamente",
        "fix":     "transition: color 200ms, background-color 200ms"
    },
    {
        "id": "WIG-AN02", "categoria": "Animacion", "severidad": "LOW",
        "patron": r'@keyframes|animation:|transition:',
        "mensaje": "Animacion detectada — verificar prefers-reduced-motion",
        "fix":     "@media (prefers-reduced-motion: reduce) { animation: none }"
    },
    # TIPOGRAFIA
    {
        "id": "WIG-T01", "categoria": "Tipografia", "severidad": "LOW",
        "patron": r'\.\.\.',
        "mensaje": "Usar ellipsis unicode (…) no tres puntos (...)",
        "fix":     "Reemplazar ... por &hellip; o el caracter …"
    },
    {
        "id": "WIG-T02", "categoria": "Tipografia", "severidad": "LOW",
        "patron": r'font-size:\s*[1-9]px',
        "mensaje": "Fuente menor a 10px — ilegible",
        "fix":     "Minimo 12px para texto legible"
    },
    # IMAGENES
    {
        "id": "WIG-I01", "categoria": "Imagenes", "severidad": "MEDIUM",
        "patron": r'<img(?![^>]*(?:width|height))[^>]*>',
        "mensaje": "Imagen sin width/height — causa CLS (layout shift)",
        "fix":     "Agregar width y height explicitos al img"
    },
    {
        "id": "WIG-I02", "categoria": "Imagenes", "severidad": "LOW",
        "patron": r'\.gif(?:["\'\s])',
        "mensaje": "GIF animado — considerar video <video autoplay muted loop>",
        "fix":     "Usar <video autoplay muted loop playsinline> para mejor performance"
    },
    # FORMULARIOS
    {
        "id": "WIG-FM01", "categoria": "Formularios", "severidad": "MEDIUM",
        "patron": r'onpaste.*preventdefault|preventdefault.*onpaste',
        "mensaje": "Bloquear paste es un anti-patron de UX",
        "fix":     "Eliminar la restriccion de paste"
    },
    {
        "id": "WIG-FM02", "categoria": "Formularios", "severidad": "LOW",
        "patron": r'<input[^>]*type=["\']text["\'][^>]*(?:email|mail)',
        "mensaje": "Campo de email deberia usar type='email'",
        "fix":     "Cambiar type='text' a type='email' para teclado correcto en movil"
    },
    # ANTI-PATRONES
    {
        "id": "WIG-AP01", "categoria": "Anti-patrones", "severidad": "HIGH",
        "patron": r'user-scalable=no|maximum-scale=1',
        "mensaje": "Zoom deshabilitado — viola accesibilidad",
        "fix":     "Eliminar user-scalable=no del viewport meta"
    },
    {
        "id": "WIG-AP02", "categoria": "Anti-patrones", "severidad": "MEDIUM",
        "patron": r'<table(?![^>]*role)[^>]*>(?!.*<th)',
        "mensaje": "Tabla sin encabezados — usar <th> para datos tabulares",
        "fix":     "Agregar <th scope='col'> en la primera fila"
    },
    # CONTENIDO
    {
        "id": "WIG-C01", "categoria": "Contenido", "severidad": "LOW",
        "patron": r'\bContinue\b|\bClick here\b|\bLearn more\b',
        "mensaje": "Etiqueta de boton/link generica — ser especifico",
        "fix":     "Usar etiquetas descriptivas: 'Guardar configuracion', 'Ver reporte'"
    },
]

SEVERIDAD_ORDEN = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
SEVERIDAD_TAG   = {"HIGH": "[!!]", "MEDIUM": "[! ]", "LOW": "[. ]"}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _escanear_html(ruta: str) -> list[dict]:
    """Escanea un archivo HTML contra todas las reglas de Web Interface Guidelines."""
    hallazgos = []
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
    except (OSError, PermissionError) as e:
        print(f"[web-design] No se pudo leer {ruta}: {e}")
        return hallazgos

    for num, linea in enumerate(lineas, 1):
        if linea.strip().startswith("<!--"):
            continue
        for regla in REGLAS:
            if re.search(regla["patron"], linea, re.IGNORECASE):
                hallazgos.append({
                    "regla_id":  regla["id"],
                    "categoria": regla["categoria"],
                    "severidad": regla["severidad"],
                    "archivo":   os.path.relpath(ruta, PROYECTO_ROOT),
                    "linea":     num,
                    "codigo":    linea.rstrip()[:100],
                    "mensaje":   regla["mensaje"],
                    "fix":       regla["fix"],
                })
    return hallazgos


def _recolectar_html(directorio: str) -> list[str]:
    """Lista todos los HTML del proyecto."""
    ignorar = {".git", "__pycache__", "node_modules", ".agents", ".claude"}
    archivos = []
    for raiz, dirs, files in os.walk(directorio):
        dirs[:] = [d for d in dirs if d not in ignorar]
        for f in files:
            if f.endswith(".html"):
                archivos.append(os.path.join(raiz, f))
    return archivos


def _imprimir_hallazgos(hallazgos: list[dict], titulo: str) -> None:
    """Imprime hallazgos agrupados por archivo — formato VS Code clickable."""
    print(f"\n{SEP}")
    print(f"  WEB INTERFACE GUIDELINES — {titulo}")
    print(SEP)

    if not hallazgos:
        print("\n  Sin issues detectados.")
        return

    # Agrupar por archivo
    por_archivo: dict[str, list] = {}
    for h in sorted(hallazgos, key=lambda x: (x["archivo"], SEVERIDAD_ORDEN[x["severidad"]])):
        por_archivo.setdefault(h["archivo"], []).append(h)

    total = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for archivo, issues in por_archivo.items():
        print(f"\n  ## {archivo}")
        for h in issues:
            total[h["severidad"]] += 1
            tag = SEVERIDAD_TAG[h["severidad"]]
            # Formato file:line clickable en VS Code
            print(f"  {h['archivo']}:{h['linea']} {tag} {h['mensaje']}")
            print(f"    Fix: {h['fix']}")

    print(f"\n  RESUMEN: {total['HIGH']} HIGH | {total['MEDIUM']} MEDIUM | {total['LOW']} LOW")
    print(SEP)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_audit(archivo: str) -> None:
    """Audita un archivo HTML especifico."""
    if not os.path.exists(archivo):
        # Buscar en el proyecto
        ruta = os.path.join(PROYECTO_ROOT, archivo)
        if not os.path.exists(ruta):
            print(f"[ERROR] Archivo no encontrado: {archivo}")
            return
        archivo = ruta

    hallazgos = _escanear_html(archivo)
    nombre    = os.path.relpath(archivo, PROYECTO_ROOT)
    _imprimir_hallazgos(hallazgos, f"Audit: {nombre}")

    if hallazgos:
        cmd_log(
            f"[web-design] audit {nombre}: {len(hallazgos)} issues "
            f"({sum(1 for h in hallazgos if h['severidad']=='HIGH')} HIGH)",
            "resultado"
        )
    else:
        cmd_log(f"[web-design] audit {nombre}: 0 issues — OK", "resultado")


def cmd_audit_dir(directorio: str = ".") -> None:
    """Audita todos los HTML del proyecto."""
    ruta = os.path.join(PROYECTO_ROOT, directorio) if not os.path.isabs(directorio) else directorio
    archivos = _recolectar_html(ruta)

    if not archivos:
        print(f"\n  Sin archivos HTML encontrados en: {directorio}")
        return

    print(f"\n  Escaneando {len(archivos)} archivo(s) HTML...")
    todos = []
    for archivo in archivos:
        todos.extend(_escanear_html(archivo))

    _imprimir_hallazgos(todos, f"Audit directorio: {directorio}")
    cmd_log(f"[web-design] audit-dir: {len(archivos)} archivos, {len(todos)} issues", "resultado")


def cmd_reglas() -> None:
    """Muestra todas las reglas disponibles."""
    print(f"\n{SEP}")
    print("  WEB INTERFACE GUIDELINES — Reglas")
    print(SEP)

    categoria_actual = None
    for r in REGLAS:
        if r["categoria"] != categoria_actual:
            categoria_actual = r["categoria"]
            print(f"\n  [{categoria_actual.upper()}]")
        print(f"  {r['id']} {SEVERIDAD_TAG[r['severidad']]} {r['mensaje']}")

    print(f"\n  Total: {len(REGLAS)} reglas")
    print(f"  Fuente: vercel-labs/web-interface-guidelines")
    print(SEP)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="web-design-guidelines: audit HTML contra Web Interface Guidelines de Vercel"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_a = sub.add_parser("audit",     help="Auditar un archivo HTML")
    p_a.add_argument("archivo")

    p_d = sub.add_parser("audit-dir", help="Auditar todos los HTML del proyecto")
    p_d.add_argument("directorio", nargs="?", default=".")

    sub.add_parser("reglas", help="Ver todas las reglas")

    args = parser.parse_args()

    if args.cmd == "audit":          cmd_audit(args.archivo)
    elif args.cmd == "audit-dir":    cmd_audit_dir(args.directorio)
    elif args.cmd == "reglas":       cmd_reglas()
    else:                            parser.print_help()


if __name__ == "__main__":
    main()
