#!/usr/bin/env python3
"""
security.py — Adaptacion local de claude-security (anthropics/claude-plugins-official)
Scanner de vulnerabilidades para el proyecto MonitoreoBigData.
Aplica reglas OWASP + patrones de seguridad Python sin necesidad de Claude Code.

Modo hibrido:
    - Claude Code: usa .claude/skills/claude-security/ con agentes IA
    - Aura/VS Code: este script aplica reglas deterministicas localmente

Uso:
    python skills/security.py scan                    <- escanear todo el proyecto
    python skills/security.py scan <archivo.py>       <- escanear un archivo
    python skills/security.py scan-cambios            <- escanear solo archivos modificados
    python skills/security.py reporte                 <- ver ultimo reporte
    python skills/security.py threats                 <- modelo de amenazas del proyecto
"""

import os
import sys
import re
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import cmd_log

SEP          = "=" * 65
PROYECTO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTE_DIR  = os.path.join(PROYECTO_ROOT, "security-reports")

# ---------------------------------------------------------------------------
# Reglas de seguridad — adaptadas de claude-security + OWASP Python
# Severidades: CRITICAL, HIGH, MEDIUM, LOW
# ---------------------------------------------------------------------------

REGLAS = [
    # CRITICAS — explotacion directa
    {
        "id": "SEC-001", "severidad": "CRITICAL",
        "nombre": "Credencial hardcodeada",
        "patron": r'(password|passwd|secret|api_key|token|credential)\s*=\s*["\'][^"\']{4,}["\']',
        "descripcion": "Credencial o secreto hardcodeado en el codigo",
        "recomendacion": "Usar variables de entorno: os.environ.get('MI_SECRET')"
    },
    {
        "id": "SEC-002", "severidad": "CRITICAL",
        "nombre": "Inyeccion SQL directa",
        "patron": r'execute\s*\(\s*["\'].*%s.*["\']|execute\s*\(\s*f["\'].*{.*}',
        "descripcion": "Posible inyeccion SQL por concatenacion de strings",
        "recomendacion": "Usar parametros: conn.execute('SELECT * FROM t WHERE id=?', (id,))"
    },
    {
        "id": "SEC-003", "severidad": "CRITICAL",
        "nombre": "Eval con input externo",
        "patron": r'eval\s*\(|exec\s*\(',
        "descripcion": "eval()/exec() pueden ejecutar codigo arbitrario",
        "recomendacion": "Evitar eval/exec. Usar ast.literal_eval() para datos simples"
    },
    # ALTAS
    {
        "id": "SEC-004", "severidad": "HIGH",
        "nombre": "Deserializacion insegura",
        "patron": r'pickle\.loads?\s*\(|yaml\.load\s*\([^)]*(?!Loader)',
        "descripcion": "pickle.load y yaml.load sin Loader son vulnerables a RCE",
        "recomendacion": "Usar yaml.safe_load() o json.loads() en lugar de pickle/yaml.load"
    },
    {
        "id": "SEC-005", "severidad": "HIGH",
        "nombre": "Path traversal",
        "patron": r'open\s*\(\s*(?:request|input|args|params)',
        "descripcion": "Apertura de archivos con rutas controladas por el usuario",
        "recomendacion": "Validar y sanitizar rutas: os.path.abspath() + verificar que este dentro del directorio permitido"
    },
    {
        "id": "SEC-006", "severidad": "HIGH",
        "nombre": "Subprocess sin sanitizar",
        "patron": r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
        "descripcion": "subprocess con shell=True es vulnerable a inyeccion de comandos",
        "recomendacion": "Usar shell=False y pasar argumentos como lista: subprocess.run(['cmd', arg])"
    },
    {
        "id": "SEC-007", "severidad": "HIGH",
        "nombre": "Datos sensibles en logs",
        "patron": r'(print|log|logger)\s*\(.*?(password|token|secret|key|credential)',
        "descripcion": "Datos sensibles pueden aparecer en logs",
        "recomendacion": "Nunca loggear credenciales. Usar logging.debug('[REDACTED]')"
    },
    # MEDIAS
    {
        "id": "SEC-008", "severidad": "MEDIUM",
        "nombre": "Excepcion generica capturada",
        "patron": r'except\s*Exception\s*as|except\s*:\s*$|except\s*Exception\s*:',
        "descripcion": "Capturar Exception generica oculta errores de seguridad",
        "recomendacion": "Capturar excepciones especificas: except (ValueError, KeyError) as e"
    },
    {
        "id": "SEC-009", "severidad": "MEDIUM",
        "nombre": "Archivo temporal inseguro",
        "patron": r'tempfile\.mktemp\s*\(',
        "descripcion": "mktemp() tiene race condition — usar mkstemp()",
        "recomendacion": "Usar tempfile.mkstemp() o tempfile.NamedTemporaryFile()"
    },
    {
        "id": "SEC-010", "severidad": "MEDIUM",
        "nombre": "MD5 o SHA1 para seguridad",
        "patron": r'hashlib\.(md5|sha1)\s*\(',
        "descripcion": "MD5 y SHA1 estan rotos para propositos de seguridad",
        "recomendacion": "Usar hashlib.sha256() o hashlib.sha3_256()"
    },
    {
        "id": "SEC-011", "severidad": "MEDIUM",
        "nombre": "Debug mode en produccion",
        "patron": r'debug\s*=\s*True',
        "descripcion": "debug=True expone informacion sensible del stack",
        "recomendacion": "Usar variables de entorno para controlar debug mode"
    },
    # BAJAS
    {
        "id": "SEC-012", "severidad": "LOW",
        "nombre": "TODO de seguridad pendiente",
        "patron": r'#\s*TODO.*(?:security|auth|permission|validate|sanitize)',
        "descripcion": "Tarea de seguridad pendiente en el codigo",
        "recomendacion": "Resolver el TODO antes de ir a produccion"
    },
    {
        "id": "SEC-013", "severidad": "LOW",
        "nombre": "Uso de assert para validacion",
        "patron": r'^(?!\s*#)\s*assert\s+',
        "descripcion": "assert se desactiva con python -O, no usar para validacion de seguridad",
        "recomendacion": "Usar if/raise ValueError en lugar de assert para validaciones criticas"
    },
]

SEVERIDAD_ORDEN = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
SEVERIDAD_COLOR = {
    "CRITICAL": "[!!!]",
    "HIGH":     "[!! ]",
    "MEDIUM":   "[!  ]",
    "LOW":      "[.  ]",
}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _escanear_archivo(ruta: str) -> list[dict]:
    """Escanea un archivo Python contra todas las reglas."""
    hallazgos   = []
    ruta_norm   = ruta.replace("\\", "/").lower()
    es_test     = "test" in ruta_norm
    es_skill    = "skills/" in ruta_norm
    es_memoria  = "memory/" in ruta_norm

    # Reglas excluidas por contexto — evitar falsos positivos
    reglas_excluidas = set()
    if es_test:
        reglas_excluidas.add("SEC-013")   # assert es valido en pytest
    if es_skill or es_memoria:
        reglas_excluidas.add("SEC-003")   # el scanner describe eval, no lo llama
        reglas_excluidas.add("SEC-011")   # "debug=True" en strings/docs no es riesgo

    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
    except (OSError, PermissionError) as e:
        print(f"[security] No se pudo leer {ruta}: {e}")
        return hallazgos

    for num, linea in enumerate(lineas, 1):
        linea_stripped = linea.strip()
        # Ignorar comentarios y strings de documentacion
        if linea_stripped.startswith("#") or linea_stripped.startswith('"""') or linea_stripped.startswith("'"):
            continue

        for regla in REGLAS:
            if regla["id"] in reglas_excluidas:
                continue

            # SEC-007: solo alertar si el print/log contiene datos personales reales
            # No alertar por metricas tecnicas (tokens, ahorro, algoritmo)
            if regla["id"] == "SEC-007":
                falsos_positivos = [
                    "tokens_", "token_count", "num_tokens", "ahorro", "algoritmo",
                    "hojas_ods.keys()", ".keys()", "len(hojas"
                ]
                if any(kw in linea.lower() for kw in falsos_positivos):
                    continue

            # SEC-008: except Exception es aceptable en funciones de utilidad/watcher
            if regla["id"] == "SEC-008" and (es_skill or es_memoria):
                continue

            if re.search(regla["patron"], linea, re.IGNORECASE):
                hallazgos.append({
                    "regla_id":      regla["id"],
                    "severidad":     regla["severidad"],
                    "nombre":        regla["nombre"],
                    "archivo":       os.path.relpath(ruta, PROYECTO_ROOT),
                    "linea":         num,
                    "codigo":        linea.rstrip(),
                    "descripcion":   regla["descripcion"],
                    "recomendacion": regla["recomendacion"],
                })

    return hallazgos




def _recolectar_archivos_py(directorio: str) -> list[str]:
    """Lista todos los .py del proyecto excepto directorios ignorados."""
    ignorar = {".git", "__pycache__", ".pytest_cache", "node_modules",
               ".agents", ".claude", "graphify-out", ".vscode"}
    archivos = []
    for raiz, dirs, files in os.walk(directorio):
        dirs[:] = [d for d in dirs if d not in ignorar]
        for f in files:
            if f.endswith(".py"):
                archivos.append(os.path.join(raiz, f))
    return archivos


def _guardar_reporte(hallazgos: list[dict], scope: str) -> str:
    """Guarda el reporte en security-reports/ en formato JSON + MD."""
    os.makedirs(REPORTE_DIR, exist_ok=True)
    ts      = datetime.now().strftime("%Y%m%d-%H%M%S")
    base    = os.path.join(REPORTE_DIR, f"SECURITY-{ts}")

    # JSON
    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump({"scope": scope, "fecha": ts, "hallazgos": hallazgos}, f, indent=2)

    # Markdown (estilo claude-security)
    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write(f"# Security Report — {scope}\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        conteo = {s: sum(1 for h in hallazgos if h["severidad"] == s)
                  for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}
        f.write(f"## Resumen\n")
        f.write(f"| Severidad | Cantidad |\n|---|---|\n")
        for s, c in conteo.items():
            f.write(f"| {s} | {c} |\n")
        f.write(f"\n## Hallazgos\n\n")
        for h in sorted(hallazgos, key=lambda x: SEVERIDAD_ORDEN[x["severidad"]]):
            f.write(f"### [{h['severidad']}] {h['nombre']} — {h['regla_id']}\n")
            f.write(f"- **Archivo**: `{h['archivo']}` linea {h['linea']}\n")
            f.write(f"- **Descripcion**: {h['descripcion']}\n")
            f.write(f"- **Recomendacion**: {h['recomendacion']}\n")
            f.write(f"- **Codigo**: `{h['codigo'].strip()[:100]}`\n\n")

    return base


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_scan(objetivo: str = None) -> None:
    """Escanea el proyecto o un archivo especifico."""
    print(f"\n{SEP}")
    if objetivo:
        print(f"  CLAUDE-SECURITY — Scan: {objetivo}")
        archivos = [objetivo] if objetivo.endswith(".py") else _recolectar_archivos_py(objetivo)
    else:
        print(f"  CLAUDE-SECURITY — Scan completo del proyecto")
        archivos = _recolectar_archivos_py(PROYECTO_ROOT)
    print(SEP)

    print(f"\n  Escaneando {len(archivos)} archivo(s)...")
    todos_hallazgos = []
    for archivo in archivos:
        hallazgos = _escanear_archivo(archivo)
        todos_hallazgos.extend(hallazgos)

    # Mostrar resultados
    if not todos_hallazgos:
        print(f"\n  Sin vulnerabilidades detectadas.")
        cmd_log("[security] scan completo — 0 vulnerabilidades encontradas", "resultado")
    else:
        todos_hallazgos.sort(key=lambda x: SEVERIDAD_ORDEN[x["severidad"]])

        conteo = {s: sum(1 for h in todos_hallazgos if h["severidad"] == s)
                  for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}

        print(f"\n  RESUMEN:")
        for s, c in conteo.items():
            if c > 0:
                print(f"  {SEVERIDAD_COLOR[s]} {s:<10}: {c}")

        print(f"\n  HALLAZGOS DETALLADOS:")
        print(f"  {'-'*60}")
        for h in todos_hallazgos:
            print(f"\n  {SEVERIDAD_COLOR[h['severidad']]} [{h['severidad']}] {h['nombre']} ({h['regla_id']})")
            print(f"     Archivo : {h['archivo']}:{h['linea']}")
            print(f"     Codigo  : {h['codigo'].strip()[:80]}")
            print(f"     Fix     : {h['recomendacion'][:80]}")

        # Guardar reporte
        base = _guardar_reporte(todos_hallazgos, objetivo or "proyecto-completo")
        print(f"\n  Reporte guardado: {base}.md")
        print(f"                    {base}.json")

        criticos = conteo.get("CRITICAL", 0)
        altos    = conteo.get("HIGH", 0)
        cmd_log(
            f"[security] scan: {len(todos_hallazgos)} hallazgos — "
            f"{criticos} CRITICAL, {altos} HIGH",
            "error" if criticos > 0 else "resultado"
        )

    print(SEP)


def cmd_scan_cambios() -> None:
    """Escanea solo archivos modificados en git (equivalente a 'Scan changes' de claude-security)."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=PROYECTO_ROOT
        )
        archivos_py = [
            os.path.join(PROYECTO_ROOT, f.strip())
            for f in result.stdout.splitlines()
            if f.strip().endswith(".py")
        ]
        if not archivos_py:
            print("\n  Sin archivos Python modificados para escanear.")
            return
        print(f"\n  Escaneando {len(archivos_py)} archivo(s) modificados...")
        for archivo in archivos_py:
            cmd_scan(archivo)
    except Exception as e:
        print(f"[ERROR] {e}")


def cmd_reporte() -> None:
    """Muestra el ultimo reporte de seguridad generado."""
    if not os.path.exists(REPORTE_DIR):
        print("\n  Sin reportes generados. Ejecuta: python skills/security.py scan")
        return

    reportes = sorted([
        f for f in os.listdir(REPORTE_DIR) if f.endswith(".md")
    ], reverse=True)

    if not reportes:
        print("\n  Sin reportes. Ejecuta: python skills/security.py scan")
        return

    ultimo = os.path.join(REPORTE_DIR, reportes[0])
    with open(ultimo, encoding="utf-8") as f:
        print(f.read())


def cmd_threats() -> None:
    """Modelo de amenazas del proyecto — equivalente al threat model de claude-security."""
    print(f"\n{SEP}")
    print("  CLAUDE-SECURITY — Modelo de Amenazas")
    print("  Proyecto: MonitoreoBigData")
    print(SEP)

    amenazas = [
        {
            "categoria": "Datos de entrada",
            "amenaza":   "Archivos CSV/ODS con datos maliciosos",
            "impacto":   "Alto — el proyecto lee archivos externos sin validacion estricta",
            "mitigacion": "Validar encoding, tamano maximo y estructura antes de procesar",
        },
        {
            "categoria": "Privacidad",
            "amenaza":   "IDs de ciudadanos (CC, TI, PAS) expuestos en logs",
            "impacto":   "Alto — datos personales protegidos por ley",
            "mitigacion": "No loggear IDs. Usar <private> tag en aura-mem para datos sensibles",
        },
        {
            "categoria": "Integridad",
            "amenaza":   "Modificacion accidental de dataset_original.csv",
            "impacto":   "Medio — loss of source of truth",
            "mitigacion": "data/raw/ debe ser read-only. Solo data/processed/ se modifica",
        },
        {
            "categoria": "Dependencias",
            "amenaza":   "Librerias de terceros con vulnerabilidades",
            "impacto":   "Medio — sumy, nltk, watchdog pueden tener CVEs",
            "mitigacion": "Ejecutar 'pip audit' periodicamente. Mantener requirements.txt actualizado",
        },
        {
            "categoria": "Configuracion",
            "amenaza":   "Rutas absolutas en configuracion.yaml expuestas en git",
            "impacto":   "Bajo — revela estructura de directorios",
            "mitigacion": "Usar rutas relativas en config. Agregar config local a .gitignore",
        },
    ]

    for i, a in enumerate(amenazas, 1):
        print(f"\n  {i}. [{a['categoria'].upper()}]")
        print(f"     Amenaza   : {a['amenaza']}")
        print(f"     Impacto   : {a['impacto']}")
        print(f"     Mitigacion: {a['mitigacion']}")

    print(f"\n  RECOMENDACION INMEDIATA:")
    print(f"  Ejecutar: python skills/security.py scan")
    print(f"  para detectar vulnerabilidades en el codigo actual.")
    print(SEP)

    cmd_log("[security] modelo de amenazas revisado", "decision")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="security: scanner de vulnerabilidades para Aura")
    sub    = parser.add_subparsers(dest="cmd")

    p_s = sub.add_parser("scan",         help="Escanear proyecto o archivo")
    p_s.add_argument("objetivo", nargs="?", default=None)

    sub.add_parser("scan-cambios", help="Escanear solo archivos modificados en git")
    sub.add_parser("reporte",      help="Ver ultimo reporte de seguridad")
    sub.add_parser("threats",      help="Ver modelo de amenazas del proyecto")

    args = parser.parse_args()

    if args.cmd == "scan":          cmd_scan(args.objetivo)
    elif args.cmd == "scan-cambios": cmd_scan_cambios()
    elif args.cmd == "reporte":      cmd_reporte()
    elif args.cmd == "threats":      cmd_threats()
    else:                            parser.print_help()


if __name__ == "__main__":
    main()
