"""Valida el manifiesto de descarga y lee los metadatos de cada Parquet."""

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=Path("data/processed/download_manifest_2026.json"))
    parser.add_argument("--output", type=Path,
                        help="reporte JSON; por defecto docs/validacion_descarga_<años>.json")
    parser.add_argument("--require-full-years", nargs="+", type=int, default=[],
                        help="años cerrados que deben tener los 12 meses publicados por tipo")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errores = []
    resultados = []
    if not manifest["verificacion_publicacion"]:
        errores.append("El manifiesto no verificó la publicación de todos los meses.")
    # Los manifiestos del ejercicio 2 no declaraban su alcance explícitamente.
    anios = sorted(manifest.get("anios", {r["anio"] for r in manifest["archivos"]}))
    tipos = sorted(manifest.get("tipos", {r["tipo"] for r in manifest["archivos"]}))
    if not anios or not tipos or not set(tipos).issubset({"yellow", "green"}):
        errores.append("El manifiesto no declara un alcance válido.")
    if not set(args.require_full_years).issubset(anios):
        errores.append("Los años requeridos no están incluidos en el manifiesto.")
    esperados = {(tipo, anio, mes) for tipo in tipos for anio in anios for mes in range(1, 13)}
    encontrados = {(r["tipo"], r["anio"], r["mes"]) for r in manifest["archivos"]}
    if encontrados != esperados or len(manifest["archivos"]) != len(esperados):
        errores.append("El manifiesto debe registrar una sola vez los 12 meses de cada tipo y año declarado.")
    for registro in manifest["archivos"]:
        if registro["estado"] == "no_publicado":
            if registro["anio"] in args.require_full_years:
                errores.append(f"{registro['ruta']}: falta un mes de un año requerido completo")
            continue
        if registro["estado"] not in ("existente", "descargado"):
            errores.append(f"{registro['ruta']}: {registro['estado']}")
            continue
        ruta = Path(registro["ruta"])
        try:
            nombre = f"{registro['tipo']}_tripdata_{registro['anio']}-{registro['mes']:02d}.parquet"
            if ruta.name != nombre or ruta.parts[-3:-1] != (registro["tipo"], str(registro["anio"])):
                raise ValueError("la ruta no coincide con el tipo, año y mes del manifiesto")
            if ruta.stat().st_size != registro["bytes"]:
                raise ValueError("el tamaño cambió desde la descarga")
            metadata = pq.read_metadata(ruta)
            resultados.append({"ruta": str(ruta), "bytes": ruta.stat().st_size,
                               "registros": metadata.num_rows,
                               "columnas": metadata.num_columns})
        except Exception as error:
            errores.append(f"{ruta}: {error}")
    if not resultados:
        errores.append("No hay archivos Parquet disponibles para validar.")
    reporte = {"fecha_descarga_utc": manifest["fecha_utc"],
               "anios": anios, "tipos": tipos,
               "anios_completos_requeridos": args.require_full_years,
               "completo_segun_publicacion": not errores,
               "archivos_validados": len(resultados),
               "no_publicados": manifest["resumen"]["no_publicados"],
               "total_bytes": sum(r["bytes"] for r in resultados),
               "total_registros_metadata": sum(r["registros"] for r in resultados),
               "archivos": resultados, "errores": errores}
    output = args.output or Path("docs") / ("validacion_descarga_" + "_".join(map(str, anios)) + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reporte, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
