"""Ejercicio 7: indicadores DuckDB y documentación de preguntas/interpretaciones."""
import argparse
import json
import os
import re
from pathlib import Path

import duckdb
import pandas as pd
from explore_parquet import ROOT, table

OUTPUT = ROOT / "docs" / "resultados_ejercicio_7" / "duckdb"


def render_sql(sql, year=2026, taxi="all"):
    def optional(match):
        block = match.group(1)
        if "{{anio}}" in block:
            return block.replace("{{anio}}", str(int(year))) if year is not None else ""
        if "{{tipo_taxi}}" in block:
            return block.replace("{{tipo_taxi}}", "'"+taxi.replace("'", "''")+"'") if taxi != "all" else ""
        raise ValueError("Bloque opcional no reconocido")
    return re.sub(r"\[\[(.*?)\]\]", optional, sql, flags=re.S)


def interpretation(key, frame):
    if key == "01_viajes":
        return f"Se observan {int(frame.iloc[0].viajes):,} viajes con fechas coherentes en la selección. Es volumen del período disponible, no una estimación anual."
    if key == "02_retencion":
        value=frame.iloc[0].porcentaje
        return f"El análisis de mediciones conserva {value:.2f}% de la población temporal; {100-value:.2f}% queda fuera de los criterios declarados. No implica que toda fila excluida sea un error."
    if key == "03_distancia":
        return f"La distancia mediana aproximada es {frame.iloc[0].mediana_millas:.2f} millas; alrededor de la mitad de la población filtrada queda por debajo de ese valor."
    if key == "04_total":
        return f"El total mediano aproximado es USD {frame.iloc[0].mediana_usd:.2f}. Describe el pago total de viajes filtrados, no el precio causal de elegir un tipo de taxi."
    sentences=[]
    for tipo in sorted(frame.tipo_taxi.unique()):
        d=frame.loc[frame.tipo_taxi==tipo]
        if key=="05_mensual":
            d=d.sort_values("mes")
            sentences.append(f"{tipo}: el índice diario del último mes disponible es {d.iloc[-1].indice_base100:.2f}, frente a 100 del primer mes. Es una variación relativa dentro del tipo.")
        elif key=="06_hora":
            row=d.loc[d.porcentaje.idxmax()]
            sentences.append(f"{tipo}: el máximo horario aparece a las {int(row.hora):02d}:00–{int(row.hora):02d}:59, con {row.porcentaje:.2f}% de los viajes del tipo.")
        elif key=="07_semana":
            row=d.loc[d.indice_base100.idxmax()]
            sentences.append(f"{tipo}: {row.dia_semana} tiene el mayor promedio diario, con índice {row.indice_base100:.2f}. Se ajusta por cuántas veces aparece cada día en el calendario.")
        elif key=="08_duracion":
            sentences.append(f"{tipo}: la duración mediana aproximada es {d.iloc[0].mediana_minutos:.2f} minutos. No se igualan rutas, horarios o tarifas entre tipos.")
        elif key=="09_distribucion":
            share=d.loc[d.intervalo.isin(['(0,1] mi','(1,2] mi','(2,5] mi']), 'porcentaje'].sum()
            sentences.append(f"{tipo}: {share:.2f}% de los viajes de mediciones tienen hasta 5 millas. La proporción no incluye distancias cero o fuera del rango declarado.")
        elif key=="10_pago":
            row=d.loc[d.porcentaje.idxmax()]
            sentences.append(f"{tipo}: {row.forma_pago} es la categoría mayor ({row.porcentaje:.2f}%). Flex Fare y Sin dato se mantienen separados de tarjeta/efectivo.")
        elif key=="11_propinas":
            row=d.iloc[0]
            sentences.append(f"{tipo}: mediana aproximada de propina/tarifa {row.tasa_mediana:.2f}% sobre {int(row.viajes_elegibles):,} viajes elegibles; {row.porcentaje_sin_propina:.2f}% tienen propina registrada cero. No representa propinas en efectivo.")
        elif key=="12_negativos":
            disputes=d.loc[d.forma_pago=='Disputa']
            if len(disputes):sentences.append(f"{tipo}: {disputes.iloc[0].porcentaje_negativo:.2f}% de los registros reportados como Disputa tienen total negativo. No se atribuye una causa a todo importe negativo.")
        elif key in ('14_demanda_comparable','15_efectivo_comparable','16_total_comparable'):
            metric={'14_demanda_comparable':'indice_2024','15_efectivo_comparable':'porcentaje_efectivo','16_total_comparable':'total_mediano_usd'}[key]
            ordered=d.sort_values('anio')
            sequence='; '.join(f"{r['anio']}: {r[metric]:.2f}" for r in ordered.to_dict(orient='records'))
            sentences.append(f"{tipo}: {sequence}. Se usan meses comunes de los tres años; esta comparación ignora el filtro de año. Los costos son nominales y sus medianas aproximadas; las diferencias no prueban causalidad.")
        elif key=="13_cobertura":
            for row in d.itertuples():sentences.append(f"{tipo}, {row.anio}: {int(row.meses)} meses y {int(row.registros):,} registros originales. Estos conteos incluyen fechas anómalas y pueden diferir del volumen temporal.")
    return ' '.join(sentences)


def build(year=2026, taxi="all"):
    config = json.loads((ROOT/"docs"/"tablero"/"indicadores.json").read_text())
    OUTPUT.mkdir(parents=True,exist_ok=True)
    frames = {}
    with duckdb.connect(str(ROOT/config.get("database_file", "data/processed/benchmark/completo.duckdb")),read_only=True) as connection:
        connection.execute("SET threads=4")
        scratch=ROOT/"data"/"processed"/"indicadores_temporales"/f"python_{os.getpid()}"
        scratch.mkdir(parents=True,exist_ok=True)
        connection.execute("SET temp_directory = "+"'"+str(scratch).replace("'","''")+"'")
        connection.execute("SET memory_limit='1GB'")
        for item in config["indicators"]:
            sql = render_sql((ROOT/item["sql"]).read_text(),year,taxi)
            frame = connection.execute(sql).fetchdf()
            frame.to_csv(OUTPUT/(item["key"]+".csv"),index=False)
            frames[item["key"]] = frame
            print("Indicador DuckDB:",item["key"],len(frame),"filas",flush=True)
    report = ["# Ejercicio 7: indicadores y tablero de viajes NYC",
        f"Trabajo individual. Resultados documentados para año {year}, tipo {taxi}.",
        "## Preguntas y diseño (7.1–7.3)",
        "Se definieron trece preguntas/indicadores, con SQL versionado y visualización en Metabase. La fuente es la tabla viajes_duckdb del archivo completo creado en el ejercicio 6 (2024 y 2026). El año corresponde al mes del archivo, no a fechas anómalas de recogida.",
        "**Poblaciones:** original = todas las filas seleccionadas por año/tipo; temporal = recogida dentro del mes del archivo; mediciones = además distancia (0,100] millas, duración (0,1440] minutos, total positivo y tarifa no negativa. No se filtran pasajeros ni pagos nulos. Propinas = mediciones, tarjeta, tarifa positiva y propina no negativa. Estos umbrales son exploratorios, no normas oficiales.",
        "**Filtros del tablero:** año (2026 inicial) y tipo (`yellow`/`green`, vacío para ambos). La cobertura ayuda a distinguir 2024 completo de 2026 parcial. Los índices mensual/semanal comparan perfiles relativos; no son conteos absolutos. Los CSV incluyen denominadores y valores absolutos para revisar su cálculo."]
    for item in config["indicators"]:
        name = item["key"]
        report += ["### "+name+": "+item["name"], "**Pregunta:** "+item["question"],
                   "**Justificación:** "+item["rationale"], "**Población:** "+item["population"]+". **Unidad:** "+item["unit"]+".",
                   f"**SQL:** [{name}.sql](../sql/indicadores/{name}.sql). **Resultado:** [CSV](resultados_ejercicio_7/duckdb/{name}.csv). **Visualización:** {item['display']}.", table(frames[name].round({c:3 for c in frames[name].select_dtypes(include='number').columns})), "**Interpretación de la selección:** "+interpretation(name,frames[name])]
    hourly = frames['06_hora']; payment = frames['10_pago']
    observations=[]
    for tipo in ('yellow','green'):
        d=hourly.loc[hourly.tipo_taxi==tipo]
        if len(d):
            peak=d.loc[d.porcentaje.idxmax()]
            observations.append(f"- {tipo}: la mayor proporción horaria aparece a las {int(peak.hora):02d}:00–{int(peak.hora):02d}:59 ({peak.porcentaje:.2f}% del tipo).")
        d=payment.loc[(payment.tipo_taxi==tipo)&(payment.forma_pago=='Efectivo')]
        if len(d):observations.append(f"- {tipo}: efectivo representa {d.iloc[0].porcentaje:.2f}% de los viajes temporales seleccionados; Sin dato y Flex Fare se conservan por separado.")
    report += ["## Interpretación y hallazgos (7.6–7.8)", "\n".join(observations),
               "Las medianas son aproximadas. Los importes negativos se muestran según la categoría reportada, sin asumir reembolso o error. Cero de propina significa cero registrado; no se generaliza a efectivo. El total incluye conceptos distintos de la tarifa base. Comparaciones entre años deben usar los mismos meses o declarar la cobertura; los datos disponibles no permiten extrapolar el año completo ni demostrar causalidad.",
               "## Tablero y reproducción (7.4–7.5)",
               "Los indicadores se organizan en tarjetas resumen, demanda temporal, características/pagos, propinas/alertas y cobertura. La configuración versionada está en [indicadores.json](tablero/indicadores.json).",
               "```bash\ndocker compose exec -T lab python scripts/build_indicators.py\n```",
               "Tras configurar Metabase, inicie sesión desde Terminal con `python scripts/metabase_dashboard.py --login`. La contraseña no se guarda; el token local se almacena en data/processed/, excluido de Git. Ejecute luego `python scripts/metabase_dashboard.py` para conectar la base en read_only, crear/actualizar las tarjetas, ejecutar sus consultas y montar el tablero.",
               "La instalación es repetible: guarda IDs locales para actualizar el mismo tablero. docs/tablero/metabase_evidencia.json registra el enlace y los IDs cuando termina; los resultados de Metabase se guardan aparte para verificar su procedencia. Hasta que exista esa evidencia no se da por terminado el tablero.",
               "Fuentes de interpretación: [diccionario amarillo TLC](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf) y [diccionario verde TLC](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf): distancia en millas, categorías de pago y exclusión de propinas en efectivo."]
    evidence_path=ROOT/'docs'/'tablero'/'metabase_evidencia.json'
    if evidence_path.exists():
        evidence=json.loads(evidence_path.read_text())
        report += ["## Evidencia del tablero instalado", f"[Abrir tablero Metabase]({evidence['url']}). {evidence['indicadores']} tarjetas verificadas con consultas ejecutadas en Metabase; conexión DuckDB read_only.",
                   "![Tablero: selección inicial 2026](tablero/captura_metabase.png)",
                   "![Tablero filtrado: 2024, taxis verdes](tablero/captura_2024_green.png)",
                   "Las capturas corresponden a visualizaciones reales de Metabase. Los JSON de resultados están en resultados_ejercicio_7/metabase/; las medianas aproximadas pueden variar ligeramente respecto a los valores de referencia calculados por Python."]
    (ROOT/'docs'/'ejercicio_7_indicadores.md').write_text('\n\n'.join(report)+'\n')
    return frames


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year',type=int,default=2026)
    parser.add_argument('--taxi',choices=['yellow','green','all'],default='all')
    args=parser.parse_args();os.chdir(ROOT);build(args.year,args.taxi)


if __name__=='__main__':main()
