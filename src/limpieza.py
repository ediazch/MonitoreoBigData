"""
limpieza.py
-----------
Funciones de lectura y limpieza de datos para el proyecto MonitoreoBigData.
Usa solo librerias de la stdlib de Python (zipfile, xml, csv).
"""

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Constantes de namespaces ODS (formato OpenDocument Spreadsheet)
# ---------------------------------------------------------------------------
NS_TABLE  = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_TEXT   = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
NS_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"

# Limites defensivos contra archivos ODS malformados o maliciosos
_MAX_BYTES_XML = 200 * 1024 * 1024
_MAX_REPETICION_FILA = 1000
_MAX_REPETICION_COLUMNA = 64
_PATRON_CIENTIFICA = re.compile(r"^\d+(?:[.,]\d+)?[eE][+-]?\d+$")


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
    return [celdas for _, celdas in leer_csv_con_fila(ruta, encoding)]


def leer_csv_con_fila(ruta: str, encoding: str = "utf-8-sig") -> list[tuple[int, list[str]]]:
    """
    Igual que leer_csv, pero conserva el numero de fila original (base 1)
    para poder trazar cada registro hasta el archivo fuente.
    """
    filas = []
    with open(ruta, encoding=encoding, errors="replace", newline="") as f:
        for numero, fila in enumerate(csv.reader(f), start=1):
            if any(celda.strip() for celda in fila):
                filas.append((numero, fila))
    return filas


def _cargar_content_xml(ruta: str) -> ET.Element:
    """
    Abre el ODS (ZIP) y parsea content.xml con salvaguardas:
    tamano maximo y rechazo de declaraciones DTD/ENTITY (XXE, billion laughs).
    """
    with zipfile.ZipFile(ruta, "r") as z:
        if z.getinfo("content.xml").file_size > _MAX_BYTES_XML:
            raise ValueError("content.xml excede el tamano maximo permitido")
        datos = z.read("content.xml")
    if re.search(rb"<!(DOCTYPE|ENTITY)", datos, re.IGNORECASE):
        raise ValueError("El ODS contiene declaraciones DTD/ENTITY no permitidas")
    return ET.fromstring(datos)


def _valor_celda(celda: Any) -> tuple[str, str | None]:
    """
    Retorna (texto, nota). Si el texto visible esta en notacion cientifica
    (p. ej. 1,23E+09) recupera el valor exacto almacenado en office:value.
    """
    texto = _extraer_texto_celda(celda)
    if (
        _PATRON_CIENTIFICA.match(texto)
        and celda.get(f"{{{NS_OFFICE}}}value-type") == "float"
    ):
        crudo = celda.get(f"{{{NS_OFFICE}}}value")
        if crudo is not None:
            try:
                valor = Decimal(crudo)
                if valor == valor.to_integral_value():
                    return str(int(valor)), "notacion_cientifica_recuperada"
            except InvalidOperation:
                pass
    return texto, None


def leer_ods_detallado(ruta: str) -> list[dict]:
    """
    Lee un ODS sin dependencias externas y conserva la trazabilidad.

    Expande filas/columnas repetidas (number-rows/columns-repeated) y numera
    las filas tal como aparecen en la hoja de calculo.

    Returns:
        Lista de { 'hoja': str, 'fila': int, 'celdas': list[str], 'notas': list[str] }
        Solo incluye filas con algun valor.
    """
    root = _cargar_content_xml(ruta)
    resultado = []

    for hoja in root.iter(f"{{{NS_TABLE}}}table"):
        nombre_hoja = hoja.get(f"{{{NS_TABLE}}}name", "")
        fila_actual = 0

        for fila in hoja.iter(f"{{{NS_TABLE}}}table-row"):
            repeticion = int(fila.get(f"{{{NS_TABLE}}}number-rows-repeated", "1"))
            primera = fila_actual + 1
            fila_actual += repeticion

            celdas: list[str] = []
            notas: list[str] = []
            for celda in fila.findall(f"{{{NS_TABLE}}}table-cell"):
                texto, nota = _valor_celda(celda)
                if nota:
                    notas.append(nota)
                veces = min(
                    int(celda.get(f"{{{NS_TABLE}}}number-columns-repeated", "1")),
                    _MAX_REPETICION_COLUMNA,
                )
                celdas.extend([texto] * veces)

            while celdas and not celdas[-1].strip():
                celdas.pop()
            if not any(c.strip() for c in celdas):
                continue

            for k in range(min(repeticion, _MAX_REPETICION_FILA)):
                resultado.append({
                    "hoja": nombre_hoja,
                    "fila": primera + k,
                    "celdas": list(celdas),
                    "notas": list(notas),
                })

    return resultado


def leer_ods(ruta: str) -> dict[str, list[list[str]]]:
    """
    Lee un archivo ODS (OpenDocument Spreadsheet) sin dependencias externas.

    Args:
        ruta: Ruta absoluta al archivo ODS.

    Returns:
        Diccionario { nombre_hoja: [[celda, celda, ...], ...] }
    """
    hojas: dict[str, list[list[str]]] = {}
    for registro in leer_ods_detallado(ruta):
        hojas.setdefault(registro["hoja"], []).append(registro["celdas"])
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
    - Retorna string limpio para comparacion uniforme.
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
        Lista sin duplicados manteniendo la primera ocurrencia.
    """
    vistos   = set()
    limpios  = []
    for r in registros:
        k = tuple(r.get(c, "") for c in clave)
        if k not in vistos:
            vistos.add(k)
            limpios.append(r)
    return limpios
