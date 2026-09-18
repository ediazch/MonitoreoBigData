"""
transformacion.py
-----------------
Funciones de analisis y cruce de datos entre el ODS (estimador de ingresos)
y el CSV (casos de prueba QA del Adviser).

Relacion clave:
    CSV.columna_0  (tipo_id)  <-->  prefijo numerico del nombre de hoja ODS
    CSV.columna_1  (num_id)   <-->  ODS.columna_1 (num_id dentro de cada hoja)
"""

from typing import Any


# ---------------------------------------------------------------------------
# Mapeo de tipos de documento
# ---------------------------------------------------------------------------

TIPOS_DOCUMENTO: dict[str, str] = {
    "1":  "Cedula de Ciudadania",
    "3":  "Cedula de Extranjeria",
    "4":  "Tarjeta de Identidad",
    "5":  "Pasaporte",
    "6":  "Tarjeta Seguro Social",
    "9":  "Registro Civil",
    "10": "Carnet Diplomatico",
    "11": "Patente de Automotor",
    "12": "Permiso Especial de Permanencia (PEP)",
    "13": "Permiso Proteccion Temporal (PPT)",
}


# ---------------------------------------------------------------------------
# Cruce / coincidencias
# ---------------------------------------------------------------------------

def cruzar_datos(
    registros_csv: list[dict],
    registros_ods: list[dict],
) -> dict[str, Any]:
    """
    Cruza los registros del CSV contra los del ODS usando tipo_id + num_id.

    Args:
        registros_csv: Salida de limpieza.normalizar_filas_csv()
        registros_ods: Salida de limpieza.normalizar_filas_ods()

    Returns:
        Dict con:
          - coincidencias:     registros presentes en ambos
          - solo_en_csv:       presentes solo en CSV
          - solo_en_ods:       presentes solo en ODS
          - resumen_por_tipo:  conteo agrupado por tipo de documento
    """
    # Construir sets de claves (tipo_id, num_id)
    claves_csv = {(r["tipo_id"], r["num_id"]): r for r in registros_csv}
    claves_ods = {(r["tipo_id"], r["num_id"]): r for r in registros_ods}

    claves_comunes  = set(claves_csv.keys()) & set(claves_ods.keys())
    claves_solo_csv = set(claves_csv.keys()) - set(claves_ods.keys())
    claves_solo_ods = set(claves_ods.keys()) - set(claves_csv.keys())

    coincidencias = [
        {
            "tipo_id":     k[0],
            "num_id":      k[1],
            "descripcion": TIPOS_DOCUMENTO.get(k[0], "Tipo desconocido"),
            "hoja_ods":    claves_ods[k].get("hoja", ""),
        }
        for k in sorted(claves_comunes)
    ]

    solo_csv = [
        {**claves_csv[k], "descripcion": TIPOS_DOCUMENTO.get(k[0], "Tipo desconocido")}
        for k in sorted(claves_solo_csv)
    ]

    solo_ods = [
        {**claves_ods[k], "descripcion": TIPOS_DOCUMENTO.get(k[0], "Tipo desconocido")}
        for k in sorted(claves_solo_ods)
    ]

    # Resumen por tipo de documento
    resumen: dict[str, dict] = {}
    for tipo, desc in TIPOS_DOCUMENTO.items():
        total_csv    = sum(1 for r in registros_csv if r["tipo_id"] == tipo)
        total_ods    = sum(1 for r in registros_ods if r["tipo_id"] == tipo)
        coincide     = sum(1 for c in coincidencias if c["tipo_id"] == tipo)
        if total_csv > 0 or total_ods > 0:
            resumen[tipo] = {
                "descripcion":   desc,
                "total_csv":     total_csv,
                "total_ods":     total_ods,
                "coincidencias": coincide,
                "cobertura_pct": round(coincide / total_csv * 100, 1) if total_csv else 0.0,
            }

    return {
        "coincidencias":     coincidencias,
        "solo_en_csv":       solo_csv,
        "solo_en_ods":       solo_ods,
        "resumen_por_tipo":  resumen,
    }


# ---------------------------------------------------------------------------
# Estadisticas globales
# ---------------------------------------------------------------------------

def calcular_estadisticas(resultado_cruce: dict) -> dict[str, Any]:
    """
    Calcula metricas globales del cruce de datos.

    Returns:
        Dict con conteos y porcentajes globales.
    """
    total_coincidencias = len(resultado_cruce["coincidencias"])
    total_solo_csv      = len(resultado_cruce["solo_en_csv"])
    total_solo_ods      = len(resultado_cruce["solo_en_ods"])
    total_csv           = total_coincidencias + total_solo_csv
    total_ods           = total_coincidencias + total_solo_ods
    total_universo      = total_csv + total_solo_ods

    cobertura_csv = round(total_coincidencias / total_csv * 100, 2) if total_csv else 0.0
    cobertura_ods = round(total_coincidencias / total_ods * 100, 2) if total_ods else 0.0

    return {
        "total_registros_csv":  total_csv,
        "total_registros_ods":  total_ods,
        "total_universo":       total_universo,
        "coincidencias":        total_coincidencias,
        "solo_en_csv":          total_solo_csv,
        "solo_en_ods":          total_solo_ods,
        "cobertura_csv_pct":    cobertura_csv,
        "cobertura_ods_pct":    cobertura_ods,
    }
