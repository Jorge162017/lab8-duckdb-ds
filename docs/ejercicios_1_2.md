# Ejercicios 1 y 2: ambiente y descarga inicial

## Organización del proyecto

Trabajo individual. El remoto `origin` apunta al fork
`git@github.com:Jorge162017/lab8-duckdb-ds.git`.

| Directorio | Propósito |
| --- | --- |
| `data/raw/` | Parquet originales de la TLC, organizados por tipo y año. |
| `data/processed/` | Datos derivados, manifiestos y futuras bases DuckDB. |
| `scripts/` | Procesos reproducibles de descarga, validación y benchmarks. |
| `sql/` | Consultas SQL documentadas. |
| `notebooks/` | Exploración y explicación de resultados. |
| `docs/` | Evidencia, decisiones e interpretaciones. |

Los datos y `instrucciones/` están excluidos por `.gitignore`. El PDF permanece
local y no forma parte de la entrega.

## Ambiente reproducible (1.4 y 1.6)

Docker Compose define dos servicios: `lab` para Python/JupyterLab y `metabase`
para el tablero. El primero incluye DuckDB, Pandas, PyArrow, Matplotlib y Requests;
el segundo incluye Java y un driver DuckDB. Los volúmenes mantienen los archivos
fuera de los contenedores y la configuración de Metabase en un volumen persistente.

Fijar versiones y compartir la configuración permite repetir el trabajo en otras
computadoras, evita depender de instalaciones personales y facilita diagnosticar
resultados diferentes. Para reproducir los comandos consulte el README.

## Análisis y cambios del descargador (2.1–2.6)

La versión base ya contemplaba ambos tipos de taxi de 2026, los doce meses,
archivos existentes, reintentos de descarga y renombrado de archivos temporales.
Por ello se conservaron esas funciones y se mejoró la verificación:

- Antes cualquier error de red se confundía con un mes no publicado. Ahora
  HTTP 404 indica ausencia y HTTP 403 se contrasta con los enlaces del catálogo
  oficial. Un 403 sin enlace se considera no publicado; si el enlace existe o
  el catálogo falla, se conserva el error. Otros fallos se reintentan y producen
  código de salida 1.
- Se verifica `Content-Length` si el servidor lo proporciona y las firmas inicial
  y final `PAR1` antes de renombrar el archivo temporal.
- Se añadió `--verify-availability`, que consulta también los archivos existentes
  sin descargarlos de nuevo.
- Cada ejecución genera un manifiesto JSON con fecha UTC, URL, ruta, estado y
  tamaño de los archivos.
- `validate_download.py` verifica que el manifiesto cubra los 24 candidatos,
  comprueba los tamaños y abre los metadatos mediante PyArrow. No carga todos
  los viajes en memoria. Su reporte contiene archivos, registros y errores.

Las firmas por sí solas no prueban la integridad de todos los registros; abrir
los metadatos verifica la estructura, y las consultas del ejercicio 3 examinarán
el contenido y su calidad.

## Criterio de completitud (2.7)

Completo significa todos los archivos publicados de ambos tipos para 2026 a la
fecha de ejecución, sin errores de consulta o descarga. Los meses no publicados
se enumeran explícitamente. No equivale a disponer de doce meses por tipo.

El manifiesto cubre los 24 candidatos y el reporte de validación debe indicar
`completo_segun_publicacion: true`. Una segunda ejecución debe omitir los archivos
existentes y descargar cero archivos si no aparecen nuevas publicaciones.

## Estado de ejecución

Verificación realizada el 6 de octubre de 2026 (hora de Guatemala).

### Descarga: completada

- Archivos disponibles descargados: 16 (8 amarillos y 8 verdes, enero–agosto).
- Tamaño total: 519.727.000 bytes (aproximadamente 495,65 MiB).
- Registros según metadatos: 30.040.469.
- Segunda ejecución: 0 descargados, 16 omitidos, 8 candidatos no publicados,
  0 fallos. Los candidatos ausentes corresponden a septiembre–diciembre de
  ambos tipos; sus enlaces no están en el catálogo oficial.
- Validación PyArrow: 16 archivos legibles, cero errores y
  `completo_segun_publicacion: true`.

La evidencia por archivo está en [validacion_descarga_2026.json](validacion_descarga_2026.json).
La descarga inicial se ejecutó con Python local y Requests, y la primera
validación utilizó un entorno temporal con PyArrow 25.0.1. Después de recuperar
Docker, se volvió a ejecutar `scripts/validate_download.py` dentro del servicio
`lab`: terminó con código 0 y validó nuevamente los 16 archivos. Los comandos
dentro de Docker están documentados en el README.

Se observó un cambio en la cantidad de columnas desde junio: los amarillos pasan
de 20 a 21 y los verdes de 21 a 22. El ejercicio 3 deberá revisar los esquemas
antes de consultar conjuntamente los archivos.

### Ambiente: completado y verificado

`docker compose config --quiet` terminó con código 0. El remoto apunta al fork y
se confirmó espacio suficiente en disco (aproximadamente 149 GiB disponibles).

El inicio estuvo bloqueado por un proceso de Docker atascado y variables de
entorno incorrectas. Se recuperó el motor, se construyó la imagen de análisis y
se verificaron Jupyter y Metabase. La evidencia de recuperación y las versiones
se detallan abajo. Ambos servicios están activos y responden con HTTP 200.

### Recuperación de Docker Desktop

El motor volvió a responder después de terminar el proceso `com.docker.backend`
que había quedado atascado y abrir la aplicación completa con las rutas del
sistema. Se verificó Docker Engine 24.0.7. El entorno de lanzamiento tenía
`PATH` limitado a Flutter y `ELECTRON_RUN_AS_NODE=1`; los registros mostraban
que `sw_vers` no se encontraba. Para un inicio con el entorno corregido:

```bash
/usr/bin/open -n -a Docker \
  --env PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  --env ELECTRON_RUN_AS_NODE=
```

La respuesta del motor se comprobó antes de construir los servicios del
laboratorio. Las verificaciones de los servicios se registran a continuación.

### Verificación del servicio de análisis

JupyterLab respondió correctamente en `http://localhost:8888/api/status` y
DuckDB ejecutó `SELECT 1 AS verificacion_duckdb`, devolviendo `[(1,)]`.
Se verificaron estas versiones dentro del contenedor:

| Herramienta | Versión |
| --- | --- |
| Python | 3.11.14 |
| DuckDB | 1.5.5 |
| JupyterLab | 4.6.4 |
| Pandas | 3.0.6 |
| PyArrow | 25.0.1 |
| Matplotlib | 3.11.2 |
| Requests | 2.34.2 |

### Verificación de Metabase y resultado final

El primer arranque terminó con `Metabase Initialization COMPLETE`.
`http://localhost:3000/api/health` respondió HTTP 200 y `{"status":"ok"}`.
La página principal de Metabase y `/lab` de Jupyter respondieron HTTP 200.
Los registros de Metabase confirmaron `Registered driver :duckdb`.

| Contenedor | Estado verificado | Puerto local |
| --- | --- | --- |
| `lab8-lab` | Running / Up | `127.0.0.1:8888` |
| `lab8-metabase` | Running / Up | `127.0.0.1:3000` |

Se construyeron las dos imágenes con los Dockerfiles originales. Como Jupyter se
inició durante la construcción de Metabase para verificarlo antes, el comando
inicial de Compose encontró un conflicto al intentar crear otra vez ese mismo
contenedor. Se resolvió ejecutando `docker compose up -d --no-build`, que reconoció
el contenedor existente y arrancó Metabase. No fue necesario cambiar versiones,
eliminar volúmenes ni borrar datos.

Los ejercicios 1 y 2 están completados: ambiente funcional, herramientas
verificadas, descarga inicial validada y procedimiento reproducible documentado.
La cuenta inicial de Metabase se configura desde su página al utilizarlo por
primera vez; todavía no se ha conectado una base analítica ni creado un tablero,
actividades de ejercicios posteriores.
