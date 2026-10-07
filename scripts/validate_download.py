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
                        default=Path("docs/validacion_descarga_2026.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errores = []
    resultados = []
    if not manifest["verificacion_publicacion"]:
        errores.append("El manifiesto no verificó la publicación de todos los meses.")
    esperados = {(tipo, 2026, mes) for tipo in ("yellow", "green") for mes in range(1, 13)}
    encontrados = {(r["tipo"], r["anio"], r["mes"]) for r in manifest["archivos"]}
    if encontrados != esperados or len(manifest["archivos"]) != 24:
        errores.append("El manifiesto debe registrar los 12 meses de ambos tipos de taxi.")
    for registro in manifest["archivos"]:
        if registro["estado"] == "no_publicado":
            continue
        if registro["estado"] not in ("existente", "descargado"):
            errores.append(f"{registro['ruta']}: {registro['estado']}")
            continue
        ruta = Path(registro["ruta"])
        try:
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
               "completo_segun_publicacion": not errores,
               "archivos_validados": len(resultados),
               "no_publicados": manifest["resumen"]["no_publicados"],
               "total_bytes": sum(r["bytes"] for r in resultados),
               "total_registros_metadata": sum(r["registros"] for r in resultados),
               "archivos": resultados, "errores": errores}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reporte, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
