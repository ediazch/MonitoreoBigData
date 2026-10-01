"""
informe_excel.py
----------------
Ensambla el informe Excel para el POM a partir del resultado de analisis_cruce.

Hojas: Resumen ejecutivo, Dashboard, Cobertura por tipo, Calidad ODS,
Matriz CSV por hoja, Detalle CSV, ODS sin caso QA, Excluidos ODS, Metodologia.
"""

import os
from datetime import datetime
from typing import Any

from openpyxl import Workbook

from informe_dashboard import hoja_dashboard
from informe_hojas_gerencial import hoja_metodologia, hoja_resumen
from informe_hojas_tecnicas import (hoja_calidad, hoja_cobertura, hoja_detalle_csv,
                                    hoja_excluidos, hoja_matriz, hoja_sin_qa)


def generar_informe(res: dict[str, Any], directorio: str) -> str:
    """Crea el .xlsx en `directorio` y retorna su ruta absoluta."""
    os.makedirs(directorio, exist_ok=True)
    wb = Workbook()
    hoja_resumen(wb, res)
    hoja_dashboard(wb, res)
    hoja_cobertura(wb, res)
    hoja_calidad(wb, res)
    hoja_matriz(wb, res)
    hoja_detalle_csv(wb, res)
    hoja_sin_qa(wb, res)
    hoja_excluidos(wb, res)
    hoja_metodologia(wb, res)

    wb.properties.title = "Informe de cruce CSV vs ODS"
    wb.properties.creator = "MonitoreoBigData"
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(directorio, f"informe_cruce_{marca}.xlsx")
    wb.save(ruta)
    return os.path.abspath(ruta)
