"""
configuracion.py
----------------
Carga de rutas de datos y umbrales de los KPI.

Rutas (prioridad):
    1. Variables de entorno MONITOREO_RUTA_ODS y MONITOREO_RUTA_CSV
    2. config/rutas_locales.yaml  (archivo local, fuera de git)

Umbrales: config/configuracion.yaml, seccion `umbrales`.
"""

import os
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONFIG = RAIZ / "config" / "configuracion.yaml"
RUTA_LOCAL = RAIZ / "config" / "rutas_locales.yaml"

UMBRALES_DEFECTO = {
    "cobertura_qa": {"verde": 90.0, "amarillo": 70.0},
    "trazabilidad": {"verde": 99.0, "amarillo": 95.0},
    "calidad_ods":  {"verde": 95.0, "amarillo": 85.0},
}


def _leer_yaml(ruta: Path) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def cargar_rutas() -> dict[str, str]:
    """Retorna {'ods': ruta, 'csv': ruta}. Lanza RuntimeError si falta alguna."""
    ods = os.environ.get("MONITOREO_RUTA_ODS", "")
    csv_ = os.environ.get("MONITOREO_RUTA_CSV", "")

    if (not ods or not csv_) and RUTA_LOCAL.exists():
        local = _leer_yaml(RUTA_LOCAL)
        ods = ods or str(local.get("ods") or "")
        csv_ = csv_ or str(local.get("csv") or "")

    faltan = [n for n, v in (("ods", ods), ("csv", csv_)) if not v]
    if faltan:
        raise RuntimeError(
            f"Faltan rutas: {', '.join(faltan)}. Define MONITOREO_RUTA_ODS y "
            f"MONITOREO_RUTA_CSV, o crea config/rutas_locales.yaml "
            f"(ver config/rutas_locales.example.yaml)."
        )
    return {"ods": ods, "csv": csv_}


def cargar_umbrales() -> dict[str, dict[str, float]]:
    """Umbrales de semaforo: valores del YAML sobre los valores por defecto."""
    umbrales = {k: dict(v) for k, v in UMBRALES_DEFECTO.items()}
    if RUTA_CONFIG.exists():
        for nombre, valores in (_leer_yaml(RUTA_CONFIG).get("umbrales") or {}).items():
            if nombre in umbrales and isinstance(valores, dict):
                umbrales[nombre].update({k: float(v) for k, v in valores.items()})
    return umbrales
