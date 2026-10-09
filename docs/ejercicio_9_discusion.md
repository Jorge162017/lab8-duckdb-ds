# Ejercicio 9: discusión final

Trabajo individual. La discusión se basa en las consultas y verificaciones ejecutadas,
el benchmark de los ejercicios anteriores y la incorporación de 2024, 2025 y 2026.
El conjunto final tiene **64 Parquet y 121.184.384 registros**. El benchmark se realizó
antes de incorporar 2025: su conjunto mayor tiene **40 archivos y 71.870.407 registros**.
Sus tiempos no se presentan como mediciones del conjunto final de tres años.

## 9.1. ¿Qué características de DuckDB resultaron más útiles?

La consulta SQL directa sobre Parquet permitió explorar estructura, contenido y calidad
sin importar primero los viajes a una tabla. Los patrones de archivos y las vistas
permitieron combinar meses y años, mientras que `union_by_name` conservó columnas
que no estaban presentes en todas las versiones del esquema. Por ejemplo,
`cbd_congestion_fee` y `request_source` no existen físicamente en 2024; se representan
como NULL, sin atribuirles valores cero.

Las agregaciones, funciones de fechas y ventanas hicieron posible contar viajes,
normalizar demanda por días calendario, obtener proporciones y comparar períodos.
La materialización posterior permitió mantener una instantánea persistente para
Metabase. Ambas estrategias comparten el mismo motor y el mismo esquema lógico,
lo que facilitó comprobar resultados equivalentes.

Evidencia: [exploración](ejercicio_3_exploracion.md),
[incorporación incremental](ejercicio_5_incorporacion_2024.md) y
[tablero](ejercicio_7_indicadores.md).

## 9.2. ¿Qué ventajas y limitaciones encontró al consultar Parquet directamente?

La principal ventaja fue trabajar con archivos nuevos sin copiar todo el conjunto a
una base ni cargarlo completo en Pandas. Se conservaron los originales por tipo y año,
y las consultas podían descubrir los archivos agregados. Las consultas de metadatos
permitieron revisar columnas y tipos sin leer todos los valores. La lectura por
columnas y los filtros pueden reducir el trabajo según la consulta y la organización
de los archivos.

Como limitación, las consultas dependen de rutas accesibles y de esquemas compatibles.
Las columnas opcionales y los nombres distintos de fechas necesitaron armonización.
Los perfiles de calidad y las distribuciones examinan valores y consumen recursos;
no toda consulta se resuelve desde los metadatos. En consultas repetidas del benchmark,
Parquet tuvo medianas mayores que la tabla en este entorno. Esto no demuestra que el
formato sea siempre menos conveniente: evita el costo inicial y el mantenimiento
de una copia materializada.

Evidencia: [SQL de fuentes](../sql/exploracion/00_fuentes.sql) y
[comparación de tiempos](resultados_ejercicio_6/comparacion.csv).

## 9.3. ¿Qué ventajas y limitaciones observó con tablas materializadas?

La tabla ofreció una fuente persistente con nombres y tipos armonizados, lista para
el tablero. En las 15 combinaciones de consulta y volumen del benchmark tuvo menor
mediana. Para 71.870.407 registros, la consulta filtrada pasó de **0,433 s en Parquet**
a **0,028 s en la tabla**, aproximadamente 15,33 veces en razón de tiempos. El perfil
de características pasó de 2,418 a 1,158 segundos.

El beneficio requirió una inversión: construir y persistir esa tabla costó **39,20 s**
y su archivo ocupa **2.033.201.152 bytes** adicionales, unos 1,89 GiB. Una tabla es
una instantánea; agregar archivos no actualiza automáticamente su contenido. Para
incorporar 2025 se creó otra instantánea identificada por sus fuentes y se cambió
la conexión de Metabase, preservando las bases y los tiempos históricos del benchmark.
La instantánea final ocupa 3.464.507.392 bytes, aproximadamente 3,23 GiB.

Se usaron conexiones de solo lectura para los consumidores y se separaron directorios
temporales entre procesos. El benchmark utilizó calentamiento, cinco repeticiones,
orden intercalado y condiciones registradas; no midió caché fría ni aisló toda la carga
del host. Las diferencias no se atribuyen exclusivamente al formato: también influyen
organización, cachés y campos derivados precomputados al materializar.

Evidencia: [benchmark y límites](ejercicio_6_benchmark.md),
[costos de construcción](resultados_ejercicio_6/materializacion.csv) e
[instantánea final](resultados_ejercicio_8/instantanea.json).

## 9.4. ¿Qué ventajas ofrece frente a cargar todos los datos en Pandas?

DuckDB permitió filtrar y agregar antes de convertir resultados a DataFrames. Pandas
se utilizó para tablas pequeñas, metadatos, resultados agrupados y preparación de
gráficos, no para almacenar los 121 millones de viajes completos. Esto evita que la
exploración dependa de mantener toda la representación tabular en memoria de Python.
El tamaño comprimido de Parquet no equivale al tamaño que tendría un DataFrame con
los mismos valores.

SQL también permitió expresar agrupaciones y filtros sobre múltiples archivos con
un flujo común. La ventaja no significa que Pandas sea innecesario: fue útil para
inspección y visualización después de reducir los datos. **No se realizó un benchmark
contra Pandas**, por lo que no se afirma un factor de velocidad o consumo de memoria
medido frente a esa herramienta. Tampoco se midió el pico de memoria; `memory_limit`
es una configuración de DuckDB y no un límite total de la memoria del proceso.

Evidencia: [script de exploración](../scripts/explore_parquet.py),
[análisis](../scripts/analyze_trips.py) y
[entorno del benchmark](resultados_ejercicio_6/entorno.json).

## 9.5. ¿Qué permite incorporar datos nuevos con cambios mínimos?

El descargador recibe años como parámetros, organiza rutas por tipo/año y omite los
archivos existentes. Los manifiestos describen cada ejecución y el validador comprueba
su cobertura, tamaños y metadatos, exigiendo doce meses en los años cerrados cuando
corresponde. Los patrones de archivos, vistas y unión por nombre evitan reescribir
las consultas para cada mes.

Los campos opcionales se declaran sin agregar filas, y se conservan año, mes y archivo
de procedencia. Los indicadores usan filtros de año/tipo. Para la tabla del tablero,
la configuración guarda la ruta de una instantánea nueva; el instalador actualiza
la conexión y las tarjetas existentes sin crear otro tablero.

La incorporación de 2025 descargó 24 archivos y preservó los 40 anteriores en tamaño,
fecha de modificación y SHA-256. La ejecución repetida omitió los 64, sin nuevas
descargas ni errores. Se realizaron 74 comprobaciones de consultas/selecciones sobre
el conjunto ampliado. La evolución se compara en enero–agosto, común a los tres años,
con 244 días en 2024 y 243 en 2025/2026; así no se confunden calendario y cobertura.

Evidencia: [validación y evolución](ejercicio_8_tres_anios.md),
[preservación](resultados_ejercicio_8/preservacion.json) y
[compatibilidad](resultados_ejercicio_8/compatibilidad.csv).

## 9.6. ¿Qué parte debería automatizarse en producción?

Automatizaría el flujo completo desde comprobar nuevas publicaciones hasta actualizar
los resultados: descarga incremental con reintentos, validación de integridad y esquema,
registro del manifiesto, perfiles de calidad y construcción de una instantánea cuando
haya datos nuevos. También automatizaría la comparación de conteos y resultados,
la actualización de la conexión del tablero y su comprobación posterior.

Un programador de tareas debería registrar errores y distinguir archivo no publicado
de fallo de conexión. Las huellas de fuentes permitirían evitar reconstrucciones sin
cambios. La publicación de una nueva instantánea debería ocurrir solo después de
validarla, manteniendo la anterior para recuperación. Los secretos se gestionarían
fuera de Git y la autenticación no formaría parte de notebooks o capturas.

Los umbrales de calidad no deberían eliminar automáticamente todos los casos marcados:
se necesita una política de negocio y trazabilidad de decisiones. El laboratorio tiene
scripts reproducibles y una instalación repetible del tablero, pero **no implementa
un servicio programado de producción** ni un sistema completo de alertas.

## 9.7. ¿Qué decisiones mantuvieron el proyecto reproducible?

Se fijaron versiones de herramientas en Docker y se documentaron servicios, rutas y
comandos. Se versionaron los SQL, scripts, notebooks ejecutados, resultados pequeños,
gráficos y capturas; los datos originales y bases se regeneran y están excluidos junto
con credenciales, sesiones, temporales e instrucciones locales. Los manifiestos y
conteos registran las fuentes; las verificaciones SHA-256 demuestran preservación.

Se declararon poblaciones separadas para demanda y mediciones, sin ocultar pagos o
pasajeros nulos. Las comparaciones anuales usan cobertura común, días calendario y
unidades explícitas. El benchmark guarda repeticiones individuales, calentamientos,
configuración, planes y equivalencia, en lugar de presentar un único tiempo. Los
percentiles se identifican como aproximados y se preserva el alcance histórico de
cada etapa: el benchmark de 2024/2026 no se mezcla con el análisis final de tres años.

Para reproducir el resultado final hay que seguir el orden de incorporación y construir
la instantánea antes de instalar el tablero. El [README](../README.md) incluye ese orden.
La URL y los IDs del tablero pertenecen a una instalación local y el instalador imprime
los correspondientes cuando se reproduce en otra computadora.

## 9.8. ¿Qué aprendió sobre datos grandes que no se ve con datos pequeños?

La muestra de unas pocas filas no permitió reconocer por sí sola las anomalías o la
cobertura de nulos. Los conteos completos mostraron fechas fuera del mes, duraciones
negativas, distancias extremas y asociaciones entre campos ausentes y modalidades
de pago. La distancia media verde de 2026 pasó de 13,35 a 3,36 millas al aplicar el
conjunto de filtros de medición, conservando 96,04% de las filas temporales. Eso mostró
que una proporción pequeña de registros y varias decisiones de filtrado pueden cambiar
mucho una media; no se atribuye toda la diferencia a un solo criterio.

También se hizo visible que esquemas y modalidades de registro cambian con el tiempo.
En el período común, pasajeros nulos amarillos pasaron de 9,53% a 23,27% y 25,98% en
2024, 2025 y 2026. No representan necesariamente viajes vacíos. La demanda diaria
verde disminuyó 23,67% entre 2024 y 2026, mientras la amarilla aumentó 13,03%, con un
máximo intermedio en 2025. Interpretar esos cambios exigió controlar meses y días,
sin afirmar causalidad o extrapolar meses faltantes.

A escala grande, importan las lecturas evitadas, la memoria intermedia, el costo de
materializar, la actualización de instantáneas y la separación de temporales entre
procesos. El laboratorio mostró que resultados correctos, trazabilidad y criterios de
comparación son tan necesarios como obtener un tiempo bajo de consulta.

Evidencia: [sensibilidad a filtros](ejercicio_4_analisis.md) y
[patrones de los tres años](ejercicio_8_tres_anios.md).
