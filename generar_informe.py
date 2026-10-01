"""
generar_informe.py
------------------
Genera el informe Excel gerencial y tecnico del cruce CSV vs ODS.

Uso:
    python generar_informe.py

Rutas de entrada (prioridad): variables MONITOREO_RUTA_ODS / MONITOREO_RUTA_CSV,
o config/rutas_locales.yaml (ignorado por git).
Salida: data/processed/informe_cruce_<fecha_hora>.xlsx (ignorado por git).
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from analisis_cruce import analizar
from configuracion import cargar_rutas, cargar_umbrales
from dataset_limpio import escribir_dataset_limpio
from informe_excel import generar_informe


def copiar_originales(rutas: dict, destino: str) -> dict:
    """Copia los archivos fuente a data/raw/ (los originales no se tocan) y retorna las rutas de la copia."""
    os.makedirs(destino, exist_ok=True)
    copias = {}
    for clave, nombre in (("csv", "dataset_original.csv"), ("ods", "estimador_original.ods")):
        copias[clave] = os.path.join(destino, nombre)
        shutil.copy2(rutas[clave], copias[clave])
    return copias


def main() -> int:
    try:
        rutas = cargar_rutas()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    for etiqueta, ruta in (("CSV", rutas["csv"]), ("ODS", rutas["ods"])):
        if not os.path.isfile(ruta):
            print(f"ERROR: no existe el archivo {etiqueta} configurado.")
            return 1

    raiz = os.path.dirname(os.path.abspath(__file__))
    copias = copiar_originales(rutas, os.path.join(raiz, "data", "raw"))
    print("Originales copiados a data/raw/ (los archivos fuente no se modifican).")

    print("Analizando: el CSV se cruza contra todas las hojas del ODS...")
    res = analizar(copias["csv"], copias["ods"], cargar_umbrales())

    salida = os.path.join(raiz, "data", "processed")
    n = escribir_dataset_limpio(res, os.path.join(salida, "dataset_limpio.csv"))
    print(f"Dataset limpio escrito: {n} renglones.")
    ruta_xlsx = generar_informe(res, salida)

    s = res["resumen"]
    print(f"  Casos CSV: {s['csv_total']} | IDs validos ODS: {s['ods_validos']}")
    print(f"  Trazabilidad CSV a ODS: {s['trazabilidad']:.2f}% | Cobertura QA del ODS: {s['cobertura_global']:.2f}%")
    for k in res["kpis"]:
        if k["semaforo"] in ("ROJO", "AMARILLO"):
            print(f"  [{k['semaforo']}] {k['nombre']}: {k['valor']} {k['unidad']} - {k['detalle']}")
    print(f"Informe generado: {ruta_xlsx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
