"""
test_limpieza.py
----------------
Pruebas unitarias para src/limpieza.py y src/transformacion.py
Siguiendo estandares ISTQB:
  - Pruebas de caja blanca sobre funciones de limpieza
  - Particion de equivalencia y analisis de valores limite para IDs
  - Pruebas de integracion ligera sobre el cruce de datos
"""

import sys
import os
import pytest

# Agregar el directorio raiz al path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.limpieza import (
    limpiar_id,
    limpiar_tipo,
    normalizar_filas_csv,
    normalizar_filas_ods,
    eliminar_duplicados,
)
from src.transformacion import cruzar_datos, calcular_estadisticas


# ===========================================================================
# SECCION 1: Pruebas unitarias — limpiar_id
# CONCEPTO ISTQB: Particion de equivalencia
#   Clase valida:   IDs numericos con ruido (espacios, comillas, guiones)
#   Clase invalida: strings vacios, None
# ===========================================================================

class TestLimpiarId:
    def test_id_simple(self):
        """ID sin ruido debe retornarse igual."""
        assert limpiar_id("1069729185") == "1069729185"

    def test_id_con_comilla_simple(self):
        """IDs exportados de Excel suelen venir con comilla al inicio."""
        assert limpiar_id("'1069729185'") == "1069729185"

    def test_id_con_espacios(self):
        """Espacios en blanco deben eliminarse."""
        assert limpiar_id("  1069729185  ") == "1069729185"

    def test_id_con_guion(self):
        """IDs con guion (e.g. pasaportes) deben unificarse."""
        assert limpiar_id("10697-29185") == "1069729185"

    def test_id_con_comilla_doble(self):
        assert limpiar_id('"1069729185"') == "1069729185"

    def test_id_vacio(self):
        """ID vacio retorna string vacio."""
        assert limpiar_id("") == ""

    def test_id_solo_espacios(self):
        assert limpiar_id("   ") == ""


# ===========================================================================
# SECCION 2: Pruebas unitarias — limpiar_tipo
# ===========================================================================

class TestLimpiarTipo:
    def test_tipo_simple(self):
        assert limpiar_tipo("1") == "1"

    def test_tipo_con_espacios(self):
        assert limpiar_tipo("  12  ") == "12"

    def test_tipo_doble_digito(self):
        assert limpiar_tipo("13") == "13"


# ===========================================================================
# SECCION 3: Pruebas unitarias — normalizar_filas_csv
# ===========================================================================

class TestNormalizarFilasCSV:
    def test_fila_valida(self):
        filas = [["1", "1069729185"]]
        resultado = normalizar_filas_csv(filas)
        assert len(resultado) == 1
        assert resultado[0]["tipo_id"] == "1"
        assert resultado[0]["num_id"] == "1069729185"

    def test_fila_incompleta_ignorada(self):
        """Filas con menos de 2 columnas deben ignorarse."""
        filas = [["1"], ["4", "1526983649"]]
        resultado = normalizar_filas_csv(filas)
        assert len(resultado) == 1
        assert resultado[0]["tipo_id"] == "4"

    def test_multiples_tipos(self):
        filas = [["1", "111"], ["4", "222"], ["13", "333"]]
        resultado = normalizar_filas_csv(filas)
        assert len(resultado) == 3
        tipos = [r["tipo_id"] for r in resultado]
        assert "1" in tipos
        assert "13" in tipos

    def test_lista_vacia(self):
        assert normalizar_filas_csv([]) == []


# ===========================================================================
# SECCION 4: Pruebas unitarias — normalizar_filas_ods
# CONCEPTO ISTQB: Prueba de valores limite — encabezados no deben incluirse
# ===========================================================================

class TestNormalizarFilasODS:
    def test_descarta_encabezado_texto(self):
        """Filas donde tipo_id es texto (ej: 'tipoID') deben descartarse."""
        hojas = {
            "13_PPT": [
                ["tipoID", "NumID"],   # encabezado — debe descartarse
                ["13", "2000000023"],
            ]
        }
        resultado = normalizar_filas_ods(hojas)
        assert len(resultado) == 1
        assert resultado[0]["num_id"] == "2000000023"

    def test_descarta_num_id_no_numerico(self):
        """Registros con num_id no numerico deben descartarse."""
        hojas = {"1_CC": [["1", "INVALIDO"], ["1", "1069729185"]]}
        resultado = normalizar_filas_ods(hojas)
        assert len(resultado) == 1

    def test_hoja_incluida_en_resultado(self):
        hojas = {"4_TI": [["4", "1526983649"]]}
        resultado = normalizar_filas_ods(hojas)
        assert resultado[0]["hoja"] == "4_TI"

    def test_multiple_hojas(self):
        hojas = {
            "1_CC": [["1", "111"], ["1", "222"]],
            "4_TI": [["4", "333"]],
        }
        resultado = normalizar_filas_ods(hojas)
        assert len(resultado) == 3


# ===========================================================================
# SECCION 5: Pruebas unitarias — eliminar_duplicados
# ===========================================================================

class TestEliminarDuplicados:
    def test_sin_duplicados(self):
        registros = [
            {"tipo_id": "1", "num_id": "111"},
            {"tipo_id": "1", "num_id": "222"},
        ]
        assert len(eliminar_duplicados(registros)) == 2

    def test_con_duplicados(self):
        registros = [
            {"tipo_id": "1", "num_id": "111"},
            {"tipo_id": "1", "num_id": "111"},
            {"tipo_id": "4", "num_id": "333"},
        ]
        resultado = eliminar_duplicados(registros)
        assert len(resultado) == 2

    def test_lista_vacia(self):
        assert eliminar_duplicados([]) == []


# ===========================================================================
# SECCION 6: Pruebas de integracion — cruce de datos
# CONCEPTO ISTQB: Prueba de integracion — verificar contrato entre modulos
# ===========================================================================

class TestCruzarDatos:
    def setup_method(self):
        """Datos de prueba controlados para cada test."""
        self.csv_data = [
            {"tipo_id": "1", "num_id": "111"},   # coincide
            {"tipo_id": "1", "num_id": "222"},   # coincide
            {"tipo_id": "4", "num_id": "999"},   # solo en csv
        ]
        self.ods_data = [
            {"tipo_id": "1", "num_id": "111", "hoja": "1_CC"},  # coincide
            {"tipo_id": "1", "num_id": "222", "hoja": "1_CC"},  # coincide
            {"tipo_id": "4", "num_id": "888", "hoja": "4_TI"},  # solo en ods
        ]

    def test_coincidencias_correctas(self):
        resultado = cruzar_datos(self.csv_data, self.ods_data)
        assert len(resultado["coincidencias"]) == 2

    def test_solo_en_csv(self):
        resultado = cruzar_datos(self.csv_data, self.ods_data)
        assert len(resultado["solo_en_csv"]) == 1
        assert resultado["solo_en_csv"][0]["num_id"] == "999"

    def test_solo_en_ods(self):
        resultado = cruzar_datos(self.csv_data, self.ods_data)
        assert len(resultado["solo_en_ods"]) == 1
        assert resultado["solo_en_ods"][0]["num_id"] == "888"

    def test_resumen_por_tipo_contiene_tipo_1(self):
        resultado = cruzar_datos(self.csv_data, self.ods_data)
        assert "1" in resultado["resumen_por_tipo"]
        assert resultado["resumen_por_tipo"]["1"]["coincidencias"] == 2

    def test_cobertura_100_pct_cuando_todo_coincide(self):
        csv_data = [{"tipo_id": "1", "num_id": "111"}]
        ods_data = [{"tipo_id": "1", "num_id": "111", "hoja": "1_CC"}]
        resultado = cruzar_datos(csv_data, ods_data)
        assert resultado["resumen_por_tipo"]["1"]["cobertura_pct"] == 100.0

    def test_datos_vacios(self):
        resultado = cruzar_datos([], [])
        assert resultado["coincidencias"] == []
        assert resultado["solo_en_csv"] == []
        assert resultado["solo_en_ods"] == []


# ===========================================================================
# SECCION 7: Pruebas de estadisticas globales
# ===========================================================================

class TestCalcularEstadisticas:
    def test_estadisticas_basicas(self):
        resultado_cruce = {
            "coincidencias":  [{"tipo_id": "1", "num_id": "111", "descripcion": "", "hoja_ods": ""}],
            "solo_en_csv":    [{"tipo_id": "4", "num_id": "999", "descripcion": ""}],
            "solo_en_ods":    [],
            "resumen_por_tipo": {},
        }
        stats = calcular_estadisticas(resultado_cruce)
        assert stats["total_registros_csv"] == 2
        assert stats["coincidencias"] == 1
        assert stats["cobertura_csv_pct"] == 50.0

    def test_cobertura_completa(self):
        resultado_cruce = {
            "coincidencias":    [{"tipo_id": "1", "num_id": "111", "descripcion": "", "hoja_ods": ""}],
            "solo_en_csv":      [],
            "solo_en_ods":      [],
            "resumen_por_tipo": {},
        }
        stats = calcular_estadisticas(resultado_cruce)
        assert stats["cobertura_csv_pct"] == 100.0
