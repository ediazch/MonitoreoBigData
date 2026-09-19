"""
analisis_relacion.py
--------------------
Script principal: cruza los datos del ODS (Income Estimator) contra
el CSV (casos de prueba QA Adviser) e imprime por consola todos los
resultados del analisis de relacion.

Uso:
    python analisis_relacion.py
"""

import sys
import os
import yaml

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from limpieza import (
    leer_csv,
    leer_ods,
    normalizar_filas_csv,
    normalizar_filas_ods,
    eliminar_duplicados,
)
from transformacion import cruzar_datos, calcular_estadisticas, TIPOS_DOCUMENTO

# ---------------------------------------------------------------------------
# Configuracion de rutas — leidas desde configuracion.yaml (SEC-001 fix)
# Las rutas absolutas se definen en config, no en el codigo
# ---------------------------------------------------------------------------
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "configuracion.yaml")

def _cargar_rutas() -> tuple[str, str]:
    """Lee las rutas desde configuracion.yaml. Fallback a variables de entorno."""
    # Prioridad 1: variables de entorno (mas seguro para CI/CD)
    ruta_ods = os.environ.get("MONITOREO_RUTA_ODS")
    ruta_csv = os.environ.get("MONITOREO_RUTA_CSV")
    if ruta_ods and ruta_csv:
        return ruta_ods, ruta_csv
    # Prioridad 2: configuracion.yaml
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        rutas = cfg.get("rutas", {}).get("datos_externos", {})
        return rutas.get("ods", ""), rutas.get("csv", "")
    except (FileNotFoundError, KeyError, TypeError) as e:
        raise RuntimeError(
            f"No se encontraron rutas en config/configuracion.yaml ni en variables de entorno.\n"
            f"Define MONITOREO_RUTA_ODS y MONITOREO_RUTA_CSV o configura rutas.datos_externos en el YAML.\n"
            f"Error: {e}"
        )

RUTA_ODS, RUTA_CSV = _cargar_rutas()


def _enmascarar_id(num_id: str) -> str:
    """
    Enmascara un numero de ID para impresion segura. (SEC-007 fix)
    Ejemplo: 1069729185 -> 106****185
    """
    if len(num_id) <= 6:
        return "***"
    return num_id[:3] + "*" * (len(num_id) - 6) + num_id[-3:]

# ---------------------------------------------------------------------------
# Helpers de presentacion
# ---------------------------------------------------------------------------
SEP_DOBLE  = "=" * 70
SEP_SIMPLE = "-" * 70
SEP_SECCION= "*" * 70

def titulo(texto: str) -> None:
    print(f"\n{SEP_DOBLE}")
    print(f"  {texto}")
    print(SEP_DOBLE)

def seccion(texto: str) -> None:
    print(f"\n{SEP_SIMPLE}")
    print(f"  {texto}")
    print(SEP_SIMPLE)

def imprimir_tabla(registros: list[dict], campos: list[str], max_filas: int = None) -> None:
    """Imprime lista de dicts como tabla en consola."""
    if not registros:
        print("  (sin registros)")
        return
    anchos = {c: max(len(c), max(len(str(r.get(c, ""))) for r in registros)) for c in campos}
    encabezado = " | ".join(c.upper().ljust(anchos[c]) for c in campos)
    linea      = "-+-".join("-" * anchos[c] for c in campos)
    print(f"  {encabezado}")
    print(f"  {linea}")
    limite = min(len(registros), max_filas) if max_filas else len(registros)
    for r in registros[:limite]:
        fila = " | ".join(str(r.get(c, "")).ljust(anchos[c]) for c in campos)
        print(f"  {fila}")
    if max_filas and len(registros) > max_filas:
        print(f"  ... y {len(registros) - max_filas} registros mas.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:

    # -----------------------------------------------------------------------
    # 1. CARGA DE DATOS
    # -----------------------------------------------------------------------
    titulo("ANALISIS DE RELACION DE DATOS — MonitoreoBigData")
    print(f"\n  ODS : {RUTA_ODS}")
    print(f"  CSV : {RUTA_CSV}")

    print("\n  [1/4] Cargando archivos...")
    filas_csv = leer_csv(RUTA_CSV)
    hojas_ods = leer_ods(RUTA_ODS)
    print(f"        CSV  -> {len(filas_csv)} filas cargadas")
    print(f"        ODS  -> {len(hojas_ods)} hojas cargadas: {list(hojas_ods.keys())}")

    # -----------------------------------------------------------------------
    # 2. LIMPIEZA Y NORMALIZACION
    # -----------------------------------------------------------------------
    print("\n  [2/4] Limpiando y normalizando datos...")
    registros_csv = normalizar_filas_csv(filas_csv)
    registros_ods = normalizar_filas_ods(hojas_ods)
    registros_csv = eliminar_duplicados(registros_csv)
    registros_ods = eliminar_duplicados(registros_ods)
    print(f"        CSV  -> {len(registros_csv)} registros validos (sin duplicados)")
    print(f"        ODS  -> {len(registros_ods)} registros validos (sin duplicados)")

    # -----------------------------------------------------------------------
    # 3. CRUCE DE DATOS
    # -----------------------------------------------------------------------
    print("\n  [3/4] Cruzando datos (tipo_id + num_id)...")
    resultado = cruzar_datos(registros_csv, registros_ods)
    stats     = calcular_estadisticas(resultado)
    print("        Cruce completado.")

    # -----------------------------------------------------------------------
    # 4. RESULTADOS
    # -----------------------------------------------------------------------
    print("\n  [4/4] Generando reporte...")

    # -- Estadisticas globales -----------------------------------------------
    titulo("ESTADISTICAS GLOBALES")
    print(f"  Total registros CSV (QA Adviser)   : {stats['total_registros_csv']}")
    print(f"  Total registros ODS (Estimador)    : {stats['total_registros_ods']}")
    print(f"  Universo total de IDs              : {stats['total_universo']}")
    print()
    print(f"  [COINCIDENCIAS]   IDs en AMBOS archivos : {stats['coincidencias']}")
    print(f"  [SOLO EN CSV]     IDs solo en QA Adviser: {stats['solo_en_csv']}")
    print(f"  [SOLO EN ODS]     IDs solo en Estimador : {stats['solo_en_ods']}")
    print()
    print(f"  Cobertura CSV sobre ODS : {stats['cobertura_csv_pct']}%")
    print(f"  Cobertura ODS sobre CSV : {stats['cobertura_ods_pct']}%")

    # -- Resumen por tipo de documento ----------------------------------------
    titulo("RELACION POR TIPO DE DOCUMENTO")
    resumen = resultado["resumen_por_tipo"]
    campos  = ["tipo_id", "descripcion", "total_csv", "total_ods", "coincidencias", "cobertura_pct"]
    filas_resumen = [
        {
            "tipo_id":      tipo,
            "descripcion":  data["descripcion"],
            "total_csv":    data["total_csv"],
            "total_ods":    data["total_ods"],
            "coincidencias":data["coincidencias"],
            "cobertura_pct":f"{data['cobertura_pct']}%",
        }
        for tipo, data in sorted(resumen.items(), key=lambda x: int(x[0]))
    ]
    imprimir_tabla(filas_resumen, campos)

    # -- Coincidencias detalladas — IDs enmascarados (SEC-007 fix) -----------
    seccion(f"COINCIDENCIAS ENCONTRADAS — {len(resultado['coincidencias'])} registros presentes en AMBOS archivos")
    coincidencias_mask = [
        {**r, "num_id": _enmascarar_id(r["num_id"])}
        for r in resultado["coincidencias"]
    ]
    imprimir_tabla(coincidencias_mask, campos=["tipo_id", "descripcion", "num_id", "hoja_ods"], max_filas=30)

    # -- Solo en CSV ----------------------------------------------------------
    seccion(f"SOLO EN CSV (QA Adviser) — {len(resultado['solo_en_csv'])} registros NO encontrados en el Estimador")
    solo_csv_mask = [
        {**r, "num_id": _enmascarar_id(r["num_id"])}
        for r in resultado["solo_en_csv"]
    ]
    imprimir_tabla(solo_csv_mask, campos=["tipo_id", "descripcion", "num_id"], max_filas=20)

    # -- Solo en ODS ----------------------------------------------------------
    seccion(f"SOLO EN ODS (Estimador) — {len(resultado['solo_en_ods'])} registros NO encontrados en el CSV QA")
    solo_ods_mask = [
        {**r, "num_id": _enmascarar_id(r["num_id"])}
        for r in resultado["solo_en_ods"]
    ]
    imprimir_tabla(solo_ods_mask, campos=["tipo_id", "descripcion", "num_id", "hoja"], max_filas=20)

    # -- Distribucion de tipos en CSV -----------------------------------------
    titulo("DISTRIBUCION DE TIPOS DE DOCUMENTO EN CSV (QA)")
    print(f"  {'TIPO':<6} {'DESCRIPCION':<40} {'CANTIDAD':>10}  {'%':>6}")
    print(f"  {'-'*6} {'-'*40} {'-'*10}  {'-'*6}")
    total = len(registros_csv)
    por_tipo_csv = {}
    for r in registros_csv:
        por_tipo_csv[r["tipo_id"]] = por_tipo_csv.get(r["tipo_id"], 0) + 1
    for tipo, cant in sorted(por_tipo_csv.items(), key=lambda x: int(x[0])):
        desc = TIPOS_DOCUMENTO.get(tipo, "Desconocido")
        pct  = round(cant / total * 100, 1)
        print(f"  {tipo:<6} {desc:<40} {cant:>10}  {pct:>5}%")

    # -- Conclusiones ---------------------------------------------------------
    titulo("CONCLUSIONES Y RELACION ENTRE ARCHIVOS")
    print("""
  ESTRUCTURA DE LA RELACION:
  --------------------------
  El archivo CSV (QA Adviser) contiene pares (tipo_documento, num_id) que
  representan los identificadores de personas evaluadas en pruebas del sistema.

  El archivo ODS (Income Estimator) organiza esos mismos identificadores
  en hojas separadas por tipo de documento, con metadatos adicionales
  como longitud del ID y formato esperado.

  CLAVE DE UNION:
    CSV.columna_0  (tipo_id)  <--> prefijo numerico del nombre de hoja ODS
    CSV.columna_1  (num_id)   <--> ODS.columna_1 (num_id en cada hoja)

  INTERPRETACION DE RESULTADOS:
    - Las COINCIDENCIAS son IDs que el sistema QA probo Y que el estimador
      de ingresos tiene registrados -> casos con cobertura completa.
    - Los registros SOLO EN CSV son casos probados en QA que no tienen
      referencia en el estimador -> posibles gaps de datos.
    - Los registros SOLO EN ODS son IDs en el estimador que aun no
      fueron cubiertos por los casos de prueba QA.
    """)

    print(f"\n{SEP_DOBLE}")
    print("  Analisis finalizado.")
    print(SEP_DOBLE)


if __name__ == "__main__":
    main()
