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

El repositorio incluye `scripts/download_data.py`, que descarga los archivos de
2026 publicados por la TLC (`--help` muestra las opciones disponibles). Los
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

<!-- TODO (Ejercicio 1.5) -->

Requisitos: **Git y Docker con Docker Compose**. Para conservar datos, instantáneas,
bases históricas e imágenes se recomienda disponer de al menos **20 GB libres**.
Desde la raíz del proyecto:

```bash
git clone https://github.com/Jorge162017/lab8-duckdb-ds.git
cd lab8-duckdb-ds
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

- [JupyterLab](http://localhost:8888/lab): notebooks y Python/DuckDB.
- [Metabase](http://localhost:3000): tablero de indicadores.

Las versiones están fijadas en [requirements.txt](requirements.txt) y los Dockerfiles.
Los datos se montan en `/workspace/data` dentro de los contenedores. Para diagnosticar
el inicio y detener servicios conservando los datos:

```bash
docker compose logs --tail=100 lab metabase
docker compose down
```

En este desarrollo se recomiendan 20 GB libres para datos, bases históricas,
instantánea final e imágenes. Evidencia: [ejercicios 1 y 2](docs/ejercicios_1_2.md).

## Como descargar los datos

<!-- TODO (Ejercicios 2.6, 5.1 y 8.1) -->

### Descarga inicial de 2026

```bash
docker compose exec -T lab python scripts/download_data.py --years 2026 --verify-availability
docker compose exec -T lab python scripts/validate_download.py
```

El descargador consulta los meses publicados y guarda archivos en
`data/raw/<tipo>/<año>/`. Usa reintentos y archivos temporales, verifica tamaño/firma
Parquet y genera un manifiesto. No confunde errores de conexión con meses ausentes;
los HTTP 403 ambiguos se contrastan con el catálogo oficial. `--workers` controla la
concurrencia (3 por defecto). La validación debe terminar con código 0 y
`completo_segun_publicacion: true`.

### Incorporación de 2024 y preparación del benchmark

```bash
docker compose exec -T lab python scripts/validate_incremental.py --snapshot-2026
docker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability --manifest data/processed/download_manifest_2024_2026_inicial.json
docker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability
docker compose exec -T lab python scripts/validate_download.py --manifest data/processed/download_manifest_2024_2026.json --require-full-years 2024
docker compose exec -T lab python scripts/validate_incremental.py
```

La segunda descarga comprueba la omisión de archivos existentes; el validador exige
los doce meses de 2024. Se contrastan conteos DuckDB con metadatos PyArrow y se
verifica preservación mediante SHA-256, tamaño y fecha de modificación.
Se genera [la preparación de tres volúmenes](docs/preparacion_benchmark.json).

### Incorporación de 2025 y conjunto final

```bash
docker compose exec -T lab python scripts/complete_three_years.py --snapshot
docker compose exec -T lab python scripts/download_data.py --years 2024 2025 2026 --verify-availability --manifest data/processed/download_manifest_2024_2025_2026_inicial.json
docker compose exec -T lab python scripts/download_data.py --years 2024 2025 2026 --verify-availability
docker compose exec -T lab python scripts/validate_download.py --manifest data/processed/download_manifest_2024_2025_2026.json --require-full-years 2024 2025
docker compose exec -T lab python scripts/complete_three_years.py
```

La instantánea final se guarda en `data/processed/analitica/` y su ruta actual queda
en [la configuración del tablero](docs/tablero/indicadores.json). Las bases y tiempos
del benchmark anterior se conservan. Se verifican consultas previas e indicadores
por año; la evolución compara enero–agosto y normaliza días calendario, incluido
el año bisiesto de 2024. Los importes son nominales y las medianas aproximadas.

El script base se amplió con `--years`, concurrencia controlada y manifiestos.
Los cambios y comprobaciones están documentados en los ejercicios
[1–2](docs/ejercicios_1_2.md), [5](docs/ejercicio_5_incorporacion_2024.md) y
[8](docs/ejercicio_8_tres_anios.md).

## Como ejecutar el analisis

<!-- TODO -->

Para ejecutar la exploración y el EDA:

```bash
docker compose exec -T lab python scripts/explore_parquet.py
docker compose exec -T lab python scripts/analyze_trips.py
```

Estos scripts leen **todos los años locales** y actualizan sus salidas. Los resultados
entregados de los ejercicios 3–6 conservan su alcance histórico. Para revisar
compatibilidad final y resultados por año sin sustituirlos, use
`complete_three_years.py`, cuyos resultados se guardan por separado.

Abra los notebooks del índice en JupyterLab. También puede ejecutarlos desde terminal;
por ejemplo, para la entrega final:

```bash
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 notebooks/08_tres_anios.ipynb
```

Los notebooks 6 y 8 cargan por defecto mediciones/resultados reales registrados;
`RUN_BENCHMARK` y `RUN_PIPELINE` permiten recalcular explícitamente. Los demás
necesitan los datos y validaciones de su etapa. Los scripts de los pasos anteriores
regeneran CSV, figuras y documentación; los notebooks conservan salidas ejecutadas.

## Como reproducir los benchmarks

<!-- TODO (Ejercicio 6) -->

```bash
docker compose exec -T lab python scripts/benchmark.py --repetitions 5 --warmups 1 --threads 4 --memory-limit 2GB --seed 42
```

Se materializan tres tablas, una por volumen. Las mismas cinco consultas se ejecutan
sobre Parquet y tablas DuckDB: **150 mediciones y 30 calentamientos**. Se comprueba
la equivalencia de resultados y se registran por separado construcción y almacenamiento.
El alcance mayor de las mediciones entregadas es **71.870.407 registros de 2024/2026**,
no el conjunto final de tres años.

Opciones para repetir consultas sobre las mismas bases o regenerar gráficos sin medir:

```bash
docker compose exec -T lab python scripts/benchmark.py --reuse-materialized
docker compose exec -T lab python scripts/benchmark.py --report-only
```

`--levels pequeno` limita una ejecución al volumen pequeño. Los tiempos individuales,
medianas, dispersión, entorno y planes se encuentran en
[resultados del ejercicio 6](docs/resultados_ejercicio_6/). Se midieron ejecuciones
recurrentes con calentamiento; no caché fría ni un benchmark contra Pandas.

## Como generar los resultados principales

<!-- TODO -->

El desarrollo es individual sobre [este fork](https://github.com/Jorge162017/lab8-duckdb-ds).
Los ejercicios 1–9 están completos: 64 archivos Parquet y 121.184.384 registros.
2024 y 2025 tienen doce meses por tipo; 2026 contiene enero–agosto en la ejecución
documentada. Las preguntas y respuestas están en los documentos enlazados al final.

Para reproducir las etapas históricas y la preservación, el orden es: 2026 → 2024 →
benchmark de 2024/2026 → 2025 → instantánea final → indicadores y tablero.
No ejecute el cálculo de indicadores ni el notebook 7 antes de construir la instantánea
final: la configuración actual del tablero contiene los tres años.

### Indicadores y tablero final

```bash
docker compose exec -T lab python scripts/build_indicators.py
```

Abra Metabase y configure su propia cuenta. En el paso opcional de conexión, continúe
con los datos de muestra; el instalador conecta después nuestra base DuckDB.
Inicie sesión desde Terminal y cree/actualice el tablero:

```bash
docker compose exec lab python scripts/metabase_dashboard.py --login --url http://metabase:3000
docker compose exec -T lab python scripts/metabase_dashboard.py --url http://metabase:3000 --public-url http://localhost:3000
```

El inicio de sesión es interactivo. La contraseña no se muestra ni se guarda;
el token se conserva localmente, excluido de Git y con permisos 600. La base se conecta
en **read_only**, con temporales separados por proceso/instantánea. El instalador
imprime el enlace del tablero; en la ejecución entregada es
[http://localhost:3000/dashboard/2](http://localhost:3000/dashboard/2).
Los IDs pueden cambiar en otra instalación.

Los filtros seleccionan año y tipo (`yellow`/`green`, tipo vacío para ambos).
Las tres tarjetas comparativas consideran siempre los tres años en meses comunes:
ignoran el filtro de año y aceptan el de tipo. La configuración final requiere la
instantánea del paso 4 antes de ejecutar el cálculo de indicadores o el notebook 7.

Si utiliza Python con Requests en el host, puede ejecutar el instalador sin Docker,
con localhost por defecto. La sesión debe corresponder a la misma URL utilizada
al iniciar sesión.

### Discusión y resultados principales

La [discusión final](docs/ejercicio_9_discusion.md) responde las ocho preguntas del
ejercicio 9 con evidencia real. Los resultados y sus límites están en los documentos
de cada etapa; el benchmark de 2024/2026 se distingue del análisis final de tres años.

El tablero final tiene 16 tarjetas. Las tres comparativas usan meses comunes e ignoran
el filtro de año, pero aceptan tipo de taxi. Su evidencia está en las capturas del
ejercicio 8. Los datos, bases, sesiones, temporales e instrucciones son locales y
se excluyen de Git; se entregan código, SQL, notebooks y resultados resumidos.

Si la TLC publica nuevos archivos o corrige datos, la reproducción puede producir
otras cifras; los manifiestos describen el alcance real de cada ejecución.



## Índice complementario de la documentación

Comience por el documento de cada ejercicio. Los notebooks conservan SQL y salidas
ejecutadas; los CSV/JSON son evidencia detallada. El [índice de documentación](docs/README.md)
explica dónde están los resultados, gráficos y validaciones.

| Ejercicio | Documento principal | Notebook | Consultas SQL |
| --- | --- | --- | --- |
| 1–2 · Ambiente y descarga | [Preparación y validación](docs/ejercicios_1_2.md) | — | — |
| 3 · Exploración de Parquet | [Estructura, tipos y calidad](docs/ejercicio_3_exploracion.md) | [03](notebooks/03_exploracion_parquet.ipynb) | [Exploración](sql/exploracion/) |
| 4 · Análisis exploratorio | [Preguntas, gráficos y hallazgos](docs/ejercicio_4_analisis.md) | [04](notebooks/04_analisis_exploratorio.ipynb) | [EDA](sql/eda/) |
| 5 · Incorporación de 2024 | [Preservación y compatibilidad](docs/ejercicio_5_incorporacion_2024.md) | [05](notebooks/05_incorporacion_2024.ipynb) | [Incorporación](sql/incremental/) |
| 6 · Benchmark | [Método, tiempos y discusión](docs/ejercicio_6_benchmark.md) | [06](notebooks/06_benchmark_parquet_duckdb.ipynb) | [Benchmark](sql/benchmark/) |
| 7 · Indicadores y tablero | [Preguntas e interpretaciones](docs/ejercicio_7_indicadores.md) | [07](notebooks/07_indicadores_metabase.ipynb) | [Indicadores](sql/indicadores/) |
| 8 · Tres años | [Evolución, patrones y tablero actualizado](docs/ejercicio_8_tres_anios.md) | [08](notebooks/08_tres_anios.ipynb) | [Evolución](sql/evolucion/) |
| 9 · Discusión | [Las ocho respuestas finales](docs/ejercicio_9_discusion.md) | — | — |

**Evidencia final del tablero:** [vista de 2026](docs/figuras_ejercicio_8/tablero_tres_anios.png)
y [selección de 2025](docs/figuras_ejercicio_8/tablero_2025.png).
El tablero tiene **16 tarjetas**: trece indicadores iniciales y tres comparaciones
de demanda, efectivo y costo mediano en meses comunes.
