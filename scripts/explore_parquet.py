"""Ejercicio 3: consultas directas sobre Parquet y documentación reproducible."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "exploracion"
OUTPUT_DIR = ROOT / "docs" / "resultados_ejercicio_3"
QUERY_SPECS = [
    ("01_inventario", "Archivos y registros", "Contar los archivos y registros disponibles por tipo y mes.",
     "Usar el mes del nombre del archivo para inventariar; no confundirlo con la fecha registrada de cada viaje."),
    ("02_esquemas", "Columnas y tipos", "Identificar columnas, tipos físicos y tipos DuckDB en cada archivo.",
     "Conservar los nombres originales en las vistas raw; revisar los esquemas antes de combinar archivos."),
    ("03_cambios_esquema", "Evolución del esquema", "Comparar nombres y tipos de columnas entre meses.",
     "Usar union_by_name y distinguir un campo ausente de un dato no reportado en un campo existente."),
    ("04_muestras", "Muestra de registros", "Inspeccionar cinco registros de cada tipo de taxi.",
     "La muestra LIMIT sirve para inspeccionar filas, pero no permite estimar la distribución de todos los viajes."),
    ("05_nulos", "Valores nulos", "Medir valores faltantes en los campos compartidos por ambos tipos.",
     "Mantener los nulos y analizar qué campos son necesarios para cada pregunta antes de filtrar o imputar."),
    ("06_calidad", "Alertas de calidad", "Cuantificar fechas discordantes, duraciones, distancias, pasajeros e importes sospechosos.",
     "Conservar las alertas; los umbrales de 24 horas, 100 millas y 6 pasajeros son exploratorios y no reglas de eliminación."),
    ("07_distribuciones", "Rangos y percentiles", "Comparar extremos con percentiles aproximados de los valores originales.",
     "Revisar valores extremos antes de usar promedios o gráficos; los percentiles son aproximados y los nulos se omiten en estas funciones."),
    ("08_categorias_pago", "Códigos de pago", "Examinar pagos, importes negativos y nulos de pasajeros por categoría.",
     "El código 0 es Flex Fare según TLC; no clasificarlo como inválido. Un importe negativo requiere contexto y no se elimina automáticamente."),
    ("09_request_source", "Campo agregado entre meses", "Contar valores de request_source por mes y tipo.",
     "Los NULL anteriores a la incorporación de la columna son ausencia estructural; no inferir demanda a partir de ellos."),
    ("10_ejemplos_alertas", "Ejemplos de alertas", "Mostrar hasta tres filas por alerta para inspeccionar casos concretos.",
     "Los ejemplos pueden solaparse y no representan una muestra aleatoria; documentar las reglas antes de una limpieza posterior."),
]


def create_connection():
    if not list((ROOT / "data" / "raw" / "yellow").glob("*/*.parquet")):
        raise FileNotFoundError("Primero descargue los Parquet de taxis amarillos.")
    if not list((ROOT / "data" / "raw" / "green").glob("*/*.parquet")):
        raise FileNotFoundError("Primero descargue los Parquet de taxis verdes.")
    # Base en memoria, sin CREATE TABLE: las vistas siguen leyendo los Parquet.
    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit = '2GB'")
    connection.execute("SET threads = 4")
    connection.execute((SQL_DIR / "00_fuentes.sql").read_text(encoding="utf-8"))
    return connection


def run_query(connection, name, output_dir=OUTPUT_DIR):
    sql = (SQL_DIR / (name + ".sql")).read_text(encoding="utf-8")
    frame = connection.execute(sql).fetchdf()
    # Solo resultados pequeños y metadatos llegan a Pandas, nunca todos los viajes.
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / (name + ".csv"), index=False)
    return frame


def table(frame):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    header = "| " + " | ".join(map(clean, frame.columns)) + " |"
    divider = "| " + " | ".join("---" for _ in frame.columns) + " |"
    rows = ["| " + " | ".join(map(clean, row)) + " |" for row in frame.itertuples(index=False, name=None)]
    return "\n".join([header, divider, *rows])


def write_report(connection, frames, output_dir=OUTPUT_DIR):
    inventory = frames["01_inventario"]
    summary = inventory.groupby("tipo_taxi").agg(archivos=("archivo", "nunique"), registros=("registros", "sum")).reset_index()
    schema = frames["02_esquemas"]
    fields = schema.groupby(["columna", "tipo_duckdb"]).agg(archivos=("archivo", "nunique")).reset_index()
    quality = frames["06_calidad"]
    nulls = frames["05_nulos"]
    findings = []
    for tipo in ("yellow", "green"):
        n = nulls.loc[nulls.tipo_taxi == tipo].iloc[0]
        q = quality.loc[quality.tipo_taxi == tipo].iloc[0]
        distribution = frames["07_distribuciones"]
        d = distribution.loc[distribution.tipo_taxi == tipo].iloc[0]
        findings.append(
            f"- **{tipo}:** {int(n.pasajeros_nulos):,} registros sin pasajeros "
            f"({100 * n.pasajeros_nulos / n.registros:.2f}%); "
            f"{int(q.fecha_fuera_mes_archivo):,} recogidas fuera del mes del archivo y "
            f"{int(q.duracion_negativa):,} duraciones negativas. "
            f"La primera recogida registrada es {q.primera_recogida}. "
            f"La distancia máxima es {d.distancia_max:,.2f} millas, frente a un "
            f"percentil 99 aproximado de {d.distancia_p50_p95_p99[2]:.2f} millas. "
            f"Hay {int(q.total_negativo):,} importes totales negativos "
            f"({100 * q.total_negativo / q.registros:.4f}%)."
        )
    payment = frames["08_categorias_pago"]
    pattern_notes = []
    for tipo, codigo in (("yellow", 0), ("green", None)):
        subset = payment.loc[payment.tipo_taxi == tipo]
        category = subset.loc[subset.payment_type.isna() if codigo is None
                              else subset.payment_type == codigo]
        missing = int(nulls.loc[nulls.tipo_taxi == tipo, "pasajeros_nulos"].iloc[0])
        if len(category) == 1 and missing > 0:
            r = category.iloc[0]
            if int(r.pasajeros_nulos) == missing == int(r.registros):
                label = "pago nulo" if codigo is None else "pago 0 (Flex Fare)"
                pattern_notes.append(f"En {tipo}, todos los pasajeros nulos coinciden con la categoría {label}, y todos los registros de esa categoría tienen pasajeros nulos.")
    alerts = []
    for row in quality.to_dict(orient="records"):
        for key in ["fecha_fuera_mes_archivo", "duracion_negativa", "duracion_cero", "duracion_mayor_24h", "distancia_negativa", "distancia_cero", "distancia_mayor_100_millas", "pasajeros_no_positivos", "pasajeros_mayor_6", "total_negativo", "total_cero", "pago_codigo_no_documentado", "tarifa_codigo_no_documentado"]:
            alerts.append(f"| {row['tipo_taxi']} | {key} | {int(row[key]):,} | {100 * row[key] / row['registros']:.4f}% |")
    report = [
        "# Ejercicio 3: exploración directa de archivos Parquet",
        "Generado con DuckDB " + duckdb.__version__ + " el " + datetime.now(timezone.utc).isoformat() + " (UTC).",
        "## Alcance y reproducción",
        "Se consultan todos los Parquet descargados de taxis amarillos y verdes. Los patrones son `data/raw/yellow/*/*.parquet` y `data/raw/green/*/*.parquet`. La lista exacta de fuentes está en [el inventario](resultados_ejercicio_3/01_inventario.csv). El mes de archivo procede de su nombre; las fechas de los viajes se conservan sin corregir.",
        "```bash\ndocker compose exec -T lab python scripts/explore_parquet.py\n```",
        "También puede ejecutar todas las celdas de `notebooks/03_exploracion_parquet.ipynb` en JupyterLab. Ambos caminos utilizan los mismos SQL y generan los mismos CSV. Los resultados se actualizan al incorporar archivos nuevos; esta documentación refleja el conjunto disponible al ejecutar el análisis.",
        "## 3.1 y 3.2: archivos y registros",
        table(summary),
        f"Total: **{inventory['archivo'].nunique():,} archivos** y **{int(inventory['registros'].sum()):,} registros**, obtenidos con COUNT sobre las fuentes Parquet.",
        "## 3.3 y 3.4: columnas y tipos",
        table(fields),
        "Los detalles de cada archivo están en `02_esquemas.csv`; la firma ordenada de nombres y tipos está en `03_cambios_esquema.csv`. Se comparan nombres y tipos, no solo cantidades.",
        "Las columnas de fechas usan prefijos tpep en amarillos y lpep en verdes. La vista `viajes` les asigna los nombres `recogida` y `llegada`. En los archivos de 2026 explorados, request_source aparece desde junio; los meses anteriores reciben NULL al unir por nombre. Los campos exclusivos de un tipo (airport_fee, ehail_fee y trip_type) también se conservan como NULL para el otro tipo. Esos NULL estructurales no se contabilizan como problemas de calidad en la consulta 05.",
        "## 3.5: muestra",
        "La consulta 04 devuelve cinco filas por tipo, con su archivo de procedencia. El resultado completo está en el notebook y [04_muestras.csv](resultados_ejercicio_3/04_muestras.csv). LIMIT no genera una muestra aleatoria ni representativa.",
        "## 3.6: posibles problemas de calidad",
        "### Resultados e interpretación",
        "\n".join(findings),
        " ".join(pattern_notes) + " La consulta 08 permite revisar asociaciones entre nulos y categorías de pago. Una asociación observada no explica su causa: excluir todas las filas con pasajeros nulos puede cambiar la cobertura de modalidades. Por eso no se aplica una limpieza automática.",
        "Los rangos y percentiles deben revisarse antes de calcular promedios. Una recogida fuera del mes nominal necesita inspección, incluyendo posibles viajes alrededor del cambio de año. El cambio de esquema se registra como evolución de la fuente, no como corrupción de archivos.",
        "### Valores faltantes",
        table(nulls),
        "### Alertas y proporciones",
        "| Tipo | Alerta | Registros | Porcentaje del tipo |\n| --- | --- | --- | --- |\n" + "\n".join(alerts),
        "Las alertas se superponen; sumarlas no equivale a contar viajes únicos con problemas. Los nulos se cuentan por separado y no satisfacen las comparaciones numéricas. Los umbrales de 100 millas, 24 horas y 6 pasajeros se usan para inspección, no como restricciones oficiales ni filtros de limpieza.",
        "Una fecha fuera del mes del nombre necesita revisión; no prueba por sí sola un error. Una llegada anterior a la recogida produce duración negativa. Los ceros y los importes negativos requieren contexto (por ejemplo, los códigos de pago distinguen disputas y viajes anulados). No se atribuye una causa a cada importe negativo sin evidencia adicional. La consulta 08 permite examinarlos por tipo de pago y la 10 muestra ejemplos.",
        "## 3.7 y 3.8: documentación de consultas",
        "La preparación [00_fuentes.sql](../sql/exploracion/00_fuentes.sql) crea vistas raw y una vista con nombres armonizados. Todas son vistas en memoria sobre read_parquet; no se importa ni materializa el conjunto de viajes. UNION ALL conserva las filas. No se filtran, deduplican, imputan ni modifican los valores originales. Cada consulta siguiente usa las fuentes del inventario, directamente o mediante esas vistas.",
    ]
    for name, title, objective, decision in QUERY_SPECS:
        report.extend([
            "### " + name + ": " + title,
            "**Objetivo:** " + objective,
            "**Fuente:** los archivos enumerados en `01_inventario.csv`; `parquet_schema` lee metadatos en las consultas 02 y 03, y las demás consultan las vistas externas.",
            f"**SQL:** [{name}.sql](../sql/exploracion/{name}.sql). **Resultado:** [{name}.csv](resultados_ejercicio_3/{name}.csv), {len(frames[name]):,} filas de salida. El notebook muestra el SQL y su resultado.",
            "**Decisión:** " + decision,
        ])
    report.extend([
        "## 3.9: qué significa consultar Parquet directamente",
        "read_parquet permite que DuckDB ejecute SQL sobre archivos externos sin cargarlos previamente en una tabla. Las vistas guardan la definición de lectura y se evalúan al consultar. Parquet almacena columnas por grupos de filas; DuckDB puede leer solo columnas necesarias y aprovechar filtros y metadatos cuando la consulta lo permite. Así se evita copiar todo el conjunto a un DataFrame y se pueden incorporar nuevos archivos mediante patrones de rutas.",
        "Esto no significa que todas las consultas sean gratuitas: los perfiles de calidad y percentiles deben examinar valores, y filtros o agregaciones complejos pueden requerir CPU, memoria o disco temporal. Los CSV y DataFrames de este ejercicio contienen solo metadatos, agregados y muestras pequeñas.",
        "## Fuentes y límites de interpretación",
        "- [Documentación de DuckDB sobre Parquet](https://duckdb.org/docs/stable/data/parquet/overview).",
        "- [Catálogo oficial TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).",
        "- [Diccionario TLC de taxis amarillos](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf).",
        "- [Diccionario TLC de taxis verdes](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf).",
        "Los diccionarios consultados están fechados el 18 de marzo de 2025: documentan distancia en millas, códigos de pago 0–6 (incluido Flex Fare), tarifa 99 como desconocida y que las propinas en efectivo no se incluyen. No describen request_source; sus categorías se registran sin atribuirles significado no confirmado. La TLC advierte que no garantiza la exactitud de los datos. Estas comprobaciones no constituyen un análisis exhaustivo de duplicados ni una validación de zonas contra su catálogo.",
    ])
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    (output_dir.parent / "ejercicio_3_exploracion.md").write_text("\n\n".join(report) + "\n", encoding="utf-8")
    # Garantiza que la exploración no creó tablas materializadas de viajes.
    base_tables = connection.execute("SELECT count(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'").fetchone()[0]
    if base_tables:
        raise AssertionError("La exploración no debe materializar tablas de viajes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    import os
    os.chdir(ROOT)
    with create_connection() as connection:
        frames = {}
        for name, title, _, _ in QUERY_SPECS:
            print(f"Ejecutando {name}: {title}", flush=True)
            frames[name] = run_query(connection, name)
            print(f"  {len(frames[name])} filas de resultado", flush=True)
        write_report(connection, frames)
    print("Exploración completada: docs/ejercicio_3_exploracion.md", flush=True)


if __name__ == "__main__":
    main()
