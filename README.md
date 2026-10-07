# Lab 8 - DuckDB

Repositorio base del laboratorio 8 del curso **CC3084 - Data Science**
(Universidad del Valle de Guatemala, Ciclo 2, 2026).

Este es el repositorio **proporcionado por el docente**. Contiene la estructura
del proyecto, el ambiente de ejecucion basado en Docker y un script que descarga
los datos de **2026**. Todo lo demas debe ser construido por cada equipo.

## Trabajo con fork

El laboratorio se desarrolla y se entrega sobre un **fork** de este repositorio.
No se trabaja directamente sobre el repositorio del docente.

1. Realice un fork de este repositorio:
   <https://github.com/menene/duckdb>

2. Clone **su propio fork** (no el del docente):

   ```bash
   git clone https://github.com/<su-usuario>/duckdb.git
   cd duckdb
   ```

3. Opcional, para recibir correcciones publicadas por el docente:

   ```bash
   git remote add upstream https://github.com/menene/duckdb.git
   git fetch upstream
   ```

Realice commits frecuentes y descriptivos: el historial del repositorio es parte
de la evaluacion. **La entrega del laboratorio es la URL de su fork.**

## Estructura

```text
duckdb/
|
+-- data/
|   +-- raw/
|   +-- processed/
|
+-- notebooks/
|
+-- scripts/
|
+-- sql/
|
+-- docs/
|
+-- Dockerfile
+-- metabase.Dockerfile
+-- docker-compose.yml
+-- README.md
```

## Requisitos

- Docker, con Docker Compose
- Git

La primera construccion del ambiente descarga varios cientos de MB y puede
tardar algunos minutos.

Considere el espacio en disco: las imagenes de Docker ocupan unos 3 GB y los
datos de los tres anios del laboratorio superan 1.5 GB, a los que se suma la
base materializada del Ejercicio 6. Se recomienda tener al menos 10 GB libres.

## Datos

El repositorio incluye `scripts/download_data.py`, que descarga los años indicados
con `--years` (2026 por defecto; `--help` muestra las opciones disponibles). Los
archivos se guardan en `data/raw/<tipo>/<anio>/`.

La TLC publica cada mes con varias semanas de atraso, por lo que los ultimos
meses de 2026 todavia no existen. El script consulta al servidor que meses estan
publicados, de modo que vuelve a ejecutarse sin problema conforme aparezcan
nuevos archivos.

Los datos descargados **no deben incluirse en el repositorio Git**. El archivo
`.gitignore` ya esta configurado para evitarlo.

Fuente de datos: NYC TLC Trip Record Data
<https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>

Dentro de los contenedores, la carpeta `data/` del proyecto esta montada en
`/workspace/data`. Esa es la ruta que deben usar las herramientas que corren
dentro del ambiente, no la ruta de su computadora.

> **Nota sobre DuckDB:** un archivo `.duckdb` admite un solo proceso con permiso
> de escritura a la vez. Si conecta una herramienta externa a su base de datos,
> use el modo de solo lectura (`read_only`) en esa conexion; de lo contrario los
> demas procesos no podran abrir el archivo.

## Material a entregar

Al finalizar, su fork debe contener:

- el codigo fuente modificado y los scripts de descarga;
- las consultas SQL desarrolladas;
- el notebook o notebooks utilizados;
- la documentacion de las consultas;
- los scripts utilizados para los benchmarks;
- el codigo de los indicadores y visualizaciones;
- el tablero o la evidencia del tablero desarrollado;
- este `README.md`, completado segun la siguiente seccion.

Los archivos de datos descargados **no** deben incluirse.

---

# Documentacion del equipo

Las siguientes secciones deben ser completadas por cada equipo. El README final
debe permitir que una persona que no participo en el desarrollo pueda levantar el
ambiente, descargar los datos, ejecutar el analisis, reproducir los benchmarks y
generar los resultados principales.

## Como levantar el ambiente

Trabajo individual sobre el fork: <https://github.com/Jorge162017/lab8-duckdb-ds>.

Ambiente verificado: JupyterLab y Metabase responden con HTTP 200, y Metabase
registra el driver DuckDB. La evidencia está en `docs/ejercicios_1_2.md`.

Requisitos: Git, Docker Desktop (motor encendido) y Docker Compose. Se recomiendan
al menos 10 GB libres. Desde la raíz del repositorio:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Abra JupyterLab en <http://localhost:8888> y Metabase en
<http://localhost:3000>. Complete la configuración inicial de Metabase al abrirlo
por primera vez. Para verificar las respuestas HTTP y las herramientas:

```bash
curl -f http://localhost:8888/api/status
curl -f http://localhost:3000/api/health
docker compose exec -T lab python -c "import duckdb, pandas, pyarrow; print(duckdb.__version__, pandas.__version__, pyarrow.__version__)"
```

El servicio `lab` incluye Python, JupyterLab, DuckDB, Pandas, PyArrow, Matplotlib
y Requests. Metabase incluye Java y el driver de DuckDB. Las versiones están
fijadas en los Dockerfiles y `requirements.txt`.

Dentro de los contenedores, los datos están en `/workspace/data`. Los puertos
están publicados solamente en la interfaz local. Para revisar fallos:

```bash
docker compose logs --tail=100 lab metabase
```

Para detener el ambiente conservando los datos y la configuración de Metabase:

```bash
docker compose down
```

Un ambiente reproducible fija las dependencias y las rutas de ejecución; permite
que otra persona repita el análisis con las mismas herramientas y reduce
las diferencias entre computadoras. Véase [la documentación de los ejercicios 1 y 2](docs/ejercicios_1_2.md).

## Como descargar los datos

La etapa inicial trabaja con taxis amarillos y verdes de 2026:

```bash
docker compose exec -T lab python scripts/download_data.py --verify-availability
docker compose exec -T lab python scripts/validate_download.py
```

Los archivos se guardan en `data/raw/<tipo>/2026/`. El descargador consulta los
12 meses por tipo: un HTTP 404 se registra como no publicado. Un HTTP 403 solo se considera
no publicado si el enlace está ausente del catálogo oficial de la TLC; si el
catálogo no puede consultarse o el archivo sí está listado, se registra un fallo.
Los errores de conexión y otros errores HTTP también se registran como fallos. No supone que ya estén
publicados los doce meses de 2026.

Los archivos locales no vacíos se omiten. `--verify-availability` comprueba además
su publicación sin descargarlos otra vez. Las descargas nuevas verifican tamaño
HTTP (si está disponible) y firmas Parquet, y usan un archivo temporal `.part`.
El reporte de cada ejecución queda en
`data/processed/download_manifest_2026.json`. La validación lee los metadatos
Parquet y genera `docs/validacion_descarga_2026.json`; ambos comandos deben terminar
con código 0. El reporte de validación debe indicar
`completo_segun_publicacion: true`.

Para comprobar que una segunda ejecución conserva los archivos descargados:

```bash
docker compose exec -T lab python scripts/download_data.py --verify-availability
docker compose exec -T lab python scripts/validate_download.py
```

La segunda descarga debe reportar cero archivos descargados si no se publicaron
archivos adicionales entre las ejecuciones. No se incluyen en Git ni los datos
ni la carpeta local `instrucciones/`. La incorporación de 2024 está completada en el ejercicio 5; 2025 se añadirá
más adelante en el ejercicio 8.

### Incorporar 2024 (ejercicio 5)

Con ambos tipos de taxi de 2026 ya descargados, guarde las huellas antes de ampliar:

```bash
docker compose exec -T lab python scripts/validate_incremental.py --snapshot-2026
docker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability --manifest data/processed/download_manifest_2024_2026_inicial.json
```

Repita la descarga y valide el conjunto ampliado:

```bash
docker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability
docker compose exec -T lab python scripts/validate_download.py --manifest data/processed/download_manifest_2024_2026.json --require-full-years 2024
docker compose exec -T lab python scripts/validate_incremental.py
```

La segunda ejecución debe omitir los archivos existentes; `--require-full-years`
exige los doce meses de 2024 por tipo. El snapshot permite comprobar que los
Parquet anteriores de 2026 no cambiaron en SHA-256, tamaño o fecha de modificación.
No se reemplaza si ya existe. `--workers` controla las descargas simultáneas
(3 por defecto, entre 1 y 8). Cada combinación de años tiene su propio manifiesto.

Resultado verificado: 24 archivos nuevos de 2024 y 16 conservados de 2026;
40 Parquet con 71.870.407 registros. Las fuentes, esquemas, continuidad SQL y
preservación están documentados en `docs/ejercicio_5_incorporacion_2024.md`.
Los datos, manifiestos y snapshot siguen excluidos de Git.

## Como ejecutar el analisis

El ejercicio 3 consulta los Parquet directamente, sin materializar viajes:

```bash
docker compose exec -T lab python scripts/explore_parquet.py
```

También puede abrir `notebooks/03_exploracion_parquet.ipynb` en JupyterLab y
seleccionar **Run → Run All Cells**. Para ejecutarlo desde terminal y guardar
las salidas:

```bash
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/03_exploracion_parquet.ipynb
```

Los dos métodos usan las mismas consultas de `sql/exploracion/`. Producen
`docs/ejercicio_3_exploracion.md` y los CSV de `docs/resultados_ejercicio_3/`.
Estos CSV contienen resultados pequeños, muestras y metadatos, no los archivos
de datos completos. La documentación registra fuentes, objetivos, resultados,
decisiones y alertas de calidad. Las vistas armonizan nombres de fechas y usan
`union_by_name` para conservar columnas que cambian entre meses; no limpian los
valores originales.

Para el ejercicio 4, ejecute el análisis exploratorio y genere sus gráficos:

```bash
docker compose exec -T lab python scripts/analyze_trips.py
```

También puede abrir `notebooks/04_analisis_exploratorio.ipynb` y ejecutar todas
sus celdas. Para guardar las salidas desde terminal:

```bash
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/04_analisis_exploratorio.ipynb
```

Los SQL están en `sql/eda/`; los resultados en `docs/resultados_ejercicio_4/`;
los gráficos en `docs/figuras_ejercicio_4/`; y las preguntas, criterios de calidad,
interpretaciones y hallazgos en `docs/ejercicio_4_analisis.md`. Las comparaciones
especifican su población: fechas válidas para demanda/pagos y filtros adicionales
de medición para características/costos. No se modifican los Parquet ni se
excluyen viajes por pasajeros o pagos ausentes. Se incluye sensibilidad a los filtros.

Para revisar el ejercicio 5 abra `notebooks/05_incorporacion_2024.ipynb` y ejecute
todas sus celdas después de completar la descarga y validación anteriores.
También puede guardar sus salidas desde terminal:

```bash
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/05_incorporacion_2024.ipynb
```

Las seis consultas nuevas están en `sql/incremental/`. Los resultados conjuntos y
la ejecución de las 21 consultas anteriores están en `docs/resultados_ejercicio_5/`;
los resultados históricos de 2026 de los ejercicios 3 y 4 se conservan.
Las vistas ahora declaran campos opcionales con una rama vacía tipada para permitir
también lecturas aisladas de 2024. Los CSV y documentación de compatibilidad usan
ambos años; para comparaciones anuales se debe agrupar o filtrar por año y usar
cobertura común. `docs/preparacion_benchmark.json` identifica tres volúmenes de
datos para el ejercicio 6; todavía no contiene mediciones de rendimiento.

El ejercicio 6 está completado; su benchmark se reproduce con los comandos de
la sección siguiente. Los ejercicios 7 a 9 se desarrollarán después.

## Como reproducir los benchmarks

Con el ejercicio 5 completo y su manifiesto de tres volúmenes preparado:

```bash
docker compose exec -T lab python scripts/benchmark.py --repetitions 5 --warmups 1 --threads 4 --memory-limit 2GB --seed 42
```

Se construye una tabla `viajes_duckdb` por conjunto en
`data/processed/benchmark/{pequeno,mediano,completo}.duckdb`. Las bases y sus
metadatos locales están excluidos de Git. El benchmark no cambia los Parquet.
La fuente y la tabla tienen los mismos campos/filas; solo cambia el nombre de
relación en las cinco consultas de `sql/benchmark/`. Se comprueban resultados
en cada ejecución, usando igualdad exacta para conteos/categorías y tolerancias
para medias flotantes. Se registran 150 mediciones y 30 calentamientos.

Cada ejecución normal reconstruye las bases derivadas y mide el costo de
construcción por separado. Para repetir consultas sobre las bases ya construidas:

```bash
docker compose exec -T lab python scripts/benchmark.py --reuse-materialized
```

La reutilización verifica los archivos y la definición de la fuente. Los costos
de construcción conservados pertenecen a la ejecución original. Para ejecutar
solo el conjunto pequeño puede añadir `--levels pequeno`. Para regenerar
únicamente gráficos y documentación desde los tiempos registrados:

```bash
docker compose exec -T lab python scripts/benchmark.py --report-only
```

El protocolo mide ejecuciones recurrentes: calentamiento previo, consultas
intercaladas y estrategias alternadas, sin vaciar cachés del sistema operativo.
Los tiempos incluyen SQL y transferencia del resultado pequeño; no incluyen
verificación, CSV, EXPLAIN ni materialización. El entorno, límites y tolerancias
quedan registrados en `docs/resultados_ejercicio_6/entorno.json`.

Revise `docs/ejercicio_6_benchmark.md`, los tiempos crudos, resumen, comparación,
costos de materialización y equivalencia de `docs/resultados_ejercicio_6/`.
Los planes y resultados por estrategia se guardan en subdirectorios de esa
carpeta; los gráficos están en `docs/figuras_ejercicio_6/`.

El notebook `notebooks/06_benchmark_parquet_duckdb.ipynb` carga los tiempos reales
registrados sin volver a medir por defecto. Cambie `RUN_BENCHMARK` a `True` para
reproducir desde sus celdas, o utilice el script anterior. Para guardar el notebook
con sus tablas y gráficos:

```bash
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/06_benchmark_parquet_duckdb.ipynb
```

La base completa está lista para la conexión del tablero posterior: dentro de
los contenedores, `/workspace/data/processed/benchmark/completo.duckdb`, tabla
`viajes_duckdb`, en modo de solo lectura. Contiene 2024 y 2026 como instantánea;
se deberá actualizar al incorporar 2025.

## Como generar los resultados principales

Con el ambiente encendido y los datos descargados:

```bash
docker compose exec -T lab python scripts/validate_download.py
docker compose exec -T lab python scripts/explore_parquet.py
docker compose exec -T lab python scripts/analyze_trips.py
```

Esto reproduce la validación, la exploración y el EDA de los ejercicios 2 a 4.
Los scripts de exploración/EDA leen **todos los años locales**: después del
ejercicio 5, ejecutarlos actualiza sus salidas con 2024 y 2026. Para comprobar
compatibilidad sin sobrescribir los resultados históricos de 2026 utilice:

```bash
docker compose exec -T lab python scripts/validate_incremental.py
```
Los notebooks conservan sus resultados ejecutados. Los scripts actualizan los
CSV, las figuras y la documentación con el conjunto de archivos disponible.
Los percentiles aproximados pueden variar ligeramente entre ejecuciones;
los conteos y las definiciones de poblaciones son exactos.
