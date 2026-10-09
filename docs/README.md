# Índice de documentación del laboratorio

Para evaluar o revisar el trabajo, lea primero los documentos principales. Los
notebooks muestran el SQL y sus salidas; los archivos CSV/JSON respaldan los conteos,
validaciones y mediciones, y no sustituyen las interpretaciones.

| Ejercicio | Qué revisar | Documento |
| --- | --- | --- |
| 1–2 | Ambiente, herramientas, organización, descarga y completitud | [Preparación y descarga](ejercicios_1_2.md) |
| 3 | Archivos/registros, columnas/tipos, muestras y problemas de calidad | [Exploración de Parquet](ejercicio_3_exploracion.md) |
| 4 | Preguntas justificadas, SQL, comparaciones, distribuciones y hallazgos | [Análisis exploratorio](ejercicio_4_analisis.md) |
| 5 | Incorporación de 2024, archivos preservados y continuidad SQL | [Incorporación incremental](ejercicio_5_incorporacion_2024.md) |
| 6 | Consultas equivalentes, repeticiones, tiempos, escala y discusión | [Benchmark](ejercicio_6_benchmark.md) |
| 7 | Preguntas, indicadores, poblaciones, unidades y tablero inicial | [Indicadores](ejercicio_7_indicadores.md) |
| 8 | 2025, tres años, períodos comparables y actualización del tablero | [Análisis completo](ejercicio_8_tres_anios.md) |
| 9 | Respuestas a las ocho preguntas de discusión | [Discusión final](ejercicio_9_discusion.md) |

## Evidencia del tablero final

- [Vista inicial de 2026 y comparaciones de tres años](figuras_ejercicio_8/tablero_tres_anios.png).
- [Selección de 2025](figuras_ejercicio_8/tablero_2025.png).
- [Definiciones de las 16 tarjetas](tablero/indicadores.json).
- [Registro de instalación](tablero/metabase_evidencia.json) y
  [comprobación con DuckDB](resultados_ejercicio_8/comprobacion_metabase.json).

El tablero final extiende los trece indicadores originales con tres comparaciones
en meses comunes. Las capturas iniciales del ejercicio 7 se mantienen como evidencia
histórica; para la entrega final utilice las del ejercicio 8.

## Resultados y figuras

| Etapa | Datos resumidos y evidencia | Gráficos |
| --- | --- | --- |
| Exploración | [Resultados 3](resultados_ejercicio_3/) | Tablas en el notebook |
| EDA | [Resultados 4](resultados_ejercicio_4/) | [Figuras 4](figuras_ejercicio_4/) |
| Incorporación 2024 | [Resultados 5](resultados_ejercicio_5/) | Tablas en el notebook |
| Benchmark | [Resultados 6](resultados_ejercicio_6/) | [Figuras 6](figuras_ejercicio_6/) |
| Indicadores iniciales | [Resultados 7](resultados_ejercicio_7/) | [Capturas iniciales](tablero/) |
| Tres años y tablero final | [Resultados 8](resultados_ejercicio_8/) | [Figuras y capturas 8](figuras_ejercicio_8/) |

Las validaciones de descarga son [2026](validacion_descarga_2026.json),
[2024/2026](validacion_descarga_2024_2026.json) y
[2024/2025/2026](validacion_descarga_2024_2025_2026.json).
La evidencia de preservación es [ejercicio 5](preservacion_2026_ejercicio_5.json)
y [ejercicio 8](resultados_ejercicio_8/preservacion.json).

## Alcance de los resultados

El benchmark entregado utiliza 2024/2026, con un máximo de 71.870.407 registros.
El análisis final utiliza 2024/2025/2026, con 121.184.384 registros. Los tiempos
anteriores no se presentan como mediciones del conjunto final. Las comparaciones
anuales usan enero–agosto, común a los tres años, con días calendario normalizados.

Los documentos conservan las preguntas del laboratorio junto con sus respuestas y
evidencia. No son instrucciones pendientes. No se requiere un informe adicional
en Word/PDF: la documentación entregable está en estos Markdown y notebooks.

[Volver al README y los comandos de reproducción](../README.md).
