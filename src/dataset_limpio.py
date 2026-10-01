"""
dataset_limpio.py
-----------------
Escribe data/processed/dataset_limpio.csv: un renglon por caso del CSV con su
resultado del cruce. Contiene IDs completos, por eso vive solo en local
(data/processed/ esta ignorado por git).
"""

import csv
import os
from typing import Any

COLUMNAS = ["fila_csv", "tipo_id", "num_id", "resultado", "hoja_ods", "fila_ods"]


def escribir_dataset_limpio(res: dict[str, Any], ruta: str) -> int:
    """Escribe el CSV limpio y retorna la cantidad de renglones."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        for d in res["detalle_csv"]:
            w.writerow([d["fila_csv"], d["tipo"], d["num_id"], d["resultado"], d["hoja_ods"], d["fila_ods"]])
    return len(res["detalle_csv"])
