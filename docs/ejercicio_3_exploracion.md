# Ejercicio 3: exploración directa de archivos Parquet

Generado con DuckDB 1.5.5 el 2026-10-07T01:27:57.876056+00:00 (UTC).

## Alcance y reproducción

Se consultan todos los Parquet descargados de taxis amarillos y verdes. Los patrones son `data/raw/yellow/*/*.parquet` y `data/raw/green/*/*.parquet`. La lista exacta de fuentes está en [el inventario](resultados_ejercicio_3/01_inventario.csv). El mes de archivo procede de su nombre; las fechas de los viajes se conservan sin corregir.

```bash
docker compose exec -T lab python scripts/explore_parquet.py
```

También puede ejecutar todas las celdas de `notebooks/03_exploracion_parquet.ipynb` en JupyterLab. Ambos caminos utilizan los mismos SQL y generan los mismos CSV. Los resultados se actualizan al incorporar archivos nuevos; esta documentación refleja el conjunto disponible al ejecutar el análisis.

## 3.1 y 3.2: archivos y registros

| tipo_taxi | archivos | registros |
| --- | --- | --- |
| green | 8 | 337114 |
| yellow | 8 | 29703355 |

Total: **16 archivos** y **30,040,469 registros**, obtenidos con COUNT sobre las fuentes Parquet.

## 3.3 y 3.4: columnas y tipos

| columna | tipo_duckdb | archivos |
| --- | --- | --- |
| Airport_fee | DOUBLE | 8 |
| DOLocationID | INTEGER | 16 |
| PULocationID | INTEGER | 16 |
| RatecodeID | BIGINT | 16 |
| VendorID | INTEGER | 16 |
| cbd_congestion_fee | DOUBLE | 16 |
| congestion_surcharge | DOUBLE | 16 |
| ehail_fee | DOUBLE | 8 |
| extra | DOUBLE | 16 |
| fare_amount | DOUBLE | 16 |
| improvement_surcharge | DOUBLE | 16 |
| lpep_dropoff_datetime | TIMESTAMP | 8 |
| lpep_pickup_datetime | TIMESTAMP | 8 |
| mta_tax | DOUBLE | 16 |
| passenger_count | BIGINT | 16 |
| payment_type | BIGINT | 16 |
| request_source | VARCHAR | 6 |
| store_and_fwd_flag | VARCHAR | 16 |
| tip_amount | DOUBLE | 16 |
| tolls_amount | DOUBLE | 16 |
| total_amount | DOUBLE | 16 |
| tpep_dropoff_datetime | TIMESTAMP | 8 |
| tpep_pickup_datetime | TIMESTAMP | 8 |
| trip_distance | DOUBLE | 16 |
| trip_type | BIGINT | 8 |

Los detalles de cada archivo están en `02_esquemas.csv`; la firma ordenada de nombres y tipos está en `03_cambios_esquema.csv`. Se comparan nombres y tipos, no solo cantidades.

Las columnas de fechas usan prefijos tpep en amarillos y lpep en verdes. La vista `viajes` les asigna los nombres `recogida` y `llegada`. En los archivos de 2026 explorados, request_source aparece desde junio; los meses anteriores reciben NULL al unir por nombre. Los campos exclusivos de un tipo (airport_fee, ehail_fee y trip_type) también se conservan como NULL para el otro tipo. Esos NULL estructurales no se contabilizan como problemas de calidad en la consulta 05.

## 3.5: muestra

La consulta 04 devuelve cinco filas por tipo, con su archivo de procedencia. El resultado completo está en el notebook y [04_muestras.csv](resultados_ejercicio_3/04_muestras.csv). LIMIT no genera una muestra aleatoria ni representativa.

## 3.6: posibles problemas de calidad

### Resultados e interpretación

- **yellow:** 7,716,688 registros sin pasajeros (25.98%); 146 recogidas fuera del mes del archivo y 10 duraciones negativas. La primera recogida registrada es 2001-01-01 09:23:58. La distancia máxima es 328,522.20 millas, frente a un percentil 99 aproximado de 19.55 millas. Hay 161,835 importes totales negativos (0.5448%).
- **green:** 48,775 registros sin pasajeros (14.47%); 98 recogidas fuera del mes del archivo y 5 duraciones negativas. La primera recogida registrada es 2008-12-31 17:35:31. La distancia máxima es 179,830.92 millas, frente a un percentil 99 aproximado de 17.78 millas. Hay 1,023 importes totales negativos (0.3035%).

En yellow, todos los pasajeros nulos coinciden con la categoría pago 0 (Flex Fare), y todos los registros de esa categoría tienen pasajeros nulos. En green, todos los pasajeros nulos coinciden con la categoría pago nulo, y todos los registros de esa categoría tienen pasajeros nulos. La consulta 08 permite revisar asociaciones entre nulos y categorías de pago. Una asociación observada no explica su causa: excluir todas las filas con pasajeros nulos puede cambiar la cobertura de modalidades. Por eso no se aplica una limpieza automática.

Los rangos y percentiles deben revisarse antes de calcular promedios. Una recogida fuera del mes nominal necesita inspección, incluyendo posibles viajes alrededor del cambio de año. El cambio de esquema se registra como evolución de la fuente, no como corrupción de archivos.

### Valores faltantes

| tipo_taxi | registros | recogida_nula | llegada_nula | pasajeros_nulos | distancia_nula | total_nulo | pago_nulo | tarifa_nula | envio_nulo | alguna_zona_nula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| green | 337114 | 0.0 | 0.0 | 48775.0 | 0.0 | 0.0 | 48775.0 | 48775.0 | 48775.0 | 0.0 |
| yellow | 29703355 | 0.0 | 0.0 | 7716688.0 | 0.0 | 0.0 | 0.0 | 7716688.0 | 7716688.0 | 0.0 |

### Alertas y proporciones

| Tipo | Alerta | Registros | Porcentaje del tipo |
| --- | --- | --- | --- |
| green | fecha_fuera_mes_archivo | 98 | 0.0291% |
| green | duracion_negativa | 5 | 0.0015% |
| green | duracion_cero | 229 | 0.0679% |
| green | duracion_mayor_24h | 4 | 0.0012% |
| green | distancia_negativa | 0 | 0.0000% |
| green | distancia_cero | 12,212 | 3.6225% |
| green | distancia_mayor_100_millas | 72 | 0.0214% |
| green | pasajeros_no_positivos | 4,527 | 1.3429% |
| green | pasajeros_mayor_6 | 99 | 0.0294% |
| green | total_negativo | 1,023 | 0.3035% |
| green | total_cero | 543 | 0.1611% |
| green | pago_codigo_no_documentado | 0 | 0.0000% |
| green | tarifa_codigo_no_documentado | 0 | 0.0000% |
| yellow | fecha_fuera_mes_archivo | 146 | 0.0005% |
| yellow | duracion_negativa | 10 | 0.0000% |
| yellow | duracion_cero | 371,673 | 1.2513% |
| yellow | duracion_mayor_24h | 263 | 0.0009% |
| yellow | distancia_negativa | 0 | 0.0000% |
| yellow | distancia_cero | 952,231 | 3.2058% |
| yellow | distancia_mayor_100_millas | 1,223 | 0.0041% |
| yellow | pasajeros_no_positivos | 91,359 | 0.3076% |
| yellow | pasajeros_mayor_6 | 28 | 0.0001% |
| yellow | total_negativo | 161,835 | 0.5448% |
| yellow | total_cero | 5,258 | 0.0177% |
| yellow | pago_codigo_no_documentado | 0 | 0.0000% |
| yellow | tarifa_codigo_no_documentado | 0 | 0.0000% |

Las alertas se superponen; sumarlas no equivale a contar viajes únicos con problemas. Los nulos se cuentan por separado y no satisfacen las comparaciones numéricas. Los umbrales de 100 millas, 24 horas y 6 pasajeros se usan para inspección, no como restricciones oficiales ni filtros de limpieza.

Una fecha fuera del mes del nombre necesita revisión; no prueba por sí sola un error. Una llegada anterior a la recogida produce duración negativa. Los ceros y los importes negativos requieren contexto (por ejemplo, los códigos de pago distinguen disputas y viajes anulados). No se atribuye una causa a cada importe negativo sin evidencia adicional. La consulta 08 permite examinarlos por tipo de pago y la 10 muestra ejemplos.

## 3.7 y 3.8: documentación de consultas

La preparación [00_fuentes.sql](../sql/exploracion/00_fuentes.sql) crea vistas raw y una vista con nombres armonizados. Todas son vistas en memoria sobre read_parquet; no se importa ni materializa el conjunto de viajes. UNION ALL conserva las filas. No se filtran, deduplican, imputan ni modifican los valores originales. Cada consulta siguiente usa las fuentes del inventario, directamente o mediante esas vistas.

### 01_inventario: Archivos y registros

**Objetivo:** Contar los archivos y registros disponibles por tipo y mes.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [01_inventario.sql](../sql/exploracion/01_inventario.sql). **Resultado:** [01_inventario.csv](resultados_ejercicio_3/01_inventario.csv), 16 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Usar el mes del nombre del archivo para inventariar; no confundirlo con la fecha registrada de cada viaje.

### 02_esquemas: Columnas y tipos

**Objetivo:** Identificar columnas, tipos físicos y tipos DuckDB en cada archivo.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [02_esquemas.sql](../sql/exploracion/02_esquemas.sql). **Resultado:** [02_esquemas.csv](resultados_ejercicio_3/02_esquemas.csv), 334 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Conservar los nombres originales en las vistas raw; revisar los esquemas antes de combinar archivos.

### 03_cambios_esquema: Evolución del esquema

**Objetivo:** Comparar nombres y tipos de columnas entre meses.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [03_cambios_esquema.sql](../sql/exploracion/03_cambios_esquema.sql). **Resultado:** [03_cambios_esquema.csv](resultados_ejercicio_3/03_cambios_esquema.csv), 16 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Usar union_by_name y distinguir un campo ausente de un dato no reportado en un campo existente.

### 04_muestras: Muestra de registros

**Objetivo:** Inspeccionar cinco registros de cada tipo de taxi.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [04_muestras.sql](../sql/exploracion/04_muestras.sql). **Resultado:** [04_muestras.csv](resultados_ejercicio_3/04_muestras.csv), 10 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** La muestra LIMIT sirve para inspeccionar filas, pero no permite estimar la distribución de todos los viajes.

### 05_nulos: Valores nulos

**Objetivo:** Medir valores faltantes en los campos compartidos por ambos tipos.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [05_nulos.sql](../sql/exploracion/05_nulos.sql). **Resultado:** [05_nulos.csv](resultados_ejercicio_3/05_nulos.csv), 2 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Mantener los nulos y analizar qué campos son necesarios para cada pregunta antes de filtrar o imputar.

### 06_calidad: Alertas de calidad

**Objetivo:** Cuantificar fechas discordantes, duraciones, distancias, pasajeros e importes sospechosos.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [06_calidad.sql](../sql/exploracion/06_calidad.sql). **Resultado:** [06_calidad.csv](resultados_ejercicio_3/06_calidad.csv), 2 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Conservar las alertas; los umbrales de 24 horas, 100 millas y 6 pasajeros son exploratorios y no reglas de eliminación.

### 07_distribuciones: Rangos y percentiles

**Objetivo:** Comparar extremos con percentiles aproximados de los valores originales.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [07_distribuciones.sql](../sql/exploracion/07_distribuciones.sql). **Resultado:** [07_distribuciones.csv](resultados_ejercicio_3/07_distribuciones.csv), 2 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Revisar valores extremos antes de usar promedios o gráficos; los percentiles son aproximados y los nulos se omiten en estas funciones.

### 08_categorias_pago: Códigos de pago

**Objetivo:** Examinar pagos, importes negativos y nulos de pasajeros por categoría.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [08_categorias_pago.sql](../sql/exploracion/08_categorias_pago.sql). **Resultado:** [08_categorias_pago.csv](resultados_ejercicio_3/08_categorias_pago.csv), 11 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** El código 0 es Flex Fare según TLC; no clasificarlo como inválido. Un importe negativo requiere contexto y no se elimina automáticamente.

### 09_request_source: Campo agregado entre meses

**Objetivo:** Contar valores de request_source por mes y tipo.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [09_request_source.sql](../sql/exploracion/09_request_source.sql). **Resultado:** [09_request_source.csv](resultados_ejercicio_3/09_request_source.csv), 37 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Los NULL anteriores a la incorporación de la columna son ausencia estructural; no inferir demanda a partir de ellos.

### 10_ejemplos_alertas: Ejemplos de alertas

**Objetivo:** Mostrar hasta tres filas por alerta para inspeccionar casos concretos.

**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.

**SQL:** [10_ejemplos_alertas.sql](../sql/exploracion/10_ejemplos_alertas.sql). **Resultado:** [10_ejemplos_alertas.csv](resultados_ejercicio_3/10_ejemplos_alertas.csv), 12 filas de salida. El notebook muestra el SQL y su resultado.

**Decisión:** Los ejemplos pueden solaparse y no representan una muestra aleatoria; documentar las reglas antes de una limpieza posterior.

## 3.9: qué significa consultar Parquet directamente

read_parquet permite que DuckDB ejecute SQL sobre archivos externos sin cargarlos previamente en una tabla. Las vistas guardan la definición de lectura y se evalúan al consultar. Parquet almacena columnas por grupos de filas; DuckDB puede leer solo columnas necesarias y aprovechar filtros y metadatos cuando la consulta lo permite. Así se evita copiar todo el conjunto a un DataFrame y se pueden incorporar nuevos archivos mediante patrones de rutas.

Esto no significa que todas las consultas sean gratuitas: los perfiles de calidad y percentiles deben examinar valores, y filtros o agregaciones complejos pueden requerir CPU, memoria o disco temporal. Los CSV y DataFrames de este ejercicio contienen solo metadatos, agregados y muestras pequeñas.

## Fuentes y límites de interpretación

- [Documentación de DuckDB sobre Parquet](https://duckdb.org/docs/stable/data/parquet/overview).

- [Catálogo oficial TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

- [Diccionario TLC de taxis amarillos](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf).

- [Diccionario TLC de taxis verdes](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf).

Los diccionarios consultados están fechados el 18 de marzo de 2025: documentan distancia en millas, códigos de pago 0–6 (incluido Flex Fare), tarifa 99 como desconocida y que las propinas en efectivo no se incluyen. No describen request_source; sus categorías se registran sin atribuirles significado no confirmado. La TLC advierte que no garantiza la exactitud de los datos. Estas comprobaciones no constituyen un análisis exhaustivo de duplicados ni una validación de zonas contra su catálogo.
