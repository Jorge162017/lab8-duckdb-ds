"""Ejercicio 4: EDA sobre Parquet, gráficos e interpretación de resultados."""

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from explore_parquet import ROOT, create_connection, table

SQL_DIR = ROOT / "sql" / "eda"
OUTPUT_DIR = ROOT / "docs" / "resultados_ejercicio_4"
FIGURE_DIR = ROOT / "docs" / "figuras_ejercicio_4"
COLORS = {"yellow": "#b88700", "green": "#13806f"}
LABELS = {"yellow": "Amarillos", "green": "Verdes"}
QUERY_SPECS = [
    ("01_cobertura", "Cobertura y poblaciones", "¿Qué proporción de datos conserva cada población de análisis?",
     "Las alertas del ejercicio 3 requieren declarar denominadores y filtros antes de interpretar resultados.",
     "Todos los viajes originales.", "Las causas de exclusión pueden solaparse y no se suman para obtener filas únicas."),
    ("02_demanda_mensual", "Demanda mensual", "¿Cómo cambia el volumen mensual y el promedio diario de viajes?",
     "Los meses tienen distinta duración; comparar solo totales puede confundir calendario con demanda.",
     "Viajes con fechas coherentes con el archivo.", "La comparación principal usa viajes por día calendario; se informa también cuántos días presentan viajes."),
    ("03_demanda_horaria", "Demanda por hora", "¿A qué horas se concentran los viajes y difieren los perfiles entre taxis?",
     "Las marcas de recogida permiten detectar patrones de uso; los volúmenes de ambos tipos son muy distintos.",
     "Viajes con fechas coherentes con el archivo.", "Se comparan porcentajes dentro de cada tipo, no conteos sobre una escala dominada por amarillos."),
    ("04_demanda_semanal", "Demanda por día de semana", "¿Qué días de la semana presentan mayor demanda diaria promedio?",
     "Los días de semana no aparecen la misma cantidad de veces en el calendario disponible.",
     "Viajes con fechas coherentes con el archivo.", "Cada conteo se divide por las ocurrencias de ese día en los meses descargados; los posibles días sin viajes cuentan como cero."),
    ("05_perfil_viajes", "Características de los viajes", "¿Cómo difieren distancia, duración y total pagado entre amarillos y verdes?",
     "Los extremos observados en el ejercicio 3 aconsejan contrastar medias con medianas y percentiles.",
     "Viajes con fechas y mediciones válidas.", "Los percentiles son aproximados; las diferencias describen este subconjunto y no prueban una causa."),
    ("06_distribuciones", "Distribuciones", "¿Predominan los viajes cortos y cómo se distribuyen duraciones y pagos?",
     "Una media no muestra la concentración ni la cola de la distribución.",
     "Viajes con fechas y mediciones válidas.", "Los intervalos se fijan explícitamente y sus porcentajes usan el total de cada tipo y variable."),
    ("07_costo_distancia", "Costo según distancia", "¿Cómo cambia el total mediano según el intervalo de distancia?",
     "Distancia y total pueden estar asociados, pero el total incluye conceptos adicionales a la tarifa base.",
     "Viajes con fechas y mediciones válidas.", "No se interpreta como efecto causal ni como tarifa por milla; los intervalos largos pueden tener pocos viajes."),
    ("08_formas_pago", "Formas de pago", "¿Qué modalidades de pago predominan y qué diferencias aparecen entre tipos?",
     "La exploración encontró Flex Fare y pagos nulos; eliminarlos alteraría la composición observada.",
     "Viajes con fechas coherentes con el archivo.", "Se conservan Flex Fare y Sin dato. Una categoría ausente no equivale a efectivo ni a tarjeta."),
    ("09_propinas_tarjeta", "Propinas registradas en tarjeta", "¿Cómo difieren las propinas registradas en los viajes pagados con tarjeta?",
     "Los diccionarios TLC indican que las propinas en efectivo no se registran.",
     "Mediciones válidas, payment_type=1, fare_amount>0 y tip_amount>=0.", "La tasa es propina/tarifa base por viaje. No representa todas las propinas ni se compara con efectivo."),
    ("10_importes_negativos", "Importes negativos y pagos", "¿En qué formas de pago aparecen totales negativos y qué proporción representan?",
     "El signo negativo requiere contexto; los códigos de pago incluyen disputas y viajes sin cargo.",
     "Viajes con fechas coherentes con el archivo, incluidos los importes negativos.", "Se informa la proporción negativa dentro de cada categoría sin atribuir automáticamente su causa."),
    ("11_sensibilidad", "Sensibilidad a los filtros", "¿Cuánto cambian las medias al aplicar los filtros de medición?",
     "El subconjunto filtrado cambia la cobertura y puede modificar las conclusiones.",
     "Comparación entre fechas válidas y fechas+mediciones válidas.", "Cambian varios criterios simultáneamente; no se atribuye toda la diferencia a un único filtro."),
]


def create_eda_connection():
    connection = create_connection()
    connection.execute((SQL_DIR / "00_poblaciones.sql").read_text())
    return connection


def run_query(connection, name):
    frame = connection.execute((SQL_DIR / (name + ".sql")).read_text()).fetchdf()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_DIR / (name + ".csv"), index=False)
    return frame


def plot_results(frames):
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figures = {}
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    def save(fig, name, title):
        fig.suptitle(title, fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, .94))
        path = FIGURE_DIR / (name + ".png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        figures[name] = path

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, tipo in zip(axes, ("yellow", "green")):
        d = frames["02_demanda_mensual"].query("tipo_taxi == @tipo")
        ax.plot(pd.to_datetime(d.mes_archivo).dt.strftime("%Y-%m"), d.viajes_por_dia, marker="o", color=COLORS[tipo])
        ax.set(title=LABELS[tipo], ylabel="Viajes por día calendario", xlabel="Mes del archivo")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=.2)
    save(fig, "02_demanda_mensual", "Demanda mensual — fechas válidas; escalas verticales independientes")

    fig, ax = plt.subplots(figsize=(9, 4))
    for tipo in ("yellow", "green"):
        d = frames["03_demanda_horaria"].query("tipo_taxi == @tipo")
        ax.plot(d.hora, d.porcentaje_tipo, label=LABELS[tipo], color=COLORS[tipo], marker=".")
    ax.set(xlabel="Hora de recogida registrada (sin conversión de zona)", ylabel="% de viajes del tipo")
    ax.set_xticks(range(0, 24, 2)); ax.legend(); ax.grid(alpha=.2)
    save(fig, "03_demanda_horaria", "Perfil horario — fechas válidas")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    weekdays = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for ax, tipo in zip(axes, ("yellow", "green")):
        d = frames["04_demanda_semanal"].query("tipo_taxi == @tipo")
        ax.bar([weekdays[int(x)-1] for x in d.dia_semana], d.viajes_por_dia, color=COLORS[tipo])
        ax.set(title=LABELS[tipo], ylabel="Viajes por ocurrencia del día")
        ax.grid(axis="y", alpha=.2)
    save(fig, "04_demanda_semanal", "Demanda semanal — fechas válidas; escalas verticales independientes")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, variable, label in zip(axes, ("distancia_millas", "duracion_minutos", "total_usd"), ("Distancia (millas)", "Duración (minutos)", "Total (USD)")):
        d = frames["06_distribuciones"].query("variable == @variable")
        categories = d[["orden", "intervalo"]].drop_duplicates().sort_values("orden").intervalo.tolist()
        for j, tipo in enumerate(("yellow", "green")):
            vals = d.query("tipo_taxi == @tipo").set_index("intervalo").porcentaje.reindex(categories, fill_value=0)
            ax.bar([i + (j-.5)*.36 for i in range(len(categories))], vals, width=.36, label=LABELS[tipo], color=COLORS[tipo])
        ax.set_xticks(range(len(categories)), categories, rotation=45, ha="right")
        ax.set(title=label, ylabel="% del tipo en el subconjunto")
        ax.grid(axis="y", alpha=.2)
    axes[0].legend()
    save(fig, "06_distribuciones", "Distribuciones — fechas y mediciones válidas")

    fig, ax = plt.subplots(figsize=(9, 4))
    for tipo in ("yellow", "green"):
        d = frames["07_costo_distancia"].query("tipo_taxi == @tipo")
        ax.plot(d.intervalo_millas, d.total_mediano_usd, label=LABELS[tipo], marker="o", color=COLORS[tipo])
    ax.set(xlabel="Intervalo de distancia (millas)", ylabel="Total mediano aproximado (USD)")
    ax.legend(); ax.grid(alpha=.2)
    save(fig, "07_costo_distancia", "Costo según distancia — fechas y mediciones válidas")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, tipo in zip(axes, ("yellow", "green")):
        d = frames["08_formas_pago"].query("tipo_taxi == @tipo").sort_values("porcentaje_tipo")
        ax.barh(d.forma_pago, d.porcentaje_tipo, color=COLORS[tipo])
        ax.set(title=LABELS[tipo], xlabel="% de viajes del tipo", xlim=(0, 100))
        ax.grid(axis="x", alpha=.2)
    save(fig, "08_formas_pago", "Formas de pago — fechas válidas; nulos conservados")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    d = frames["09_propinas_tarjeta"].set_index("tipo_taxi").reindex(["yellow", "green"])
    names = [LABELS[t] for t in d.index]
    colors = [COLORS[t] for t in d.index]
    axes[0].bar(names, d.porcentaje_sin_propina, color=colors)
    axes[0].set(ylabel="% de viajes elegibles", title="Sin propina registrada")
    axes[1].bar(names, d.tasa_mediana_porcentaje, color=colors)
    axes[1].set(ylabel="% de la tarifa base", title="Tasa mediana aproximada")
    for ax in axes: ax.grid(axis="y", alpha=.2)
    save(fig, "09_propinas_tarjeta", "Propinas — solo tarjeta con mediciones válidas y tarifa positiva")
    return figures


def findings(frames):
    texts = []
    monthly = frames["02_demanda_mensual"]
    hourly = frames["03_demanda_horaria"]
    weekly = frames["04_demanda_semanal"]
    profiles = frames["05_perfil_viajes"].set_index("tipo_taxi")
    payment = frames["08_formas_pago"]
    days = {1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves", 5: "viernes", 6: "sábado", 7: "domingo"}
    for tipo in ("yellow", "green"):
        d = monthly.query("tipo_taxi == @tipo")
        maximum, minimum = d.loc[d.viajes_por_dia.idxmax()], d.loc[d.viajes_por_dia.idxmin()]
        texts.append(f"**Demanda mensual, {LABELS[tipo].lower()}:** el máximo diario medio aparece en {pd.Timestamp(maximum.mes_archivo):%Y-%m}, con {maximum.viajes_por_dia:,.2f} viajes/día; el mínimo en {pd.Timestamp(minimum.mes_archivo):%Y-%m}, con {minimum.viajes_por_dia:,.2f}. La diferencia máximo/mínimo es {100 * (maximum.viajes_por_dia / minimum.viajes_por_dia - 1):.2f}%. Se comparan promedios diarios, no meses de igual duración. Fuente: consulta 02; no demuestra estacionalidad recurrente con un solo tramo temporal.")
        h = hourly.query("tipo_taxi == @tipo")
        peak = h.loc[h.porcentaje_tipo.idxmax()]
        evening = h.loc[h.hora.between(17, 20), "porcentaje_tipo"].sum()
        w = weekly.query("tipo_taxi == @tipo")
        week_peak = w.loc[w.viajes_por_dia.idxmax()]
        texts.append(f"**Patrón temporal, {LABELS[tipo].lower()}:** la hora con mayor proporción es {int(peak.hora):02d}:00–{int(peak.hora):02d}:59 ({peak.porcentaje_tipo:.2f}% del tipo); las horas 17–20 concentran {evening:.2f}%. {days[int(week_peak.dia_semana)].capitalize()} presenta el mayor promedio semanal, {week_peak.viajes_por_dia:,.2f} viajes por ocurrencia del día. Fuente: consultas 03–04; los calendarios están normalizados, pero no se controla por eventos o composición mensual.")
    y, g = profiles.loc["yellow"], profiles.loc["green"]
    texts.append(f"**Diferencias en características:** las medianas aproximadas de distancia son {y.distancia_mediana_millas:.2f} millas en amarillos y {g.distancia_mediana_millas:.2f} en verdes; las duraciones medianas, {y.duracion_mediana_minutos:.2f} y {g.duracion_mediana_minutos:.2f} minutos; los totales medianos, USD {y.total_mediano_usd:.2f} y USD {g.total_mediano_usd:.2f}. Fuente: consulta 05, solo mediciones válidas. No se igualan rutas, tarifas ni horarios, por lo que no se interpreta como diferencia causal de precio entre servicios.")
    distributions = frames["06_distribuciones"]
    short_trips = []
    for tipo in ("yellow", "green"):
        d = distributions.query("tipo_taxi == @tipo and variable == 'distancia_millas'")
        proportion = d.loc[d.orden <= 3, "porcentaje"].sum()
        short_trips.append(f"{LABELS[tipo].lower()}: {proportion:.2f}%")
    texts.append("**Concentración de distancias:** los viajes de hasta 5 millas representan " + "; ".join(short_trips) + ". Fuente: consulta 06, subconjunto de mediciones válidas. La concentración en distancias cortas coexiste con una cola de viajes largos; estos porcentajes no incluyen distancia cero ni mediciones descartadas.")
    payment_text = []
    for tipo in ("yellow", "green"):
        d = payment.query("tipo_taxi == @tipo")
        dominant = d.loc[d.porcentaje_tipo.idxmax()]
        cash = d.loc[d.payment_type == 2, "porcentaje_tipo"].sum()
        special = d.loc[(d.payment_type == 0) | d.payment_type.isna(), "porcentaje_tipo"].sum()
        payment_text.append(f"{LABELS[tipo]}: {dominant.forma_pago} representa {dominant.porcentaje_tipo:.2f}%, efectivo {cash:.2f}% y Flex Fare o Sin dato {special:.2f}%")
    texts.append("**Composición de pagos:** " + "; ".join(payment_text) + ". Fuente: consulta 08, fechas válidas. Flex Fare y Sin dato son categorías distintas y sus porcentajes no se reasignan a tarjeta/efectivo.")
    for row in frames["09_propinas_tarjeta"].itertuples():
        texts.append(f"**Propinas de tarjeta, {LABELS[row.tipo_taxi].lower()}:** sobre {row.viajes_tarjeta_elegibles:,} viajes elegibles, {row.porcentaje_sin_propina:.2f}% tienen propina registrada cero; la mediana aproximada de propina/tarifa base es {row.tasa_mediana_porcentaje:.2f}%. Fuente: consulta 09. No se generaliza a efectivo ni a todos los viajes; cero significa cero registrado, no prueba ausencia de otras propinas.")
    negatives = frames["10_importes_negativos"]
    for tipo in ("yellow", "green"):
        d = negatives.query("tipo_taxi == @tipo")
        disputes = d.loc[d.payment_type == 4]
        if len(disputes):
            row = disputes.iloc[0]
            total = d.totales_negativos.sum()
            share = 100 * row.totales_negativos / total if total else 0
            texts.append(f"**Importes negativos, {LABELS[tipo].lower()}:** {int(row.totales_negativos):,} negativos están en pago tipo 4 (Disputa), equivalentes a {share:.2f}% de los negativos del tipo. Dentro de esa categoría, {row.porcentaje_negativo_categoria:.2f}% son negativos. Fuente: consulta 10. Es una asociación con la categoría reportada, no evidencia de que todo negativo sea un reembolso o error.")
    sensitivity = frames["11_sensibilidad"]
    for tipo in ("yellow", "green"):
        d = sensitivity.query("tipo_taxi == @tipo")
        before = d.loc[d.poblacion == "Fechas válidas, sin filtros de medición"].iloc[0]
        after = d.loc[d.poblacion == "Fechas y mediciones válidas"].iloc[0]
        texts.append(f"**Sensibilidad, {LABELS[tipo].lower()}:** la distancia media pasa de {before.distancia_media_millas:.2f} a {after.distancia_media_millas:.2f} millas, conservando {100 * after.viajes / before.viajes:.2f}% de los viajes con fechas válidas. Fuente: consulta 11. Los filtros cambian a la vez distancia, duración e importes; la diferencia no se atribuye exclusivamente a distancias extremas.")
    return texts


def write_report(frames, figures):
    coverage = frames["01_cobertura"].copy()
    coverage["porcentaje_mediciones_sobre_original"] = 100 * coverage.mediciones_validas / coverage.registros_originales
    months = sorted(pd.to_datetime(frames["02_demanda_mensual"].mes_archivo).dt.strftime("%Y-%m").unique())
    report = [
        "# Ejercicio 4: análisis exploratorio con DuckDB",
        "Trabajo individual. Generado el " + datetime.now(timezone.utc).isoformat() + " (UTC).",
        "## Alcance y reproducción",
        "Meses disponibles: " + ", ".join(months) + ". Se analizan los archivos del inventario del ejercicio 3. Los meses no publicados no se representan como cero viajes y no se extrapola el año completo.",
        "```bash\ndocker compose exec -T lab python scripts/analyze_trips.py\n```",
        "También puede ejecutar `notebooks/04_analisis_exploratorio.ipynb` completo en JupyterLab. Ambos métodos usan los SQL de `sql/eda/`, producen CSV en `docs/resultados_ejercicio_4/` y gráficos en `docs/figuras_ejercicio_4/`. Se sigue consultando Parquet mediante vistas en memoria; no se materializan los viajes ni se cargan completos en Pandas.",
        "## Poblaciones y decisiones de calidad",
        "1. **Original:** todas las filas descargadas. 2. **Fechas válidas:** la recogida pertenece al mes del nombre del archivo. Es la población de demanda, modalidades de pago e importes negativos. 3. **Mediciones válidas:** además, 0 < distancia <= 100 millas, 0 < duración <= 1440 minutos, total > 0 y tarifa base >= 0. Se utiliza para perfiles, distribuciones y costo por distancia. La tasa de propina agrega tarjeta, tarifa base positiva y propina no negativa.",
        "Son filtros exploratorios, no límites oficiales ni correcciones de la fuente. Los Parquet permanecen intactos. No se excluyen filas por pasajeros nulos o pago nulo. La duración se calcula en segundos y se expresa en minutos; las marcas de tiempo se conservan sin convertir de zona horaria. Las alertas por criterio se solapan. La consulta 11 mide sensibilidad al conjunto de filtros, sin aislar causalmente cada criterio.",
        table(coverage.round(4)),
        "## Hallazgos respaldados por resultados (4.5)",
    ]
    report += [f"{i}. {text}" for i, text in enumerate(findings(frames), 1)]
    report.append("## Preguntas, SQL, resultados e interpretación (4.1–4.4)")
    for name, title, question, rationale, population, decision in QUERY_SPECS:
        report.extend([
            "### " + name + ": " + title,
            "**Pregunta:** " + question,
            "**Justificación:** " + rationale,
            "**Población y fuente:** " + population + " Archivos del [inventario](resultados_ejercicio_3/01_inventario.csv), mediante las vistas de [00_fuentes.sql](../sql/exploracion/00_fuentes.sql) y [00_poblaciones.sql](../sql/eda/00_poblaciones.sql).",
            f"**Consulta:** [{name}.sql](../sql/eda/{name}.sql). **Resultado completo:** [{name}.csv](resultados_ejercicio_4/{name}.csv), {len(frames[name])} filas de salida.",
            "**Interpretación y límites:** " + decision,
        ])
        if name in ("01_cobertura", "02_demanda_mensual", "04_demanda_semanal", "05_perfil_viajes", "07_costo_distancia", "08_formas_pago", "09_propinas_tarjeta", "10_importes_negativos", "11_sensibilidad"):
            display_frame = frames[name].copy()
            for column in display_frame.select_dtypes(include="number").columns:
                display_frame[column] = display_frame[column].round(4)
            report.append(table(display_frame))
        if name in figures:
            report.append(f"![{title}](figuras_ejercicio_4/{name}.png)")
    report.extend([
        "## Límites generales y fuentes",
        "Las medianas y percentiles son aproximados. Los SQL sin ORDER BY antes de funciones aproximadas pueden presentar pequeñas diferencias entre ejecuciones por procesamiento paralelo. No se consideran inferencias causales, significancia estadística, ajuste por rutas ni corrección por inflación. El período observado no permite probar patrones anuales recurrentes. Se conservan los pagos ausentes y Flex Fare; no se atribuye significado a request_source sin un diccionario confirmado.",
        "Los importes se expresan en USD y las distancias en millas. El total incluye más conceptos que la tarifa base. Los diccionarios TLC describen los códigos de pago y advierten que las propinas en efectivo no están incluidas; por eso la comparación de propinas se limita a tarjeta.",
        "- [Diccionario TLC amarillo](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf).",
        "- [Diccionario TLC verde](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf).",
        "- [Catálogo TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).",
        "- [DuckDB: lectura de Parquet](https://duckdb.org/docs/stable/data/parquet/overview).",
        "El análisis entrega más de tres hallazgos y cubre comportamiento temporal, características de viajes, diferencias entre taxis, pagos, distribuciones y atípicos. El tablero y la ampliación de años corresponden a ejercicios posteriores.",
    ])
    (ROOT / "docs" / "ejercicio_4_analisis.md").write_text("\n\n".join(report) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    os.chdir(ROOT)
    with create_eda_connection() as connection:
        frames = {}
        for name, title, *_ in QUERY_SPECS:
            print(f"Ejecutando {name}: {title}", flush=True)
            frames[name] = run_query(connection, name)
        figures = plot_results(frames)
        write_report(frames, figures)
    print("Análisis completado: docs/ejercicio_4_analisis.md", flush=True)


if __name__ == "__main__":
    main()
