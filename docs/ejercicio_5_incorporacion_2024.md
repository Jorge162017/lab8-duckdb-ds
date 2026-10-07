# Ejercicio 5: incorporación incremental de 2024

Generado el 2026-10-07T16:48:43.893542+00:00 (UTC). Trabajo individual.

## Resultado y alcance (5.1–5.5)

El descargador acepta `--years`, conserva 2026 como valor por defecto y admite ejecución incremental por año y tipo. La estructura sigue siendo `data/raw/<tipo>/<año>/`. Los años repetidos se deduplican y `--workers` limita las descargas simultáneas (3 por defecto). Se conservan los reintentos, archivos temporales, comprobación de firmas y tamaño, catálogo para 403 ambiguos y manifiestos por ejecución.

La validación ahora deriva los candidatos del alcance declarado en el manifiesto. `--require-full-years 2024` exige los doce meses de ambos tipos; 2026 se valida según los archivos publicados. Los manifiestos anteriores de 2026 siguen siendo compatibles.

### Reproducción

Antes de incorporar 2024, con 2026 ya descargado:

```bash
docker compose exec -T lab python scripts/validate_incremental.py --snapshot-2026
docker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability --manifest data/processed/download_manifest_2024_2026_inicial.json
docker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability
docker compose exec -T lab python scripts/validate_download.py --manifest data/processed/download_manifest_2024_2026.json --require-full-years 2024
docker compose exec -T lab python scripts/validate_incremental.py
```

El snapshot es local y debe crearse antes de la ampliación para comprobar preservación. Si ya existe, se conserva; no se reemplaza por una huella posterior. Una segunda descarga solo omitirá todos los archivos si no se publicaron meses nuevos entre las ejecuciones.

### Evidencia de descarga y preservación

Resumen de la ejecución inicial: {"descargados": 24, "omitidos": 16, "no_publicados": ["yellow 2026-09", "yellow 2026-10", "yellow 2026-11", "yellow 2026-12", "green 2026-09", "green 2026-10", "green 2026-11", "green 2026-12"], "fallidos": []}

Resumen de la segunda ejecución: {"descargados": 0, "omitidos": 40, "no_publicados": ["yellow 2026-09", "yellow 2026-10", "yellow 2026-11", "yellow 2026-12", "green 2026-09", "green 2026-10", "green 2026-11", "green 2026-12"], "fallidos": []}

Se comprobaron **16 archivos originales de 2026 sin cambios** en bytes, fecha de modificación y SHA-256. La evidencia está en [preservacion_2026_ejercicio_5.json](preservacion_2026_ejercicio_5.json). El manifiesto inicial y el snapshot permanecen en `data/processed/`, excluidos de Git.

La lectura de metadatos PyArrow y los conteos DuckDB coinciden por archivo. Véase [validacion_descarga_2024_2026.json](validacion_descarga_2024_2026.json).

## Consulta conjunta (5.6 y 5.8)

| anio | tipo_taxi | archivos | registros | primer_mes | ultimo_mes |
| --- | --- | --- | --- | --- | --- |
| 2024 | green | 12 | 660218 | 2024-01-01 00:00:00 | 2024-12-01 00:00:00 |
| 2024 | yellow | 12 | 41169720 | 2024-01-01 00:00:00 | 2024-12-01 00:00:00 |
| 2026 | green | 8 | 337114 | 2026-01-01 00:00:00 | 2026-08-01 00:00:00 |
| 2026 | yellow | 8 | 29703355 | 2026-01-01 00:00:00 | 2026-08-01 00:00:00 |

Total conjunto: **71,870,407 registros** en **40 archivos**. Los años proceden del nombre del archivo; las fechas anómalas de los viajes no se corrigen.

### Meses con cobertura común

Meses presentes en ambos años y ambos tipos: 1, 2, 3, 4, 5, 6, 7, 8. 2024 tiene doce meses y 2026 solo los publicados. No se comparan directamente sus totales como si ambos representaran un año completo.

## Diferencias de esquema y continuidad de consultas (5.7)

| anio | tipo_taxi | columna | tipo_original | archivos_con_columna |
| --- | --- | --- | --- | --- |
| 2024 | green | RatecodeID | BIGINT | 12 |
| 2026 | green | RatecodeID | BIGINT | 8 |
| 2026 | green | cbd_congestion_fee | DOUBLE | 8 |
| 2024 | green | passenger_count | BIGINT | 12 |
| 2026 | green | passenger_count | BIGINT | 8 |
| 2024 | green | payment_type | BIGINT | 12 |
| 2026 | green | payment_type | BIGINT | 8 |
| 2026 | green | request_source | VARCHAR | 3 |
| 2024 | green | trip_type | BIGINT | 12 |
| 2026 | green | trip_type | BIGINT | 8 |
| 2024 | yellow | RatecodeID | BIGINT | 12 |
| 2026 | yellow | RatecodeID | BIGINT | 8 |
| 2026 | yellow | cbd_congestion_fee | DOUBLE | 8 |
| 2024 | yellow | passenger_count | BIGINT | 12 |
| 2026 | yellow | passenger_count | BIGINT | 8 |
| 2024 | yellow | payment_type | BIGINT | 12 |
| 2026 | yellow | payment_type | BIGINT | 8 |
| 2026 | yellow | request_source | VARCHAR | 3 |

`union_by_name=true` combina columnas por nombre y representa campos ausentes mediante NULL. Se ajustó 00_fuentes.sql con una rama vacía tipada (`WHERE FALSE`) para declarar cbd_congestion_fee y request_source incluso si se consultan solo archivos de 2024. La rama no añade filas ni imputa valores; evita depender de que existan archivos de 2026 para descubrir esos campos. La vista armoniza tpep/lpep y conserva el origen. Los tipos compatibles se promueven automáticamente; los originales y los finales se guardan por separado. No se fuerza una conversión a entero que pueda truncar valores.

La consulta 04 contrasta nulos de cbd_congestion_fee y request_source con su presencia física en la consulta 03. Un campo ausente en un año no se interpreta como cero ni como un valor no reportado en una columna existente.

| anio | tipo_taxi | registros | cbd_congestion_fee_nulo | request_source_nulo | pasajeros_nulos | pago_nulo |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | green | 660218 | 660218.0 | 660218.0 | 24328.0 | 24328.0 |
| 2024 | yellow | 41169720 | 41169720.0 | 41169720.0 | 4091232.0 | 0.0 |
| 2026 | green | 337114 | 0.0 | 317903.0 | 48775.0 | 48775.0 |
| 2026 | yellow | 29703355 | 0.0 | 26799909.0 | 7716688.0 | 0.0 |

Las **21 consultas existentes de los ejercicios 3 y 4** se ejecutaron sobre el conjunto ampliado sin modificar su SQL. Sus resultados conjuntos están en [compatibilidad_sql.csv](resultados_ejercicio_5/compatibilidad_sql.csv), con un CSV por consulta. Los notebooks y resultados originales de 2026 no se sobrescriben.

Que una consulta siga ejecutándose no convierte una agregación conjunta en una comparación entre años. Para una comparación anual debe añadirse el año al GROUP BY o restringirse la población. Las consultas nuevas 01–05 declaran explícitamente 2024 y 2026; las anteriores de hora, pagos y percentiles agregan el conjunto completo si se vuelven a ejecutar. Las medianas siguen siendo aproximadas.

## Consultas documentadas (5.8)

### 01_consulta_conjunta: Consulta conjunta por año y tipo

**Objetivo:** Demostrar que una misma vista consulta 2024 y 2026 y contar sus fuentes y registros.

**SQL:** [01_consulta_conjunta.sql](../sql/incremental/01_consulta_conjunta.sql). **Resultado:** [01_consulta_conjunta.csv](resultados_ejercicio_5/01_consulta_conjunta.csv), 4 filas.

**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar.

### 02_inventario: Inventario ampliado

**Objetivo:** Enumerar cada Parquet y contrastar COUNT de DuckDB con sus metadatos PyArrow.

**SQL:** [02_inventario.sql](../sql/incremental/02_inventario.sql). **Resultado:** [02_inventario.csv](resultados_ejercicio_5/02_inventario.csv), 40 filas.

**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar.

### 03_esquemas_por_anio: Esquemas por año

**Objetivo:** Identificar columnas ausentes y cambios de tipos físicos antes de interpretar NULL.

**SQL:** [03_esquemas_por_anio.sql](../sql/incremental/03_esquemas_por_anio.sql). **Resultado:** [03_esquemas_por_anio.csv](resultados_ejercicio_5/03_esquemas_por_anio.csv), 82 filas.

**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar.

### 04_campos_opcionales: Campos opcionales y nulos

**Objetivo:** Verificar la representación de campos añadidos sin imputar datos de años anteriores.

**SQL:** [04_campos_opcionales.sql](../sql/incremental/04_campos_opcionales.sql). **Resultado:** [04_campos_opcionales.csv](resultados_ejercicio_5/04_campos_opcionales.csv), 4 filas.

**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar.

### 05_meses_comunes: Meses con cobertura común

**Objetivo:** Identificar meses presentes para ambos taxis y ambos años, evitando comparar un año completo con uno parcial.

**SQL:** [05_meses_comunes.sql](../sql/incremental/05_meses_comunes.sql). **Resultado:** [05_meses_comunes.csv](resultados_ejercicio_5/05_meses_comunes.csv), 16 filas.

**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar.

### 06_tipos_unificados: Tipos de la vista conjunta

**Objetivo:** Documentar los tipos resultantes de la combinación de esquemas.

**SQL:** [06_tipos_unificados.sql](../sql/incremental/06_tipos_unificados.sql). **Resultado:** [06_tipos_unificados.csv](resultados_ejercicio_5/06_tipos_unificados.csv), 26 filas.

**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar.

## Diseño incremental (5.9)

Los parámetros de años evitan reescribir el descargador; las rutas separan tipo y año; los patrones `*/*.parquet` descubren nuevos archivos; las vistas guardan definiciones de lectura en lugar de copias; union_by_name tolera las columnas añadidas. Los manifiestos y verificaciones registran el alcance de cada ejecución y los archivos existentes no se descargan otra vez. Los análisis históricos quedan versionados y las comprobaciones de compatibilidad se guardan aparte.

## Preparación del ejercicio 6

[preparacion_benchmark.json](preparacion_benchmark.json) define tres volúmenes de datos, con rutas, tamaños y conteos exactos:

| nombre | descripcion | cantidad_archivos | registros | bytes_parquet |
| --- | --- | --- | --- | --- |
| pequeno | Enero de 2024, amarillos y verdes | 2 | 3021175 | 51323925 |
| mediano | Enero a junio de 2024, amarillos y verdes | 12 | 20671900 | 350080949 |
| completo | Todos los archivos validados de 2024 y 2026 | 40 | 71870407 | 1228648745 |

Todavía no se materializan tablas ni se registran tiempos. El ejercicio 6 deberá construir cada tabla y medir las mismas consultas contra sus Parquet equivalentes, con condiciones y repeticiones controladas. Este ejercicio deja las fuentes y tamaños preparados, sin adelantar conclusiones de rendimiento.
