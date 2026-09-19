# MonitoreoBigData

Proyecto base de análisis y monitoreo de datos con arquitectura híbrida de skills de IA.
Desarrollado con Python 3.11+, incluye análisis de datos reales, memoria persistente automática,
escaneo de seguridad y workflow de desarrollo profesional.

---

## Estructura del proyecto

```
MonitoreoBigData/
│
├── data/
│   ├── raw/                          <- datos originales sin modificar
│   └── processed/                    <- datos limpios y transformados
│
├── notebooks/
│   └── 01_exploracion_inicial.ipynb  <- análisis exploratorio (EDA)
│
├── src/
│   ├── __init__.py
│   ├── limpieza.py                   <- funciones de limpieza y lectura de datos
│   └── transformacion.py             <- cruce y análisis de datos
│
├── config/
│   └── configuracion.yaml            <- parámetros centralizados del proyecto
│
├── tests/
│   └── test_limpieza.py              <- 29 pruebas unitarias (pytest)
│
├── memory/                           <- aura-mem: memoria persistente automática
│   ├── aura_mem.py                   <- motor principal SQLite
│   ├── session_log.py                <- gestión de sesiones
│   ├── mem_search.py                 <- búsqueda full-text FTS5
│   ├── compresor.py                  <- compresión local con Sumy LSA
│   └── watcher.py                   <- file watcher automático
│
├── skills/                           <- adaptaciones Python de skills para Aura
│   ├── task_observer.py             <- observación y mejora de patrones
│   ├── impeccable.py                <- diseño profesional de interfaces
│   ├── superpowers.py               <- workflow de desarrollo (plan/tdd/review)
│   ├── headroom.py                  <- compresión de tokens (50-93%)
│   ├── security.py                  <- scanner de vulnerabilidades OWASP
│   └── ralph.py                     <- loop iterativo hasta criterio
│
├── .claude/skills/                   <- skills para Claude Code CLI
├── .agents/skills/                   <- skills para otros agentes (Cursor, Codex, etc.)
├── graphify-out/                     <- grafo de conocimiento del proyecto
├── security-reports/                 <- reportes de seguridad generados
├── .vscode/tasks.json               <- auto-inicio del watcher al abrir VS Code
├── .gitignore
├── analisis_relacion.py             <- script principal de análisis ODS vs CSV
├── dashboard.html                   <- dashboard visual de resultados
├── PRODUCT.md                       <- contexto de producto (impeccable)
└── requirements.txt                 <- dependencias del proyecto
```

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/ediazch/MonitoreoBigData.git
cd MonitoreoBigData

# Instalar dependencias
pip install -r requirements.txt

# Descargar recursos NLTK (compresión de memoria)
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"
```

---

## Análisis de datos — ODS vs CSV

El proyecto cruza dos archivos de datos de identidad:

- `Data_Income_estimator_V1.ods` — estimador de ingresos con 10 hojas por tipo de documento
- `Data_pruebas_Income(Adviser)QA 1.csv` — casos de prueba QA del sistema Adviser

**Relación clave:**
```
CSV.columna_0 (tipo_id)  <-->  prefijo numérico del nombre de hoja ODS
CSV.columna_1 (num_id)   <-->  ODS.columna_1 (num_id en cada hoja)
```

**Resultados del análisis:**

| Métrica | Valor |
|---|---|
| Total registros CSV | 666 |
| Total registros ODS | 697 |
| Coincidencias | 662 (99.4%) |
| Solo en CSV | 4 |
| Solo en ODS | 35 |
| Tipo crítico (PPT-13) | 50% cobertura |

```bash
# Ejecutar análisis completo
python analisis_relacion.py
```

---

## Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con cobertura
python -m pytest tests/ -v --cov=src
```

29 pruebas unitarias que cubren:
- Limpieza y normalización de IDs
- Normalización de filas CSV y ODS
- Eliminación de duplicados
- Cruce de datos y estadísticas
- Cobertura por tipo de documento

---

## Skills — Arquitectura híbrida

El proyecto implementa un sistema híbrido de skills que funciona tanto con agentes IA (Claude Code, Cursor, Codex) como directamente desde Python.

### Automáticos — sin intervención manual

| Evento | Acción automática |
|---|---|
| Abrir VS Code | Inicia sesión + file watcher + patrones |
| Modificar `.py` | aura-mem registra el cambio |
| Modificar `.html` | impeccable audita automáticamente |
| `git commit` | Registra en memoria + actualiza graphify |
| `git checkout` | Registra cambio de rama |
| 30 min inactivo | Cierra sesión + comprime memoria |

### Manuales — comandos disponibles

#### aura-mem — Memoria persistente
```bash
# Ver resumen de memoria
python memory/aura_mem.py resumen

# Guardar observación
python memory/aura_mem.py log "mensaje" --tipo [fase|resultado|decision|bugfix|error|instalacion|nota]

# Buscar en memoria
python memory/mem_search.py "query"
python memory/mem_search.py --recientes

# Sesiones
python memory/session_log.py start
python memory/session_log.py end
python memory/session_log.py historial

# Comprimir memoria
python memory/compresor.py --auto
python memory/compresor.py --stats
```

#### graphify — Grafo de conocimiento
```bash
python -m graphify query "como funciona el cruce de datos"
python -m graphify path "leer_csv" "cruzar_datos"
python -m graphify explain "normalizar_filas_ods"
python -m graphify update . --code-only
```

#### superpowers — Workflow de desarrollo
```bash
python skills/superpowers.py brainstorm "nueva feature"
python skills/superpowers.py plan "nueva feature"
python skills/superpowers.py tdd "modulo"
python skills/superpowers.py review src/archivo.py
python skills/superpowers.py status
```

#### security — Scanner de vulnerabilidades
```bash
python skills/security.py threats          # modelo de amenazas
python skills/security.py scan             # escanear todo
python skills/security.py scan src/limpieza.py
python skills/security.py scan-cambios     # solo archivos modificados
python skills/security.py reporte          # ver último reporte
```

#### headroom — Compresión de tokens
```bash
python skills/headroom.py demo
python skills/headroom.py comprimir-archivo src/limpieza.py
python skills/headroom.py comprimir-json graphify-out/graph.json
python skills/headroom.py stats
```

#### ralph — Loop iterativo
```bash
python skills/ralph.py run-tests --max 10
python skills/ralph.py run "python analisis_relacion.py" --until "662" --max 5
python skills/ralph.py status
python skills/ralph.py cancelar
```

#### impeccable — Diseño profesional
```bash
python skills/impeccable.py init
python skills/impeccable.py generar dashboard
python skills/impeccable.py audit dashboard.html
python skills/impeccable.py critique "descripcion del diseño"
python skills/impeccable.py polish dashboard.html
python skills/impeccable.py anti-patrones
```

#### task-observer — Mejora continua
```bash
python skills/task_observer.py observar "algo que notaste"
python skills/task_observer.py sugerir
python skills/task_observer.py patrones
python skills/task_observer.py revisar
```

---

## Skills instalados para agentes externos

| Skill | Agente | Repositorio |
|---|---|---|
| graphify | Claude Code, Cursor | graphify-labs/graphify |
| superpowers (14 skills) | Claude Code, Codex | obra/superpowers |
| impeccable | Claude Code | pbakaus/impeccable |
| task-observer | Claude Code | rebelytics/one-skill-to-rule-them-all |
| find-skills | Todos | vercel-labs/skills |
| claude-security | Claude Code | anthropics/claude-plugins-official |
| ralph-wiggum | Claude Code | anthropics/claude-code |
| OmniRoute (30+ skills) | Todos | diegosouzapw/OmniRoute |

---

## Seguridad

- Rutas de datos leídas desde `config/configuracion.yaml` o variables de entorno
- IDs de ciudadanos enmascarados en consola (`106****185`)
- Scanner OWASP activo con 13 reglas
- 0 vulnerabilidades detectadas en el código actual
- Datos sensibles nunca se commitean (`.gitignore`)

Variables de entorno opcionales:
```bash
MONITOREO_RUTA_ODS=<ruta al archivo ODS>
MONITOREO_RUTA_CSV=<ruta al archivo CSV>
```

---

## Dependencias principales

```
pandas==2.2.2       # análisis de datos
numpy==1.26.4       # operaciones numéricas
PyYAML==6.0.1       # configuración
matplotlib==3.9.0   # visualización
seaborn==0.13.2     # visualización estadística
jupyter==1.0.0      # notebooks
pytest==8.2.2       # testing
watchdog==6.0.0     # file watcher automático
sumy==0.13.0        # compresión local de memoria
nltk==3.10.3        # procesamiento de texto
headroom-ai==0.37.0 # compresión de tokens
```

---

## Plan de trabajo — Fases

| Fase | Estado | Descripción |
|---|---|---|
| 1. Skeleton | Completada | Estructura base del proyecto |
| 2. Datos | Completada | Dataset y análisis ODS vs CSV |
| 3. Limpieza | Completada | `src/limpieza.py` con funciones de limpieza |
| 4. Transformación | Completada | `src/transformacion.py` con cruce de datos |
| 5. EDA | Pendiente | Notebook de exploración inicial |
| 6. Testing | Completada | 29 pruebas unitarias pytest |
| 7. Configuración | Completada | `config/configuracion.yaml` centralizado |

---

## Activar tareas automáticas en VS Code

Para que el watcher inicie automáticamente al abrir el proyecto:

1. `Ctrl+Shift+P`
2. Escribir: `Tasks: Manage Automatic Tasks`
3. Seleccionar: `Allow Automatic Tasks`

---

## Autor

Proyecto de aprendizaje de Big Data y análisis de datos.
Arquitectura híbrida con skills de IA para desarrollo profesional.
