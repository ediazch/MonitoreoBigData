# Graph Report - MonitoreoBigData  (2026-09-18)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 89 nodes · 143 edges · 10 communities (9 shown, 1 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- limpiar_id
- test_limpieza.py
- cruzar_datos
- limpieza.py
- main
- normalizar_filas_ods
- normalizar_filas_csv
- eliminar_duplicados
- limpiar_tipo

## God Nodes (most connected - your core abstractions)
1. `limpiar_id()` - 12 edges
2. `cruzar_datos()` - 11 edges
3. `main()` - 11 edges
4. `normalizar_filas_ods()` - 10 edges
5. `normalizar_filas_csv()` - 10 edges
6. `TestLimpiarId` - 8 edges
7. `TestCruzarDatos` - 8 edges
8. `limpiar_tipo()` - 8 edges
9. `calcular_estadisticas()` - 7 edges
10. `eliminar_duplicados()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `calcular_estadisticas()`  [INFERRED]
  analisis_relacion.py → src/transformacion.py
- `main()` --calls--> `cruzar_datos()`  [INFERRED]
  analisis_relacion.py → src/transformacion.py
- `main()` --calls--> `leer_ods()`  [INFERRED]
  analisis_relacion.py → src/limpieza.py
- `main()` --calls--> `eliminar_duplicados()`  [INFERRED]
  analisis_relacion.py → src/limpieza.py
- `main()` --calls--> `normalizar_filas_csv()`  [INFERRED]
  analisis_relacion.py → src/limpieza.py

## Import Cycles
- None detected.

## Communities (10 total, 1 thin omitted)

### Community 0 - "limpiar_id"
Cohesion: 0.19
Nodes (8): limpiar_id(), Normaliza un numero de identificacion: - Elimina espacios, comillas…, ID sin ruido debe retornarse igual., IDs exportados de Excel suelen venir con comilla al inicio., Espacios en blanco deben eliminarse., IDs con guion (e.g. pasaportes) deben unificarse., ID vacio retorna string vacio., TestLimpiarId

### Community 1 - "test_limpieza.py"
Cohesion: 0.18
Nodes (10): os, pytest, calcular_estadisticas(), Any, transformacion.py ----------------- Funciones de analisis y cruce de datos…, Calcula metricas globales del cruce de datos. Returns: Dict con conteos y…, sys, test_limpieza.py ---------------- Pruebas unitarias para src/limpieza.py y… (+2 more)

### Community 2 - "cruzar_datos"
Cohesion: 0.27
Nodes (4): cruzar_datos(), Cruza los registros del CSV contra los del ODS usando tipo_id + num_id. Args:…, Datos de prueba controlados para cada test., TestCruzarDatos

### Community 3 - "limpieza.py"
Cohesion: 0.22
Nodes (9): csv, _extraer_texto_celda(), leer_ods(), Any, limpieza.py ----------- Funciones de limpieza y lectura de datos para el…, Lee un archivo ODS (OpenDocument Spreadsheet) sin dependencias externas.…, Extrae el texto visible de una celda ODS., xml_etree_elementtree (+1 more)

### Community 4 - "main"
Cohesion: 0.31
Nodes (8): imprimir_tabla(), main(), analisis_relacion.py -------------------- Script principal: cruza los datos del…, Imprime lista de dicts como tabla en consola., seccion(), titulo(), leer_csv(), Lee un archivo CSV y retorna lista de filas. Filtra filas vacias…

### Community 5 - "normalizar_filas_ods"
Cohesion: 0.31
Nodes (5): normalizar_filas_ods(), Extrae y normaliza los registros de todas las hojas del ODS. Descarta filas de…, Filas donde tipo_id es texto (ej: 'tipoID') deben descartarse., Registros con num_id no numerico deben descartarse., TestNormalizarFilasODS

### Community 6 - "normalizar_filas_csv"
Cohesion: 0.36
Nodes (4): normalizar_filas_csv(), Convierte las filas crudas del CSV en lista de dicts normalizados. Estructura…, Filas con menos de 2 columnas deben ignorarse., TestNormalizarFilasCSV

### Community 7 - "eliminar_duplicados"
Cohesion: 0.47
Nodes (3): eliminar_duplicados(), Elimina registros duplicados por clave compuesta. Args: registros: Lista de…, TestEliminarDuplicados

### Community 8 - "limpiar_tipo"
Cohesion: 0.47
Nodes (3): limpiar_tipo(), Normaliza el tipo de documento a string entero sin espacios., TestLimpiarTipo

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `limpiar_id()` connect `limpiar_id` to `test_limpieza.py`, `limpieza.py`, `normalizar_filas_ods`, `normalizar_filas_csv`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Why does `normalizar_filas_ods()` connect `normalizar_filas_ods` to `limpiar_id`, `test_limpieza.py`, `limpieza.py`, `main`, `limpiar_tipo`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Why does `main()` connect `main` to `test_limpieza.py`, `cruzar_datos`, `limpieza.py`, `normalizar_filas_ods`, `normalizar_filas_csv`, `eliminar_duplicados`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `main()` (e.g. with `eliminar_duplicados()` and `leer_csv()`) actually correct?**
  _`main()` has 7 INFERRED edges - model-reasoned connections that need verification._