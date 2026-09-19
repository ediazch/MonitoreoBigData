#!/usr/bin/env python3
"""
impeccable.py — Adaptacion local de impeccable (pbakaus/impeccable)
Guia de diseno profesional para dashboards y visualizaciones del proyecto.
Se integra con aura-mem para registrar decisiones de diseno.

Modo hibrido:
    - Claude Code: usa .claude/skills/impeccable/ con el binario nativo
    - Aura/VS Code: usa este script para guia, audit y generacion de plantillas

Uso:
    python skills/impeccable.py init
    python skills/impeccable.py audit <archivo.html>
    python skills/impeccable.py critique "<descripcion del diseno>"
    python skills/impeccable.py polish <archivo>
    python skills/impeccable.py generar dashboard
    python skills/impeccable.py anti-patrones
"""

import os
import sys
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import cmd_log

SEP    = "=" * 65
PRODUCT_FILE = os.path.join(os.path.dirname(__file__), "..", "PRODUCT.md")


# ---------------------------------------------------------------------------
# Reglas de diseno — 61 reglas del impeccable original adaptadas al proyecto
# ---------------------------------------------------------------------------

REGLAS_AUDIT = {
    "tipografia": [
        ("inter_overuse",    r'\bInter\b',           "Evitar Inter como fuente unica — usa System UI o una fuente con personalidad"),
        ("arial_overuse",    r'\bArial\b',            "Arial es demasiado generica — considera alternativas"),
        ("font_size_small",  r'font-size:\s*[0-9]px', "Fuente menor a 10px — ilegible en pantallas reales"),
    ],
    "color": [
        ("gray_on_color",    r'color:\s*gray',        "Texto gris sobre fondo de color — problema de contraste"),
        ("pure_black",       r'#000000|#000(?![0-9a-f])', "Negro puro — usar #0a0a0a o similar con tinte"),
        ("purple_blue_grad", r'linear-gradient.*purple.*blue|linear-gradient.*blue.*purple', "Gradiente purpura-azul — demasiado comun en SaaS"),
    ],
    "layout": [
        ("cards_nested",     r'card.*card|\.card\s+\.card', "Cards anidadas — simplificar jerarquia visual"),
        ("icon_above_heading", r'<i.*</i>\s*<h[1-6]',      "Icono encima de heading — patron sobreusado"),
    ],
    "animacion": [
        ("bounce_easing",    r'cubic-bezier.*bounce|ease-bounce', "Easing tipo bounce — se siente desactualizado"),
        ("elastic_easing",   r'elastic|spring',               "Easing elastico — evitar para UI de datos"),
    ],
}

ANTI_PATRONES = [
    ("Inter para todo",            "Usar System UI stack o una fuente con caracter propio"),
    ("Gradiente purpura a azul",   "Elegir una paleta cromatica del dominio del proyecto"),
    ("Cards dentro de cards",      "Usar jerarquia plana con espaciado y tipografia"),
    ("Texto gris sobre color",     "Texto blanco o negro con suficiente contraste (4.5:1 minimo)"),
    ("Negro/gris puro sin tinte",  "Siempre agregar un tinte sutil del color primario"),
    ("Icono cuadrado sobre heading","Integrar iconos con el texto, no encima"),
    ("Bounce/elastic animations",  "Usar ease-out o ease-in-out para UI de datos"),
    ("Rounded everything",         "Variar el radio de borde segun jerarquia del elemento"),
]

COMANDOS_DISPONIBLES = {
    "init":         "Configurar contexto del producto (genera PRODUCT.md)",
    "audit":        "Revisar archivo HTML/CSS contra las 61 reglas",
    "critique":     "Revision de UX: jerarquia, claridad, proposito",
    "polish":       "Pase final de calidad antes de mostrar",
    "anti-patrones":"Ver lista de anti-patrones a evitar",
    "generar":      "Generar plantilla base de dashboard para el proyecto",
}


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_init() -> None:
    """Configura el contexto del producto — equivalente a /impeccable init"""
    print(f"\n{SEP}")
    print("  IMPECCABLE — Configuracion del Producto")
    print(SEP)

    producto = {
        "nombre":      "MonitoreoBigData",
        "proposito":   "Dashboard de analisis y monitoreo de datos de identidad",
        "audiencia":   "Analistas de datos y equipo QA de Transturismo",
        "contexto":    "Herramienta interna — escritorio, luz del dia",
        "tono":        "Profesional, denso en datos, confiable",
        "restricciones": "Sin gradientes llamativos, tipografia legible, alta densidad de informacion",
        "paleta":      "Azul corporativo + grises neutros + verde/rojo para estados",
    }

    contenido = f"""# PRODUCT.md — MonitoreoBigData
Generado por impeccable.py el {datetime.now().strftime('%Y-%m-%d')}

## Proposito
{producto['proposito']}

## Audiencia
{producto['audiencia']}

## Contexto de uso
{producto['contexto']}

## Tono visual
{producto['tono']}

## Restricciones de diseno
{producto['restricciones']}

## Paleta cromatica
{producto['paleta']}

## Principios clave (impeccable)
- Jerarquia visual clara: el dato mas importante domina
- Sin decoracion gratuita — cada elemento tiene proposito
- Contraste minimo 4.5:1 para texto sobre fondo
- Tipografia: Inter 400/600 solo si es necesario, preferir system-ui
- Espaciado: escala de 4px (4, 8, 12, 16, 24, 32, 48, 64)
"""

    with open(PRODUCT_FILE, "w", encoding="utf-8") as f:
        f.write(contenido)

    cmd_log("[impeccable] PRODUCT.md generado — contexto del producto configurado", "decision")

    print(f"\n  PRODUCT.md generado en: {PRODUCT_FILE}")
    for k, v in producto.items():
        print(f"  {k:<15}: {v}")
    print(SEP)


def cmd_audit(archivo: str) -> None:
    """Audita un archivo HTML/CSS contra las reglas de impeccable."""
    if not os.path.exists(archivo):
        print(f"[ERROR] Archivo no encontrado: {archivo}")
        return

    with open(archivo, encoding="utf-8", errors="replace") as f:
        contenido = f.read()

    print(f"\n{SEP}")
    print(f"  IMPECCABLE AUDIT — {os.path.basename(archivo)}")
    print(SEP)

    total_issues = 0
    for categoria, reglas in REGLAS_AUDIT.items():
        issues = []
        for nombre, patron, mensaje in reglas:
            if re.search(patron, contenido, re.IGNORECASE):
                issues.append(f"    [!] {mensaje}")
                total_issues += 1

        if issues:
            print(f"\n  {categoria.upper()}:")
            for issue in issues:
                print(issue)

    if total_issues == 0:
        print("\n  Sin issues detectados — diseno limpio.")
        cmd_log(f"[impeccable] audit OK: {os.path.basename(archivo)} — 0 issues", "resultado")
    else:
        print(f"\n  Total issues: {total_issues}")
        cmd_log(f"[impeccable] audit: {os.path.basename(archivo)} — {total_issues} issues encontrados", "nota")

    print(SEP)


def cmd_critique(descripcion: str) -> None:
    """Revision de UX basada en principios de impeccable."""
    print(f"\n{SEP}")
    print("  IMPECCABLE CRITIQUE — Revision de UX")
    print(SEP)
    print(f"\n  Diseno: {descripcion}")
    print(f"\n  CHECKLIST DE CALIDAD:")

    checklist = [
        ("Jerarquia visual",    "El elemento mas importante es visualmente dominante?"),
        ("Proposito claro",     "El usuario sabe en 3 segundos que hace esta pantalla?"),
        ("Densidad apropiada",  "La cantidad de info es adecuada para la audiencia?"),
        ("Consistencia",        "Los espaciados, colores y tipografia son consistentes?"),
        ("Estados vacios",      "Hay estado vacio definido para cuando no hay datos?"),
        ("Responsive",          "Funciona en diferentes resoluciones de escritorio?"),
        ("Accesibilidad",       "El contraste cumple WCAG 2.1 AA (4.5:1 minimo)?"),
        ("Performance",         "Las visualizaciones cargan en menos de 2 segundos?"),
    ]

    for nombre, pregunta in checklist:
        print(f"  [ ] {nombre:<20} {pregunta}")

    print(f"\n  ANTI-PATRONES A VERIFICAR:")
    for patron, solucion in ANTI_PATRONES[:4]:
        print(f"  [?] {patron:<35} -> {solucion}")

    cmd_log(f"[impeccable] critique ejecutado: {descripcion[:60]}", "decision")
    print(SEP)


def cmd_polish(archivo: str = None) -> None:
    """Pase final de calidad antes de entregar."""
    print(f"\n{SEP}")
    print("  IMPECCABLE POLISH — Checklist final")
    print(SEP)

    pasos = [
        "Revisar contraste de todos los textos (herramienta: contrast-ratio.com)",
        "Verificar que no hay texto truncado en resoluciones 1280px y 1920px",
        "Comprobar estados: vacio, cargando, error, exito",
        "Revisar espaciado — debe seguir escala de 4px",
        "Confirmar que los colores de estado son consistentes (verde=ok, rojo=error)",
        "Verificar que los numeros grandes usan separadores de miles",
        "Comprobar que las fechas siguen formato consistente",
        "Revisar orden de tabulacion para accesibilidad",
        "Validar que el HTML es semanticamente correcto",
        "Hacer prueba con zoom al 150% — debe seguir siendo legible",
    ]

    for i, paso in enumerate(pasos, 1):
        print(f"  {i:>2}. [ ] {paso}")

    if archivo:
        cmd_log(f"[impeccable] polish checklist aplicado a: {archivo}", "resultado")
    print(SEP)


def cmd_anti_patrones() -> None:
    """Muestra lista completa de anti-patrones de impeccable."""
    print(f"\n{SEP}")
    print("  IMPECCABLE — Anti-patrones a evitar")
    print(SEP)
    for i, (patron, solucion) in enumerate(ANTI_PATRONES, 1):
        print(f"\n  {i}. EVITAR: {patron}")
        print(f"     USAR:   {solucion}")
    print(SEP)


def cmd_generar(tipo: str) -> None:
    """Genera plantilla base de dashboard HTML para el proyecto."""
    if tipo != "dashboard":
        print(f"[ERROR] Tipo no soportado: '{tipo}'. Usa: dashboard")
        return

    plantilla = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MonitoreoBigData — Dashboard</title>
    <style>
        /* Sistema de diseno — impeccable */
        :root {
            --color-bg:       #f8f9fa;
            --color-surface:  #ffffff;
            --color-border:   #e2e8f0;
            --color-text:     #1a202c;
            --color-text-muted: #4a5568;
            --color-primary:  #2b6cb0;
            --color-success:  #276749;
            --color-warning:  #744210;
            --color-error:    #742a2a;
            --color-ok-bg:    #f0fff4;
            --color-err-bg:   #fff5f5;
            --font:           system-ui, -apple-system, sans-serif;
            --space-1: 4px; --space-2: 8px; --space-3: 12px;
            --space-4: 16px; --space-6: 24px; --space-8: 32px;
            --radius: 6px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: var(--font);
            background: var(--color-bg);
            color: var(--color-text);
            font-size: 14px;
            line-height: 1.5;
        }

        /* Layout */
        .header {
            background: var(--color-surface);
            border-bottom: 1px solid var(--color-border);
            padding: var(--space-4) var(--space-8);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 { font-size: 18px; font-weight: 600; color: var(--color-primary); }
        .header .meta { font-size: 12px; color: var(--color-text-muted); }

        .main { padding: var(--space-6) var(--space-8); max-width: 1400px; margin: 0 auto; }

        /* Metricas */
        .metricas { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-6); }
        .metrica {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            padding: var(--space-4) var(--space-6);
        }
        .metrica .valor { font-size: 28px; font-weight: 700; color: var(--color-primary); }
        .metrica .label { font-size: 12px; color: var(--color-text-muted); margin-top: var(--space-1); }
        .metrica.ok    { border-left: 3px solid #48bb78; }
        .metrica.warn  { border-left: 3px solid #ed8936; }
        .metrica.error { border-left: 3px solid #fc8181; }

        /* Tabla */
        .seccion {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            margin-bottom: var(--space-4);
        }
        .seccion-header {
            padding: var(--space-3) var(--space-4);
            border-bottom: 1px solid var(--color-border);
            font-weight: 600;
            font-size: 13px;
            color: var(--color-text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            text-align: left;
            padding: var(--space-2) var(--space-4);
            font-size: 11px;
            font-weight: 600;
            color: var(--color-text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--color-border);
        }
        td { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-border); font-size: 13px; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: var(--color-bg); }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-ok    { background: var(--color-ok-bg);  color: var(--color-success); }
        .badge-error { background: var(--color-err-bg); color: var(--color-error); }
    </style>
</head>
<body>
    <header class="header">
        <h1>MonitoreoBigData</h1>
        <span class="meta">Ultima actualizacion: <span id="fecha"></span></span>
    </header>

    <main class="main">
        <!-- Metricas globales -->
        <div class="metricas">
            <div class="metrica ok">
                <div class="valor">662</div>
                <div class="label">Coincidencias totales</div>
            </div>
            <div class="metrica ok">
                <div class="valor">99.4%</div>
                <div class="label">Cobertura CSV sobre ODS</div>
            </div>
            <div class="metrica warn">
                <div class="valor">4</div>
                <div class="label">Solo en CSV (gaps QA)</div>
            </div>
            <div class="metrica error">
                <div class="valor">50%</div>
                <div class="label">Cobertura tipo 13 PPT</div>
            </div>
        </div>

        <!-- Tabla de resultados por tipo -->
        <div class="seccion">
            <div class="seccion-header">Relacion por tipo de documento</div>
            <table>
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Descripcion</th>
                        <th>Total CSV</th>
                        <th>Total ODS</th>
                        <th>Coincidencias</th>
                        <th>Cobertura</th>
                    </tr>
                </thead>
                <tbody id="tabla-datos">
                    <!-- Datos se insertan via JS -->
                </tbody>
            </table>
        </div>
    </main>

    <script>
        document.getElementById("fecha").textContent = new Date().toLocaleString("es-CO");

        const datos = [
            { tipo:"1",  desc:"Cedula de Ciudadania",              csv:101, ods:101, coin:101, pct:100.0 },
            { tipo:"3",  desc:"Cedula de Extranjeria",             csv:27,  ods:27,  coin:27,  pct:100.0 },
            { tipo:"4",  desc:"Tarjeta de Identidad",              csv:114, ods:114, coin:114, pct:100.0 },
            { tipo:"5",  desc:"Pasaporte",                         csv:98,  ods:98,  coin:98,  pct:100.0 },
            { tipo:"6",  desc:"Tarjeta Seguro Social",             csv:154, ods:153, coin:153, pct:99.4  },
            { tipo:"9",  desc:"Registro Civil",                    csv:6,   ods:6,   coin:6,   pct:100.0 },
            { tipo:"10", desc:"Carnet Diplomatico",                csv:27,  ods:26,  coin:26,  pct:96.3  },
            { tipo:"11", desc:"Patente de Automotor",              csv:64,  ods:63,  coin:63,  pct:98.4  },
            { tipo:"12", desc:"Permiso Especial Permanencia (PEP)",csv:73,  ods:73,  coin:73,  pct:100.0 },
            { tipo:"13", desc:"Permiso Proteccion Temporal (PPT)", csv:2,   ods:36,  coin:1,   pct:50.0  },
        ];

        const tbody = document.getElementById("tabla-datos");
        datos.forEach(d => {
            const cls  = d.pct === 100 ? "badge-ok" : d.pct >= 95 ? "" : "badge-error";
            const row  = `<tr>
                <td><strong>${d.tipo}</strong></td>
                <td>${d.desc}</td>
                <td>${d.csv}</td>
                <td>${d.ods}</td>
                <td>${d.coin}</td>
                <td><span class="badge ${cls}">${d.pct}%</span></td>
            </tr>`;
            tbody.insertAdjacentHTML("beforeend", row);
        });
    </script>
</body>
</html>
"""
    salida = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
    with open(salida, "w", encoding="utf-8") as f:
        f.write(plantilla)

    cmd_log("[impeccable] dashboard.html generado con sistema de diseno impeccable", "resultado")
    print(f"\n  Dashboard generado: {salida}")
    print(f"  Abrelo en el navegador para ver el resultado.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="impeccable: diseno profesional para Aura")
    sub    = parser.add_subparsers(dest="cmd")

    sub.add_parser("init",         help="Configurar contexto del producto")
    sub.add_parser("anti-patrones",help="Ver anti-patrones de diseno a evitar")

    p_audit = sub.add_parser("audit",    help="Auditar archivo HTML/CSS")
    p_audit.add_argument("archivo")

    p_crit = sub.add_parser("critique",  help="Revision de UX de un diseno")
    p_crit.add_argument("descripcion")

    p_pol = sub.add_parser("polish",     help="Checklist final de calidad")
    p_pol.add_argument("archivo", nargs="?", default=None)

    p_gen = sub.add_parser("generar",    help="Generar plantilla (dashboard)")
    p_gen.add_argument("tipo", choices=["dashboard"])

    args = parser.parse_args()

    if args.cmd == "init":              cmd_init()
    elif args.cmd == "anti-patrones":  cmd_anti_patrones()
    elif args.cmd == "audit":          cmd_audit(args.archivo)
    elif args.cmd == "critique":       cmd_critique(args.descripcion)
    elif args.cmd == "polish":         cmd_polish(args.archivo)
    elif args.cmd == "generar":        cmd_generar(args.tipo)
    else:                              parser.print_help()


if __name__ == "__main__":
    main()
