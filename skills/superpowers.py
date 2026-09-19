#!/usr/bin/env python3
"""
superpowers.py — Adaptacion local de superpowers (obra/superpowers)
Workflow de planificacion, TDD y revision de codigo integrado al proyecto.
Se integra con aura-mem para persistir planes y decisiones.

Modo hibrido:
    - Claude Code: usa .claude/skills/ con los 14 skills originales
    - Aura/VS Code: usa este script para el workflow completo

Uso:
    python skills/superpowers.py brainstorm "<idea>"
    python skills/superpowers.py plan "<feature>"
    python skills/superpowers.py tdd "<modulo>"
    python skills/superpowers.py review "<archivo>"
    python skills/superpowers.py status
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "memory"))
from aura_mem import cmd_log

SEP      = "=" * 65
PLANS_DIR = os.path.join(os.path.dirname(__file__), "..", ".plan")


# ---------------------------------------------------------------------------
# Comandos — workflow de superpowers adaptado
# ---------------------------------------------------------------------------

def cmd_brainstorm(idea: str) -> None:
    """
    Fase 1 de superpowers: brainstorming.
    Guia al usuario a refinar la idea antes de codear.
    """
    print(f"\n{SEP}")
    print("  SUPERPOWERS — Brainstorming")
    print(SEP)
    print(f"\n  Idea: {idea}")
    print(f"\n  Preguntas de refinamiento (responde antes de implementar):")

    preguntas = [
        "Cual es el problema real que esto resuelve?",
        "Quien lo va a usar y con que frecuencia?",
        "Cual es el criterio de exito — como sabes que funciono?",
        "Existen datos o dependencias que necesites primero?",
        "Cuanto tiempo estimado toma implementarlo?",
        "Hay alternativas mas simples que logren lo mismo?",
        "Como se va a testear?",
        "Que puede salir mal?",
    ]

    for i, p in enumerate(preguntas, 1):
        print(f"  {i}. {p}")

    print(f"\n  Cuando tengas las respuestas, ejecuta:")
    print(f"  python skills/superpowers.py plan \"{idea}\"")

    cmd_log(f"[superpowers] brainstorm iniciado: {idea[:80]}", "decision")
    print(SEP)


def cmd_plan(feature: str) -> None:
    """
    Fase 2 de superpowers: writing-plans.
    Genera un plan de implementacion con tareas de 2-5 minutos.
    """
    os.makedirs(PLANS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    plan_file = os.path.join(PLANS_DIR, f"plan-{timestamp}.json")

    # Desglose automatico basado en la feature
    tareas = _generar_tareas(feature)

    plan = {
        "id":       timestamp,
        "feature":  feature,
        "creado":   datetime.now().isoformat(),
        "estado":   "pendiente",
        "tareas":   tareas,
    }

    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\n{SEP}")
    print(f"  SUPERPOWERS — Plan de implementacion")
    print(SEP)
    print(f"\n  Feature : {feature}")
    print(f"  Plan ID : {timestamp}")
    print(f"\n  TAREAS (orden de implementacion):")
    for i, t in enumerate(tareas, 1):
        print(f"\n  {i}. {t['nombre']}")
        print(f"     Archivo : {t['archivo']}")
        print(f"     Accion  : {t['accion']}")
        print(f"     Test    : {t['test']}")
        print(f"     Tiempo  : {t['tiempo_estimado']}")

    print(f"\n  Plan guardado: {plan_file}")
    print(f"\n  Siguiente paso:")
    print(f"  python skills/superpowers.py tdd \"{tareas[0]['nombre']}\"")

    cmd_log(f"[superpowers] plan creado: {feature[:80]} | {len(tareas)} tareas", "decision")
    print(SEP)


def cmd_tdd(modulo: str) -> None:
    """
    Fase 3 de superpowers: test-driven-development.
    Guia el ciclo RED-GREEN-REFACTOR estricto.
    """
    print(f"\n{SEP}")
    print("  SUPERPOWERS — Test Driven Development")
    print("  Ciclo: RED -> GREEN -> REFACTOR")
    print(SEP)
    print(f"\n  Modulo: {modulo}")

    pasos = [
        ("RED",      "Escribe el test que DEBE FALLAR",   [
            "Identifica el comportamiento esperado",
            "Escribe el test en tests/test_limpieza.py o tests/test_nuevo.py",
            "Ejecuta: python -m pytest tests/ -v",
            "Confirma que el test FALLA (rojo)",
            "NO escribas codigo de implementacion todavia",
        ]),
        ("GREEN",    "Escribe el MINIMO codigo para pasar", [
            "Implementa solo lo necesario para que el test pase",
            "Sin optimizaciones, sin features extras (YAGNI)",
            "Ejecuta: python -m pytest tests/ -v",
            "Confirma que el test PASA (verde)",
        ]),
        ("REFACTOR", "Mejora el codigo sin romper tests",  [
            "Elimina duplicacion (DRY)",
            "Mejora nombres de variables y funciones",
            "Ejecuta: python -m pytest tests/ -v",
            "Confirma que todos los tests siguen en verde",
            "Haz commit: git commit -m 'test: <descripcion>'",
        ]),
    ]

    for fase, titulo, acciones in pasos:
        print(f"\n  [{fase}] {titulo}:")
        for a in acciones:
            print(f"    [ ] {a}")

    print(f"\n  ANTI-PATRONES TDD a evitar:")
    anti = [
        "Escribir codigo antes del test",
        "Hacer el test pasar sin implementar logica real",
        "Saltar el paso REFACTOR",
        "Escribir tests despues de implementar",
        "Tests que nunca fallan (siempre verde desde el inicio)",
    ]
    for a in anti:
        print(f"  [!] {a}")

    cmd_log(f"[superpowers] ciclo TDD iniciado: {modulo}", "nota")
    print(SEP)


def cmd_review(archivo: str) -> None:
    """
    Fase 4 de superpowers: requesting-code-review.
    Checklist de revision de codigo contra el plan.
    """
    print(f"\n{SEP}")
    print(f"  SUPERPOWERS — Code Review")
    print(SEP)
    print(f"\n  Archivo: {archivo}")

    # Cargar ultimo plan si existe
    plan_info = _cargar_ultimo_plan()
    if plan_info:
        print(f"\n  Plan de referencia: {plan_info['feature']}")

    print(f"\n  CHECKLIST DE REVISION (severidades: CRITICO / MAYOR / MENOR):")

    criticos = [
        "El codigo implementa exactamente lo especificado en el plan?",
        "Todos los tests pasan? (python -m pytest tests/ -v)",
        "No hay datos hardcodeados o credenciales expuestas?",
        "Las funciones tienen manejo de errores apropiado?",
    ]
    mayores = [
        "El codigo sigue el patron del resto del proyecto?",
        "Las funciones tienen docstrings descriptivos?",
        "Se eliminaron prints de debug?",
        "Los nombres de variables son descriptivos?",
    ]
    menores = [
        "El codigo sigue PEP8?",
        "Los imports estan organizados (stdlib, terceros, locales)?",
        "Los comentarios son necesarios y utiles?",
    ]

    print(f"\n  CRITICOS (bloquean el merge):")
    for c in criticos:
        print(f"  [ ] {c}")

    print(f"\n  MAYORES (deben resolverse antes de merge):")
    for m in mayores:
        print(f"  [ ] {m}")

    print(f"\n  MENORES (mejoras recomendadas):")
    for m in menores:
        print(f"  [ ] {m}")

    cmd_log(f"[superpowers] code review iniciado: {archivo}", "nota")
    print(SEP)


def cmd_status() -> None:
    """Muestra el estado actual del workflow de superpowers."""
    print(f"\n{SEP}")
    print("  SUPERPOWERS — Estado del workflow")
    print(SEP)

    # Listar planes
    os.makedirs(PLANS_DIR, exist_ok=True)
    planes = sorted([
        f for f in os.listdir(PLANS_DIR) if f.endswith(".json")
    ], reverse=True)

    if not planes:
        print("\n  Sin planes activos.")
        print(f"  Inicia con: python skills/superpowers.py brainstorm \"tu idea\"")
    else:
        print(f"\n  PLANES ({len(planes)}):")
        for p in planes[:5]:
            path = os.path.join(PLANS_DIR, p)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            completadas = sum(1 for t in data["tareas"] if t.get("completada"))
            total       = len(data["tareas"])
            pct         = round(completadas / total * 100) if total else 0
            print(f"\n  [{data['estado'].upper()}] {data['feature'][:50]}")
            print(f"    Progreso: {completadas}/{total} tareas ({pct}%)")
            print(f"    Creado  : {data['creado'][:10]}")

    print(f"\n  COMANDOS DISPONIBLES:")
    comandos = {
        "brainstorm": "Refinar una idea antes de implementar",
        "plan":       "Crear plan de tareas para una feature",
        "tdd":        "Guia ciclo RED-GREEN-REFACTOR",
        "review":     "Checklist de code review",
        "status":     "Ver estado actual",
    }
    for cmd, desc in comandos.items():
        print(f"  python skills/superpowers.py {cmd:<12} <- {desc}")

    print(SEP)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generar_tareas(feature: str) -> list[dict]:
    """Genera desglose de tareas basado en la feature."""
    feature_lower = feature.lower()

    # Tareas base para cualquier feature
    tareas_base = [
        {
            "nombre":          f"Escribir tests para {feature}",
            "archivo":         "tests/test_limpieza.py",
            "accion":          "Agregar clase Test con casos de prueba",
            "test":            "python -m pytest tests/ -v --tb=short",
            "tiempo_estimado": "5 min",
            "completada":      False,
        },
        {
            "nombre":          f"Implementar {feature}",
            "archivo":         "src/limpieza.py o src/transformacion.py",
            "accion":          "Agregar funcion con docstring y manejo de errores",
            "test":            "python -m pytest tests/ -v",
            "tiempo_estimado": "10 min",
            "completada":      False,
        },
        {
            "nombre":          "Actualizar configuracion.yaml si aplica",
            "archivo":         "config/configuracion.yaml",
            "accion":          "Agregar parametros de configuracion",
            "test":            "python analisis_relacion.py",
            "tiempo_estimado": "3 min",
            "completada":      False,
        },
        {
            "nombre":          "Actualizar graphify",
            "archivo":         "graphify-out/",
            "accion":          "python -m graphify . --code-only",
            "test":            "Verificar nuevos nodos en graph.html",
            "tiempo_estimado": "2 min",
            "completada":      False,
        },
        {
            "nombre":          "Commit y registro en aura-mem",
            "archivo":         ".git/",
            "accion":          "git add . && git commit -m 'feat: <descripcion>'",
            "test":            "python memory/mem_search.py --recientes",
            "tiempo_estimado": "2 min",
            "completada":      False,
        },
    ]

    # Tareas especificas segun tipo de feature
    if "dashboard" in feature_lower or "visual" in feature_lower:
        tareas_base.insert(1, {
            "nombre":          "Ejecutar impeccable init",
            "archivo":         "PRODUCT.md",
            "accion":          "python skills/impeccable.py init",
            "test":            "Verificar PRODUCT.md generado",
            "tiempo_estimado": "2 min",
            "completada":      False,
        })

    if "analisis" in feature_lower or "datos" in feature_lower:
        tareas_base.insert(1, {
            "nombre":          "Explorar datos en notebook",
            "archivo":         "notebooks/01_exploracion_inicial.ipynb",
            "accion":          "Agregar celda de analisis exploratorio",
            "test":            "jupyter nbconvert --execute notebooks/01_exploracion_inicial.ipynb",
            "tiempo_estimado": "10 min",
            "completada":      False,
        })

    return tareas_base


def _cargar_ultimo_plan() -> dict | None:
    """Carga el plan mas reciente si existe."""
    os.makedirs(PLANS_DIR, exist_ok=True)
    planes = sorted([
        f for f in os.listdir(PLANS_DIR) if f.endswith(".json")
    ], reverse=True)
    if not planes:
        return None
    with open(os.path.join(PLANS_DIR, planes[0]), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="superpowers: workflow de desarrollo para Aura")
    sub    = parser.add_subparsers(dest="cmd")

    p_b = sub.add_parser("brainstorm", help="Refinar una idea antes de implementar")
    p_b.add_argument("idea")

    p_p = sub.add_parser("plan",    help="Crear plan de tareas para una feature")
    p_p.add_argument("feature")

    p_t = sub.add_parser("tdd",     help="Guia ciclo RED-GREEN-REFACTOR")
    p_t.add_argument("modulo")

    p_r = sub.add_parser("review",  help="Checklist de code review")
    p_r.add_argument("archivo")

    sub.add_parser("status", help="Ver estado del workflow")

    args = parser.parse_args()

    if args.cmd == "brainstorm": cmd_brainstorm(args.idea)
    elif args.cmd == "plan":     cmd_plan(args.feature)
    elif args.cmd == "tdd":      cmd_tdd(args.modulo)
    elif args.cmd == "review":   cmd_review(args.archivo)
    elif args.cmd == "status":   cmd_status()
    else:                        parser.print_help()


if __name__ == "__main__":
    main()
