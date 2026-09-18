"""
limpieza.py
-----------
Funciones de limpieza y lectura de datos para el proyecto MonitoreoBigData.
Usa solo librerias de la stdlib de Python (zipfile, xml, csv).
"""

import csv
import zipfile
import xml.etree.ElementTree as ET
from typing import Any


# ---------------------------------------------------------------------------
# Constantes de namespaces ODS (formato OpenDocument Spreadsheet)
# ---------------------------------------------------------------------------
NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_TEXT  = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"


# ---------------------------------------------------------------------------
# Lectura de archivos
# ---------------------------------------------------------------------------

def leer_csv(ruta: str, encoding: str = "utf-8-sig") -> list[list[str]]:
    """
    Lee un archivo CSV y retorna lista de filas.
    Filtra filas vacias automaticamente.

    Args:
        ruta:     Ruta absoluta al archivo CSV.
        encoding: Encoding del archivo (default utf-8-sig para BOM de Excel).

    Returns:
        Lista de listas con los valores de cada fila.
    """
    filas = []
    with open(ruta, encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f)
        for fila in reader:
            if any(celda.strip() for celda in fila):
                filas.append(fila)
    return filas


def leer_ods(ruta: str) -> dict[str, list[list[str]]]:
    """
    Lee un archivo ODS (OpenDocument Spreadsheet) sin dependencias externas.
    Internamente un ODS es un ZIP que contiene content.xml.

    Args:
        ruta: Ruta absoluta al archivo ODS.

    Returns:
        Diccionario { nombre_hoja: [[celda, celda, ...], ...] }
    """
    with zipfile.ZipFile(ruta, "r") as z:
        content_xml = z.read("content.xml").decode("utf-8")

    root = ET.fromstring(content_xml)
    hojas = {}

    for sheet in root.findall(f".//{{{NS_TABLE}}}table"):
        nombre_hoja = sheet.get(f"{{{NS_TABLE}}}name", "")
        filas_hoja  = []

        for row in sheet.findall(f".//{{{NS_TABLE}}}table-row"):
            celdas = row.findall(f".//{{{NS_TABLE}}}table-cell")
            valores = [_extraer_texto_celda(c) for c in celdas]
            if any(v.strip() for v in valores):
                filas_hoja.append(valores)

        hojas[nombre_hoja] = filas_hoja

    return hojas


def _extraer_texto_celda(celda: Any) -> str:
    """Extrae el texto visible de una celda ODS."""
    partes = celda.findall(f".//{{{NS_TEXT}}}p")
    return " ".join((p.text or "").strip() for p in partes).strip()


# ---------------------------------------------------------------------------
# Limpieza de datos
# ---------------------------------------------------------------------------

def limpiar_id(valor: str) -> str:
    """
    Normaliza un numero de identificacion:
    - Elimina espacios, comillas simples/dobles, guiones.
    - Retorna string limpio en minusculas para comparacion uniforme.
    """
    return valor.strip().replace("'", "").replace('"', "").replace("-", "").replace(" ", "")


def limpiar_tipo(valor: str) -> str:
    """Normaliza el tipo de documento a string entero sin espacios."""
    return valor.strip()


def normalizar_filas_csv(filas: list[list[str]]) -> list[dict]:
    """
    Convierte las filas crudas del CSV en lista de dicts normalizados.

    Estructura CSV esperada:
        columna 0 = tipo_id
        columna 1 = num_id

    Returns:
        Lista de { 'tipo_id': str, 'num_id': str }
    """
    resultado = []
    for fila in filas:
        if len(fila) < 2:
            continue
        resultado.append({
            "tipo_id": limpiar_tipo(fila[0]),
            "num_id":  limpiar_id(fila[1]),
        })
    return resultado


def normalizar_filas_ods(hojas: dict[str, list[list[str]]]) -> list[dict]:
    """
    Extrae y normaliza los registros de todas las hojas del ODS.
    Descarta filas de encabezado (donde tipo_id no es numerico).
    Columnas ODS: 0=tipo_id, 1=num_id

    Returns:
        Lista de { 'tipo_id': str, 'num_id': str, 'hoja': str }
    """
    resultado = []
    for nombre_hoja, filas in hojas.items():
        for fila in filas:
            if len(fila) < 2:
                continue
            tipo = limpiar_tipo(fila[0])
            num  = limpiar_id(fila[1])
            # Descartar encabezados o valores no numericos
            if not tipo.isdigit() or not num.isdigit():
                continue
            resultado.append({
                "tipo_id": tipo,
                "num_id":  num,
                "hoja":    nombre_hoja,
            })
    return resultado


def eliminar_duplicados(registros: list[dict], clave: tuple[str, ...] = ("tipo_id", "num_id")) -> list[dict]:
    """
    Elimina registros duplicados por clave compuesta.

    Args:
        registros: Lista de dicts.
        clave:     Campos que forman la clave unica.

    Returns:
        Lista sin duplicados manteniendo el primer occurrence.
    """
    vistos   = set()
    limpios  = []
    for r in registros:
        k = tuple(r.get(c, "") for c in clave)
        if k not in vistos:
            vistos.add(k)
            limpios.append(r)
    return limpios
