"""Ejercicio 6: benchmark reproducible de Parquet frente a tablas DuckDB."""

import argparse
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from explore_parquet import ROOT, table

SQL_DIR = ROOT / "sql" / "benchmark"
OUTPUT_DIR = ROOT / "docs" / "resultados_ejercicio_6"
FIGURE_DIR = ROOT / "docs" / "figuras_ejercicio_6"
DATABASE_DIR = ROOT / "data" / "processed" / "benchmark"
STRATEGIES = {"parquet": "viajes_parquet", "duckdb": "viajes_duckdb"}
QUERY_SPECS = [
    ("01_conteo", "Conteo por taxi", "Inventario de registros; algunos conteos pueden aprovechar metadatos.", "Ejercicio 3: inventario."),
    ("02_demanda_mensual", "Demanda mensual", "Agrupación temporal con el mismo criterio de fechas válidas del EDA.", "Ejercicio 4: demanda mensual."),
    ("03_formas_pago", "Formas de pago", "Agrupación categórica y conteo condicional de importes negativos.", "Ejercicio 4: modalidades de pago e importes negativos."),
    ("04_caracteristicas", "Características", "Filtros de calidad y medias de distancia, duración y total; evita percentiles aproximados para verificar equivalencia.", "Ejercicio 4: perfil de viajes y sensibilidad."),
    ("05_filtro_fecha_zona", "Fecha y zona", "Filtro selectivo en una semana fija de enero de 2024, con agrupación por zona y tipo.", "Ejercicio 4: análisis temporal, distancia y pagos."),
]


def serialize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def source_sql(level):
    sql = (ROOT / "sql" / "exploracion" / "00_fuentes.sql").read_text()
    for tipo in ("yellow", "green"):
        paths = [p for p in level["archivos"] if Path(p).parts[2] == tipo]
        if not paths:
            raise ValueError("Cada nivel debe incluir ambos tipos de taxi")
        sql = sql.replace(sql_string(f"data/raw/{tipo}/*/*.parquet"),
                          "[" + ", ".join(sql_string(p) for p in paths) + "]")
    return sql.replace("CREATE OR REPLACE VIEW", "CREATE OR REPLACE TEMP VIEW").replace("VIEW viajes AS", "VIEW viajes_parquet AS")


def fingerprint(level):
    results = []
    for name in level["archivos"]:
        path = ROOT / name
        stat = path.stat()
        results.append({"ruta": name, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    if sum(r["bytes"] for r in results) != level["bytes_parquet"]:
        raise ValueError("Cambió el tamaño de los archivos desde la preparación del ejercicio 5")
    return results


def configure(connection, args):
    connection.execute(f"SET threads = {args.threads}")
    connection.execute("SET memory_limit = " + sql_string(args.memory_limit))
    scratch = DATABASE_DIR / "temporales"
    scratch.mkdir(parents=True, exist_ok=True)
    connection.execute("SET temp_directory = " + sql_string(scratch))


def materialize(level, args):
    name = level["nombre"]
    target = DATABASE_DIR / (name + ".duckdb")
    meta_path = DATABASE_DIR / (name + "_materializacion.json")
    sources = fingerprint(level)
    sql = source_sql(level)
    sql_hash = hashlib.sha256(sql.encode()).hexdigest()
    if args.reuse_materialized:
        metadata = json.loads(meta_path.read_text())
        if metadata["fuentes"] != sources or metadata["sql_fuente_sha256"] != sql_hash:
            raise ValueError("La base no corresponde a los Parquet actuales; repita sin --reuse-materialized")
        if not target.exists() or target.stat().st_size != metadata["bytes_duckdb"]:
            raise ValueError("La base materializada cambió o no existe")
        return metadata
    if target.exists() and not meta_path.exists():
        raise FileExistsError("No se reemplazará una base sin metadatos de este benchmark")
    building = DATABASE_DIR / (name + f".building_{os.getpid()}.duckdb")
    if building.exists():
        raise FileExistsError("Ya existe el archivo temporal de esta ejecución")
    print(f"Materializando {name}: {level['registros']:,} registros", flush=True)
    start = time.perf_counter()
    connection = duckdb.connect(str(building))
    try:
        configure(connection, args)
        connection.execute(sql)
        prepared = time.perf_counter()
        commands = (SQL_DIR / "00_materializar.sql").read_text().split("CHECKPOINT;")
        connection.execute(commands[0])
        created = time.perf_counter()
        connection.execute("CHECKPOINT")
        checkpointed = time.perf_counter()
        count = connection.execute("SELECT count(*) FROM viajes_duckdb").fetchone()[0]
        if count != level["registros"]:
            raise AssertionError("La tabla materializada no coincide con el inventario")
    finally:
        connection.close()
    building.replace(target)
    metadata = {"nivel": name, "database": str(target.relative_to(ROOT)),
                "registros": count, "cantidad_archivos": len(sources),
                "bytes_parquet": level["bytes_parquet"], "bytes_duckdb": target.stat().st_size,
                "preparacion_s": prepared-start, "creacion_tabla_s": created-prepared,
                "checkpoint_s": checkpointed-created,
                "materializacion_s": checkpointed-start,
                "sql_fuente_sha256": sql_hash, "fuentes": sources,
                "fecha_utc": datetime.now(timezone.utc).isoformat()}
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"  Persistida: {metadata['materializacion_s']:.2f} s; {metadata['bytes_duckdb'] / 1024**2:.1f} MiB", flush=True)
    return metadata


def execute(connection, sql):
    start = time.perf_counter()
    cursor = connection.execute(sql)
    rows = cursor.fetchall()
    elapsed = time.perf_counter()-start
    description = [(col[0], str(col[1])) for col in cursor.description]
    return elapsed, rows, description


def compare(expected, actual):
    if len(expected) != len(actual):
        raise AssertionError("Distinta cantidad de filas de resultado")
    for left, right in zip(expected, actual):
        if len(left) != len(right):
            raise AssertionError("Distinta cantidad de columnas")
        for a, b in zip(left, right):
            if isinstance(a, float) or isinstance(b, float):
                if a is None or b is None:
                    if a is not None or b is not None:
                        raise AssertionError("NULL no coincide")
                elif math.isnan(a) and math.isnan(b):
                    continue
                elif not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-8):
                    raise AssertionError(f"Valores numéricos distintos: {a} / {b}")
            elif a != b:
                raise AssertionError(f"Resultados distintos: {a} / {b}")


def run_level(level, metadata, args, rng):
    name = level["nombre"]
    with duckdb.connect(str(ROOT / metadata["database"]), read_only=True) as connection:
        configure(connection, args)
        connection.execute(source_sql(level))
        schema_p = connection.execute("DESCRIBE viajes_parquet").fetchall()
        schema_d = connection.execute("DESCRIBE viajes_duckdb").fetchall()
        # Restricciones de nulabilidad no son parte del esquema analítico; nombre y tipo sí.
        if [(r[0], r[1]) for r in schema_p] != [(r[0], r[1]) for r in schema_d]:
            raise AssertionError("Los esquemas lógicos difieren")
        queries = {name_: (SQL_DIR / (name_ + ".sql")).read_text() for name_, *_ in QUERY_SPECS}
        plan_dir = OUTPUT_DIR / "planes" / name
        result_dir = OUTPUT_DIR / "resultados_consultas" / name
        plan_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)
        references = {}
        descriptions = {}
        warmups, validations, timings = [], [], []
        # Orden reproducible, alternado en cada par; no hay ejecución simultánea.
        query_order = list(queries)
        rng.shuffle(query_order)
        for query_index, query in enumerate(query_order):
            for warmup in range(args.warmups):
                order = ["parquet", "duckdb"] if (query_index+warmup) % 2 == 0 else ["duckdb", "parquet"]
                current = {}
                for strategy in order:
                    sql = queries[query].replace("{{fuente}}", STRATEGIES[strategy])
                    elapsed, rows, description = execute(connection, sql)
                    current[strategy] = rows, description
                    warmups.append({"nivel": name, "consulta": query, "estrategia": strategy,
                                    "calentamiento": warmup+1, "segundos": elapsed})
                if current["parquet"][1] != current["duckdb"][1]:
                    raise AssertionError("El esquema del resultado difiere")
                compare(current["parquet"][0], current["duckdb"][0])
                references[query] = current["parquet"][0]
                descriptions[query] = current["parquet"][1]
            if query == "01_conteo" and sum(row[1] for row in references[query]) != level["registros"]:
                raise AssertionError("El conteo de consulta difiere del inventario")
            validations.append({"nivel": name, "consulta": query,
                                "filas_resultado": len(references[query]), "esquema_igual": True,
                                "resultados_equivalentes": True, "verificaciones_medidas": args.repetitions * 2})
            for strategy in STRATEGIES:
                sql = queries[query].replace("{{fuente}}", STRATEGIES[strategy])
                pd.DataFrame(current[strategy][0], columns=[r[0] for r in descriptions[query]]).to_csv(result_dir / (query + "_" + strategy + ".csv"), index=False)
                plans = connection.execute("EXPLAIN " + sql).fetchall()
                (plan_dir / (query + "_" + strategy + ".txt")).write_text("\n".join(str(p[-1]) for p in plans).rstrip() + "\n")
        # Intercala consultas y alterna qué estrategia va primero en cada ronda.
        for repetition in range(args.repetitions):
            order_queries = list(queries)
            rng.shuffle(order_queries)
            for query_index, query in enumerate(order_queries):
                order = ["parquet", "duckdb"] if (repetition+query_index) % 2 == 0 else ["duckdb", "parquet"]
                for position, strategy in enumerate(order, 1):
                    sql = queries[query].replace("{{fuente}}", STRATEGIES[strategy])
                    elapsed, rows, description = execute(connection, sql)
                    if description != descriptions[query]:
                        raise AssertionError("Cambió el esquema durante las mediciones")
                    compare(references[query], rows)
                    timings.append({"nivel": name, "registros": level["registros"],
                                    "consulta": query, "estrategia": strategy,
                                    "repeticion": repetition+1, "posicion_par": position,
                                    "segundos": elapsed, "filas_resultado": len(rows),
                                    "equivalencia_ok": True})
            print(f"  {name}: ronda {repetition+1}/{args.repetitions} completada", flush=True)
    if fingerprint(level) != metadata["fuentes"]:
        raise AssertionError("Los Parquet cambiaron durante el benchmark")
    return timings, warmups, validations


def summarize(raw):
    summary = raw.groupby(["nivel", "registros", "consulta", "estrategia"], sort=False).segundos.agg(
        repeticiones="count", mediana_s="median", media_s="mean", minimo_s="min", maximo_s="max", desviacion_s="std"
    ).reset_index()
    comparison = summary.pivot(index=["nivel", "registros", "consulta"], columns="estrategia", values="mediana_s").reset_index()
    comparison.columns.name = None
    comparison = comparison.rename(columns={"parquet": "parquet_mediana_s", "duckdb": "duckdb_mediana_s"})
    comparison["razon_parquet_duckdb"] = comparison.parquet_mediana_s / comparison.duckdb_mediana_s
    comparison["menor_mediana"] = comparison.apply(lambda r: "duckdb" if r.duckdb_mediana_s < r.parquet_mediana_s else "parquet", axis=1)
    return summary, comparison


def environment(args):
    def read(path):
        p = Path(path)
        return p.read_text().strip() if p.exists() else None
    return {"fecha_utc": datetime.now(timezone.utc).isoformat(), "duckdb": duckdb.__version__,
            "python": sys.version.split()[0], "sistema": platform.platform(),
            "arquitectura": platform.machine(), "cpus_visibles": os.cpu_count(),
            "cgroup_memory_max": read("/sys/fs/cgroup/memory.max"),
            "cgroup_cpu_max": read("/sys/fs/cgroup/cpu.max"),
            "threads": args.threads, "memory_limit": args.memory_limit,
            "repeticiones": args.repetitions, "calentamientos": args.warmups,
            "semilla": args.seed, "conexion_mediciones": "read_only, una por nivel y ambas estrategias",
            "caches": "un calentamiento mínimo; no se vacían cachés del SO; materialización previa lee los Parquet",
            "temporizador": "perf_counter; execute y fetchall; excluye comparación, CSV, EXPLAIN y materialización",
            "tolerancia": {"enteros_y_categorias": "exacta", "flotantes_rtol": 1e-9, "flotantes_atol": 1e-8},
            "orden": "consultas barajadas por ronda; estrategias alternadas por par; secuencial",
            "otros_servicios": "Jupyter, Metabase y otros contenedores pueden permanecer activos; no se aísla toda carga del host"}


def make_outputs(raw, warmups, validations, materializations, metadata):
    summary, comparison = summarize(raw)
    for name, frame in (("tiempos", raw), ("calentamientos", warmups), ("equivalencia", validations),
                        ("materializacion", materializations), ("resumen", summary), ("comparacion", comparison)):
        frame.to_csv(OUTPUT_DIR / (name + ".csv"), index=False)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    level_order = materializations.nivel.tolist()
    titles = {q: title for q, title, *_ in QUERY_SPECS}
    fig, axes = plt.subplots(1, len(level_order), figsize=(6*len(level_order), 4), squeeze=False)
    for ax, level in zip(axes[0], level_order):
        d = comparison.query("nivel == @level").sort_values("consulta")
        x = list(range(len(d)))
        ax.bar([v-.18 for v in x], d.parquet_mediana_s*1000, width=.36, label="Parquet", color="#3877b5")
        ax.bar([v+.18 for v in x], d.duckdb_mediana_s*1000, width=.36, label="Tabla DuckDB", color="#13806f")
        ax.set_xticks(x, [q[:2] for q in d.consulta])
        ax.set(title=level, xlabel="Consulta (ver leyenda SQL)", ylabel="Mediana de tiempo (ms), escala log")
        ax.set_yscale("log"); ax.grid(axis="y", alpha=.2); ax.legend()
    fig.suptitle("Parquet frente a tabla materializada — ejecuciones recurrentes")
    fig.tight_layout(); fig.savefig(FIGURE_DIR / "tiempos_por_volumen.png", dpi=150, bbox_inches="tight"); plt.close(fig)
    fig, axes = plt.subplots(1, len(QUERY_SPECS), figsize=(18, 4), squeeze=False)
    for ax, (query, title, *_) in zip(axes[0], QUERY_SPECS):
        d = comparison.query("consulta == @query").sort_values("registros")
        ax.plot(d.registros/1e6, d.parquet_mediana_s, marker="o", label="Parquet", color="#3877b5")
        ax.plot(d.registros/1e6, d.duckdb_mediana_s, marker="o", label="Tabla DuckDB", color="#13806f")
        ax.set(title=title, xlabel="Millones de registros", ylabel="Mediana (s)")
        ax.grid(alpha=.2)
    axes[0,0].legend(); fig.tight_layout(); fig.savefig(FIGURE_DIR / "escalabilidad.png", dpi=150, bbox_inches="tight"); plt.close(fig)
    report = [
        "# Ejercicio 6: Parquet frente a tablas DuckDB",
        "## Alcance y reproducción",
        "El benchmark usa los tres conjuntos exactos de [preparacion_benchmark.json](preparacion_benchmark.json), con 2024 y 2026. No se infieren tiempos ni se extrapolan otros entornos.",
        "```bash\ndocker compose exec -T lab python scripts/benchmark.py --repetitions 5 --warmups 1 --threads 4 --memory-limit 2GB --seed 42\n```",
        "Cada ejecución reconstruye las tres bases derivadas en `data/processed/benchmark/`. Para repetir solamente consultas sobre las mismas fuentes y tablas puede añadir `--reuse-materialized`; se verifican rutas, tamaños, fechas de modificación y SQL de origen. Los costos de construcción reutilizados pertenecen a su ejecución original, identificada en los metadatos locales. `--levels pequeno` permite una ejecución parcial. Para regenerar documentación/gráficos desde mediciones existentes utilice `--report-only`.",
        "El notebook `06_benchmark_parquet_duckdb.ipynb` revisa las mediciones registradas; su opción RUN_BENCHMARK permite reproducirlas explícitamente. Todos los datos y bases permanecen excluidos de Git.",
        "## 6.1–6.4: equivalencia y materialización",
        "Para cada tamaño se crean vistas **temporales** de Parquet con listas explícitas de archivos, armonización de nombres y NULL estructurales. `CREATE TABLE viajes_duckdb AS SELECT * FROM viajes_parquet` materializa exactamente esa fuente sin limpiar, filtrar ni deduplicar. CHECKPOINT completa la persistencia. Se verifica el conteo contra el inventario del ejercicio 5 y se reabre la base con read_only antes de medir ambas estrategias. Solo la tabla persiste; las vistas externas no se guardan en la base, facilitando su uso posterior desde otra herramienta.",
        "La tabla también guarda tipo de taxi, archivo y mes de archivo ya derivados. Parquet calcula esos campos mediante la vista. El SQL analítico solo cambia el nombre de la relación, pero parte del trabajo de armonización se paga al construir la tabla; esa ventaja tiene un costo explícito de materialización. No se crean índices ni se ordena la tabla deliberadamente.",
        f"Se comprobaron {len(validations)} combinaciones de tamaño/consulta. Los nombres y tipos de resultados coinciden. Cada ejecución medida también se compara con su referencia: categorías, fechas y conteos exactos; medias flotantes con tolerancias relativas 1e-9 y absolutas 1e-8 para diferencias de acumulación. No se utilizan percentiles aproximados en el benchmark.",
        "## 6.5–6.7: protocolo y resultados",
        "Condiciones registradas en [entorno.json](resultados_ejercicio_6/entorno.json):",
        "```json\n" + json.dumps(metadata, indent=2, ensure_ascii=False) + "\n```",
        "Se realiza al menos un calentamiento por estrategia/consulta, excluido de la tabla principal. Se intercalan consultas y alterna la estrategia que inicia cada par; la ejecución es secuencial. Las mediciones incluyen execute y fetchall, con resultados pequeños. Se excluyen materialización, verificación, exportación CSV y EXPLAIN. Son ejecuciones recurrentes con cachés no vaciadas, no un experimento de caché fría. El calentamiento no garantiza que todos los datos residan en RAM; no se mide pico de memoria y memory_limit no representa toda la memoria del proceso.",
        "### Costo separado de materialización",
        table(materializations[["nivel", "registros", "cantidad_archivos", "bytes_parquet", "bytes_duckdb", "preparacion_s", "creacion_tabla_s", "checkpoint_s", "materializacion_s"]].round(4)),
        "Materializacion_s incluye apertura/preparación de fuente, CTAS y checkpoint. La verificación posterior del conteo y el cierre no están incluidos. Los tamaños son bytes de Parquet y archivo DuckDB después del checkpoint; no incluyen scratch temporal.",
        "### Comparación de medianas",
        table(comparison.round(6)),
        "Razón = mediana Parquet / mediana DuckDB. Mayor que 1 favorece la tabla; menor que 1 favorece Parquet. `menor_mediana` identifica la menor observada, no significa una diferencia estadísticamente probada. La dispersión, mínimos y máximos están en [resumen.csv](resultados_ejercicio_6/resumen.csv), y todas las repeticiones en [tiempos.csv](resultados_ejercicio_6/tiempos.csv).",
        "![Tiempos por volumen](figuras_ejercicio_6/tiempos_por_volumen.png)",
        "![Escalabilidad](figuras_ejercicio_6/escalabilidad.png)",
        "## 6.8: consultas del benchmark",
    ]
    for query, title, objective, origin in QUERY_SPECS:
        report += ["### " + query + ": " + title, "**Objetivo:** " + objective + " **Origen:** " + origin,
                   f"**SQL:** [{query}.sql](../sql/benchmark/{query}.sql). Se sustituye únicamente {{{{fuente}}}} por viajes_parquet o viajes_duckdb. Los CSV por tamaño/estrategia están en resultados_ejercicio_6/resultados_consultas/ y los planes en resultados_ejercicio_6/planes/."]
    report += ["## 6.9: interpretación de resultados"]
    for level in level_order:
        d = comparison.query("nivel == @level")
        native_wins = int((d.menor_mediana == "duckdb").sum())
        strongest = d.loc[d.razon_parquet_duckdb.idxmax()]
        weakest = d.loc[d.razon_parquet_duckdb.idxmin()]
        report += [f"**{level}:** la tabla tiene menor mediana en {native_wins}/{len(d)} consultas. La razón mayor es {strongest.razon_parquet_duckdb:.2f}× en {strongest.consulta}; la menor, {weakest.razon_parquet_duckdb:.2f}× en {weakest.consulta}. Estos extremos se interpretan junto con los tiempos absolutos y la dispersión, especialmente en consultas de pocos milisegundos."]
        material = materializations.loc[materializations.nivel == level].iloc[0]
        saving = d.parquet_mediana_s.sum()-d.duckdb_mediana_s.sum()
        if saving > 0:
            rounds = math.ceil(material.materializacion_s/saving)
            report += [f"Una ronda que ejecuta una vez las cinco consultas tendría, sumando medianas observadas, un ahorro aproximado de {saving:.4f} s con la tabla. El costo de construcción de {material.materializacion_s:.2f} s se compensaría alrededor de {rounds:,} rondas similares. Es una estimación bajo carga estable, no un umbral garantizado ni una medición de rondas completas; excluye mantenimiento, almacenamiento y cambios de datos."]
        else:
            report += ["La suma de medianas de esta mezcla no favorece a la tabla; no se estima compensación del costo de construcción para esa mezcla."]
    report += [
        "El crecimiento del conjunto se observa por consulta, no mediante una única tasa global. Los conteos, agregaciones con filtros y selección por fecha tienen trabajos distintos. Las diferencias pueden estar relacionadas con estadísticas, formato y compresión, descarte de grupos de filas, costo de abrir varios archivos, cachés y los campos derivados precomputados. Estas son explicaciones posibles apoyadas por capacidades de DuckDB; no se aísla causalmente cada factor. Los EXPLAIN guardados permiten revisar los operadores concretos sin añadir su ejecución al tiempo medido.",
        "## 6.10: cuándo usar cada estrategia",
        "**Parquet directo:** exploración o consultas ocasionales, archivos que llegan continuamente, necesidad de evitar una copia/materialización y flujos que ya organizan sus datos por archivos. Aprovecha que se pueden seleccionar columnas y aplicar filtros, pero el beneficio depende de consulta y organización.",
        "**Tabla DuckDB:** consultas repetidas sobre una instantánea, necesidad de un archivo analítico persistente y casos donde el ahorro medido compensa construcción y mantenimiento. La tabla completa del laboratorio queda en `data/processed/benchmark/completo.duckdb`, con `viajes_duckdb`, lista para la conexión posterior del tablero en modo de solo lectura.",
        "Esta medición no prueba que una estrategia sea siempre superior. El entorno usa Docker y volúmenes compartidos con macOS; otros servicios pueden competir por recursos. Los conjuntos también difieren en número de archivos, meses y esquemas, además de filas, por lo que la gráfica no aísla exclusivamente el tamaño. Para otra máquina o patrón de consultas se debe repetir el benchmark. No se cronometran conexiones nuevas por consulta ni se controla la caché del sistema operativo.",
        "Referencias: [DuckDB: Parquet](https://duckdb.org/docs/current/data/parquet/overview) y [DuckDB: ajuste de cargas](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads).",
    ]
    (ROOT / "docs" / "ejercicio_6_benchmark.md").write_text("\n\n".join(report)+"\n", encoding="utf-8")
    return summary, comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="2GB")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--levels", nargs="+", choices=["pequeno", "mediano", "completo"])
    parser.add_argument("--reuse-materialized", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.repetitions < 3 or args.warmups < 1 or args.threads < 1:
        parser.error("Use al menos 3 repeticiones, 1 calentamiento y 1 hilo")
    os.chdir(ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    if args.report_only:
        make_outputs(*(pd.read_csv(OUTPUT_DIR / (n+".csv")) for n in ("tiempos", "calentamientos", "equivalencia", "materializacion")),
                     json.loads((OUTPUT_DIR / "entorno.json").read_text()))
        print("Documentación y gráficos regenerados desde las mediciones existentes.")
        return
    preparation = json.loads((ROOT / "docs" / "preparacion_benchmark.json").read_text())
    levels = [level for level in preparation["niveles"] if args.levels is None or level["nombre"] in args.levels]
    rng = random.Random(args.seed)
    metadata = environment(args)
    timings, warmups, validations, materials = [], [], [], []
    for level in levels:
        material = materialize(level, args)
        materials.append({k: v for k, v in material.items() if k != "fuentes"})
        measured, warmed, validated = run_level(level, material, args, rng)
        timings += measured; warmups += warmed; validations += validated
    metadata["niveles_ejecutados"] = [level["nombre"] for level in levels]
    metadata["materializacion_reutilizada"] = args.reuse_materialized
    (OUTPUT_DIR / "entorno.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False)+"\n")
    make_outputs(pd.DataFrame(timings), pd.DataFrame(warmups), pd.DataFrame(validations), pd.DataFrame(materials), metadata)
    print("Benchmark completado: docs/ejercicio_6_benchmark.md", flush=True)


if __name__ == "__main__":
    main()
