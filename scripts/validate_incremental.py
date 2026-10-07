"""Ejercicio 5: preservación de 2026, consultas conjuntas y compatibilidad SQL."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analyze_trips import create_eda_connection
from explore_parquet import ROOT, table

OUTPUT_DIR = ROOT / "docs" / "resultados_ejercicio_5"
SQL_DIR = ROOT / "sql" / "incremental"
SNAPSHOT = ROOT / "data" / "processed" / "snapshot_2026_ejercicio_5.json"
QUERY_SPECS = [
    ("01_consulta_conjunta", "Consulta conjunta por año y tipo", "Demostrar que una misma vista consulta 2024 y 2026 y contar sus fuentes y registros."),
    ("02_inventario", "Inventario ampliado", "Enumerar cada Parquet y contrastar COUNT de DuckDB con sus metadatos PyArrow."),
    ("03_esquemas_por_anio", "Esquemas por año", "Identificar columnas ausentes y cambios de tipos físicos antes de interpretar NULL."),
    ("04_campos_opcionales", "Campos opcionales y nulos", "Verificar la representación de campos añadidos sin imputar datos de años anteriores."),
    ("05_meses_comunes", "Meses con cobertura común", "Identificar meses presentes para ambos taxis y ambos años, evitando comparar un año completo con uno parcial."),
    ("06_tipos_unificados", "Tipos de la vista conjunta", "Documentar los tipos resultantes de la combinación de esquemas."),
]


def fingerprint(path):
    with path.open("rb") as handle:
        sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
    stat = path.stat()
    return {"ruta": str(path.relative_to(ROOT)), "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns, "sha256": sha256}


def prepare_snapshot():
    if SNAPSHOT.exists():
        print("Se conserva el snapshot previo:", SNAPSHOT.relative_to(ROOT))
        return
    paths = sorted((ROOT / "data" / "raw").glob("*/2026/*.parquet"))
    if not paths or {p.parent.parent.name for p in paths} != {"yellow", "green"}:
        raise FileNotFoundError("Primero descargue ambos tipos de taxi de 2026.")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"fecha_utc": datetime.now(timezone.utc).isoformat(),
                                   "archivos": [fingerprint(p) for p in paths]}, indent=2) + "\n")
    print("Snapshot previo:", len(paths), "archivos de 2026.")


def check_preservation():
    if not SNAPSHOT.exists():
        raise FileNotFoundError("Falta el snapshot anterior a la ampliación. Ejecute --snapshot-2026 antes de descargar 2024.")
    baseline = json.loads(SNAPSHOT.read_text())
    if not baseline["archivos"]:
        raise ValueError("El snapshot está vacío")
    results = []
    for before in baseline["archivos"]:
        after = fingerprint(ROOT / before["ruta"])
        unchanged = all(after[k] == before[k] for k in ("bytes", "mtime_ns", "sha256"))
        results.append({**after, "sin_cambios": unchanged})
    if not all(r["sin_cambios"] for r in results):
        raise AssertionError("Se detectó un cambio en los archivos originales de 2026")
    evidence = {"archivos_preservados": len(results), "todos_sin_cambios": True,
                "criterios": ["bytes", "mtime_ns", "sha256"], "archivos": results}
    (ROOT / "docs" / "preservacion_2026_ejercicio_5.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def compatibility(connection):
    results = []
    for ejercicio, folder in ((3, ROOT / "sql" / "exploracion"), (4, ROOT / "sql" / "eda")):
        destination = OUTPUT_DIR / f"compatibilidad_ejercicio_{ejercicio}"
        destination.mkdir(parents=True, exist_ok=True)
        for sql_path in sorted(folder.glob("*.sql")):
            if sql_path.name.startswith("00_"):
                continue
            print("Compatibilidad:", sql_path.relative_to(ROOT), flush=True)
            frame = connection.execute(sql_path.read_text()).fetchdf()
            target = destination / (sql_path.stem + ".csv")
            frame.to_csv(target, index=False)
            results.append({"ejercicio": ejercicio, "consulta": str(sql_path.relative_to(ROOT)),
                            "estado": "OK", "filas_resultado": len(frame),
                            "resultado": str(target.relative_to(ROOT))})
    pd.DataFrame(results).to_csv(OUTPUT_DIR / "compatibilidad_sql.csv", index=False)
    return results


def benchmark_preparation(inventory):
    levels = []
    for name, description, selector in [
        ("pequeno", "Enero de 2024, amarillos y verdes", (inventory.anio == 2024) & (pd.to_datetime(inventory.mes_archivo).dt.month == 1)),
        ("mediano", "Enero a junio de 2024, amarillos y verdes", (inventory.anio == 2024) & (pd.to_datetime(inventory.mes_archivo).dt.month <= 6)),
        ("completo", "Todos los archivos validados de 2024 y 2026", inventory.anio.isin([2024, 2026])),
    ]:
        subset = inventory.loc[selector]
        paths = subset.archivo.tolist()
        levels.append({"nombre": name, "descripcion": description,
                       "cantidad_archivos": len(paths), "registros": int(subset.registros.sum()),
                       "bytes_parquet": sum((ROOT / p).stat().st_size for p in paths),
                       "archivos": paths})
    preparation = {"estado": "datos_preparados_sin_mediciones_de_rendimiento",
                   "fuente": "docs/resultados_ejercicio_5/02_inventario.csv",
                   "niveles": levels,
                   "nota": "El ejercicio 6 materializará cada conjunto y medirá consultas equivalentes; este archivo no contiene tiempos ni afirma cuál estrategia es más rápida."}
    (ROOT / "docs" / "preparacion_benchmark.json").write_text(json.dumps(preparation, indent=2, ensure_ascii=False) + "\n")
    return preparation


def validate_counts(frames, validation):
    inventory = frames["02_inventario"]
    actual = {r.archivo: int(r.registros) for r in inventory.itertuples()}
    expected = {r["ruta"]: r["registros"] for r in validation["archivos"]}
    if actual != expected:
        raise AssertionError("Los conteos SQL no coinciden con todos los metadatos validados")
    joint = frames["01_consulta_conjunta"]
    if set(zip(joint.anio, joint.tipo_taxi)) != {(2024, "yellow"), (2024, "green"), (2026, "yellow"), (2026, "green")}:
        raise AssertionError("Falta una combinación de año y tipo")
    if not (joint.loc[joint.anio == 2024, "archivos"] == 12).all():
        raise AssertionError("2024 debe tener 12 meses por tipo")
    if int(joint.registros.sum()) != int(inventory.registros.sum()):
        raise AssertionError("El conteo conjunto y el inventario no coinciden")


def write_report(frames, preservation, manifest, compatibility_results, preparation):
    summary = manifest["resumen"]
    schemas = frames["03_esquemas_por_anio"]
    target_columns = schemas.loc[schemas.columna.str.lower().isin(["cbd_congestion_fee", "request_source", "ratecodeid", "payment_type", "passenger_count", "trip_type"])]
    source_initial = ROOT / "data" / "processed" / "download_manifest_2024_2026_inicial.json"
    initial = json.loads(source_initial.read_text())["resumen"] if source_initial.exists() else None
    common = sorted(frames["05_meses_comunes"].mes.unique())
    report = [
        "# Ejercicio 5: incorporación incremental de 2024",
        "Generado el " + datetime.now(timezone.utc).isoformat() + " (UTC). Trabajo individual.",
        "## Resultado y alcance (5.1–5.5)",
        "El descargador acepta `--years`, conserva 2026 como valor por defecto y admite ejecución incremental por año y tipo. La estructura sigue siendo `data/raw/<tipo>/<año>/`. Los años repetidos se deduplican y `--workers` limita las descargas simultáneas (3 por defecto). Se conservan los reintentos, archivos temporales, comprobación de firmas y tamaño, catálogo para 403 ambiguos y manifiestos por ejecución.",
        "La validación ahora deriva los candidatos del alcance declarado en el manifiesto. `--require-full-years 2024` exige los doce meses de ambos tipos; 2026 se valida según los archivos publicados. Los manifiestos anteriores de 2026 siguen siendo compatibles.",
        "### Reproducción",
        "Antes de incorporar 2024, con 2026 ya descargado:",
        "```bash\ndocker compose exec -T lab python scripts/validate_incremental.py --snapshot-2026\ndocker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability --manifest data/processed/download_manifest_2024_2026_inicial.json\ndocker compose exec -T lab python scripts/download_data.py --years 2024 2026 --verify-availability\ndocker compose exec -T lab python scripts/validate_download.py --manifest data/processed/download_manifest_2024_2026.json --require-full-years 2024\ndocker compose exec -T lab python scripts/validate_incremental.py\n```",
        "El snapshot es local y debe crearse antes de la ampliación para comprobar preservación. Si ya existe, se conserva; no se reemplaza por una huella posterior. Una segunda descarga solo omitirá todos los archivos si no se publicaron meses nuevos entre las ejecuciones.",
        "### Evidencia de descarga y preservación",
        "Resumen de la ejecución inicial: " + (json.dumps(initial, ensure_ascii=False) if initial is not None else "No se suministró el manifiesto inicial; no se afirma cuántos archivos fueron nuevos en aquella ejecución."),
        "Resumen de la segunda ejecución: " + json.dumps(summary, ensure_ascii=False),
        f"Se comprobaron **{preservation['archivos_preservados']} archivos originales de 2026 sin cambios** en bytes, fecha de modificación y SHA-256. La evidencia está en [preservacion_2026_ejercicio_5.json](preservacion_2026_ejercicio_5.json). El manifiesto inicial y el snapshot permanecen en `data/processed/`, excluidos de Git.",
        "La lectura de metadatos PyArrow y los conteos DuckDB coinciden por archivo. Véase [validacion_descarga_2024_2026.json](validacion_descarga_2024_2026.json).",
        "## Consulta conjunta (5.6 y 5.8)",
        table(frames["01_consulta_conjunta"]),
        f"Total conjunto: **{int(frames['02_inventario'].registros.sum()):,} registros** en **{len(frames['02_inventario']):,} archivos**. Los años proceden del nombre del archivo; las fechas anómalas de los viajes no se corrigen.",
        "### Meses con cobertura común",
        "Meses presentes en ambos años y ambos tipos: " + ", ".join(map(str, common)) + ". 2024 tiene doce meses y 2026 solo los publicados. No se comparan directamente sus totales como si ambos representaran un año completo.",
        "## Diferencias de esquema y continuidad de consultas (5.7)",
        table(target_columns),
        "`union_by_name=true` combina columnas por nombre y representa campos ausentes mediante NULL. Se ajustó 00_fuentes.sql con una rama vacía tipada (`WHERE FALSE`) para declarar cbd_congestion_fee y request_source incluso si se consultan solo archivos de 2024. La rama no añade filas ni imputa valores; evita depender de que existan archivos de 2026 para descubrir esos campos. La vista armoniza tpep/lpep y conserva el origen. Los tipos compatibles se promueven automáticamente; los originales y los finales se guardan por separado. No se fuerza una conversión a entero que pueda truncar valores.",
        "La consulta 04 contrasta nulos de cbd_congestion_fee y request_source con su presencia física en la consulta 03. Un campo ausente en un año no se interpreta como cero ni como un valor no reportado en una columna existente.",
        table(frames["04_campos_opcionales"]),
        f"Las **{len(compatibility_results)} consultas existentes de los ejercicios 3 y 4** se ejecutaron sobre el conjunto ampliado sin modificar su SQL. Sus resultados conjuntos están en [compatibilidad_sql.csv](resultados_ejercicio_5/compatibilidad_sql.csv), con un CSV por consulta. Los notebooks y resultados originales de 2026 no se sobrescriben.",
        "Que una consulta siga ejecutándose no convierte una agregación conjunta en una comparación entre años. Para una comparación anual debe añadirse el año al GROUP BY o restringirse la población. Las consultas nuevas 01–05 declaran explícitamente 2024 y 2026; las anteriores de hora, pagos y percentiles agregan el conjunto completo si se vuelven a ejecutar. Las medianas siguen siendo aproximadas.",
        "## Consultas documentadas (5.8)",
    ]
    for name, title, objective in QUERY_SPECS:
        report += ["### " + name + ": " + title,
                   "**Objetivo:** " + objective,
                   f"**SQL:** [{name}.sql](../sql/incremental/{name}.sql). **Resultado:** [{name}.csv](resultados_ejercicio_5/{name}.csv), {len(frames[name])} filas.",
                   "**Fuente:** archivos exactos del inventario 02, mediante las vistas externas; la consulta 03 lee los metadatos Parquet. **Decisión:** conservar procedencia y diferencias de esquema, validar conteos y declarar año y cobertura antes de comparar."]
    report += [
        "## Diseño incremental (5.9)",
        "Los parámetros de años evitan reescribir el descargador; las rutas separan tipo y año; los patrones `*/*.parquet` descubren nuevos archivos; las vistas guardan definiciones de lectura en lugar de copias; union_by_name tolera las columnas añadidas. Los manifiestos y verificaciones registran el alcance de cada ejecución y los archivos existentes no se descargan otra vez. Los análisis históricos quedan versionados y las comprobaciones de compatibilidad se guardan aparte.",
        "## Preparación del ejercicio 6",
        "[preparacion_benchmark.json](preparacion_benchmark.json) define tres volúmenes de datos, con rutas, tamaños y conteos exactos:",
        table(pd.DataFrame([{k: level[k] for k in ("nombre", "descripcion", "cantidad_archivos", "registros", "bytes_parquet")} for level in preparation["niveles"]])),
        "Todavía no se materializan tablas ni se registran tiempos. El ejercicio 6 deberá construir cada tabla y medir las mismas consultas contra sus Parquet equivalentes, con condiciones y repeticiones controladas. Este ejercicio deja las fuentes y tamaños preparados, sin adelantar conclusiones de rendimiento.",
    ]
    (ROOT / "docs" / "ejercicio_5_incorporacion_2024.md").write_text("\n\n".join(report) + "\n", encoding="utf-8")


def run_validation():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validation = json.loads((ROOT / "docs" / "validacion_descarga_2024_2026.json").read_text())
    if not validation["completo_segun_publicacion"] or set(validation["anios"]) != {2024, 2026}:
        raise ValueError("Primero complete validate_download.py para 2024 y 2026")
    if 2024 not in validation["anios_completos_requeridos"]:
        raise ValueError("La validación debe exigir 2024 completo")
    manifest = json.loads((ROOT / "data" / "processed" / "download_manifest_2024_2026.json").read_text())
    if manifest["resumen"]["fallidos"]:
        raise ValueError("El manifiesto contiene errores")
    preservation = check_preservation()
    with create_eda_connection() as connection:
        frames = {}
        for name, _, _ in QUERY_SPECS:
            print("Validación:", name, flush=True)
            frames[name] = connection.execute((SQL_DIR / (name + ".sql")).read_text()).fetchdf()
            frames[name].to_csv(OUTPUT_DIR / (name + ".csv"), index=False)
        validate_counts(frames, validation)
        compatibility_results = compatibility(connection)
        if connection.execute("SELECT count(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'").fetchone()[0]:
            raise AssertionError("El ejercicio 5 no debe materializar tablas")
    preparation = benchmark_preparation(frames["02_inventario"])
    write_report(frames, preservation, manifest, compatibility_results, preparation)
    print("Validación incremental completada.", flush=True)
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-2026", action="store_true",
                        help="guarda antes de ampliar las huellas de los Parquet originales de 2026")
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.snapshot_2026:
        prepare_snapshot()
    else:
        run_validation()


if __name__ == "__main__":
    main()
