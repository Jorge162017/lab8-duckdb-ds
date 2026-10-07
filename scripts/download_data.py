#!/usr/bin/env python3
"""Descarga incremental de archivos Parquet del NYC TLC Trip Record Data.

Descarga los registros de viajes de taxis amarillos (yellow) y verdes (green)
para los años indicados mediante --years. Por defecto se conserva 2026,
el conjunto inicial del laboratorio. Cada archivo existente se conserva.

Fuente oficial de los datos:
    https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Uso:
    python scripts/download_data.py                 # amarillos y verdes
    python scripts/download_data.py --taxi yellow
    python scripts/download_data.py --taxi green
    python scripts/download_data.py --years 2024 2026 --verify-availability

Los archivos se guardan en:
    data/raw/<tipo>/<anio>/<nombre-original>.parquet

Comportamiento:
  - La TLC publica cada mes con varias semanas de atraso, por lo que no todos
    los meses de 2026 existen todavia. El script consulta al servidor que
    meses estan publicados en lugar de suponerlos.
  - Un archivo que ya existe localmente no se vuelve a descargar.
  - --verify-availability comprueba también la publicación de archivos locales.
  - Cada ejecución deja un manifiesto JSON; errores de red no se confunden con 404.
  - La descarga se hace sobre un nombre temporal y solo se renombra al
    terminar, de modo que una interrupcion no deja archivos .parquet a medias.
"""

import argparse
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime, timezone
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import urljoin
from pathlib import Path

import requests

ANIO_POR_DEFECTO = 2026
ROOT = Path(__file__).resolve().parents[1]
TIPOS_TAXI = ("yellow", "green")
URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
DIR_DESTINO = Path("data/raw")

TIEMPO_ESPERA = 60          # segundos por peticion
INTENTOS = 3                # intentos por archivo antes de darse por vencido
BLOQUE = 1024 * 1024        # 1 MiB por bloque de descarga
SUFIJO_TEMPORAL = ".part"
URL_CATALOGO = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"


@lru_cache(maxsize=1)
def enlaces_publicados() -> frozenset:
    """Obtiene enlaces del catálogo oficial para resolver respuestas 403 ambiguas."""
    class Enlaces(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = set()

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                for nombre, valor in attrs:
                    if nombre == "href" and valor:
                        self.urls.add(urljoin(URL_CATALOGO, valor))

    with requests.get(URL_CATALOGO, headers={"User-Agent": "Mozilla/5.0"},
                      timeout=TIEMPO_ESPERA) as respuesta:
        respuesta.raise_for_status()
        parser = Enlaces()
        parser.feed(respuesta.text)
    urls = frozenset(u for u in parser.urls if u.startswith(URL_BASE + "/")
                     and ("/yellow_tripdata_" in u or "/green_tripdata_" in u)
                     and u.endswith(".parquet"))
    if not urls:
        raise requests.RequestException("No se encontraron enlaces de taxis en el catálogo oficial")
    return urls


def construir_nombre(tipo: str, mes: int, anio: int = ANIO_POR_DEFECTO) -> str:
    """Nombre del archivo publicado por la TLC, p. ej. yellow_tripdata_2026-01.parquet."""
    return f"{tipo}_tripdata_{anio}-{mes:02d}.parquet"


def construir_url(tipo: str, mes: int, anio: int = ANIO_POR_DEFECTO) -> str:
    """URL completa del archivo Parquet mensual."""
    return f"{URL_BASE}/{construir_nombre(tipo, mes, anio)}"


def ruta_destino(tipo: str, mes: int, anio: int = ANIO_POR_DEFECTO) -> Path:
    """Ruta local donde se guarda el archivo."""
    return DIR_DESTINO / tipo / str(anio) / construir_nombre(tipo, mes, anio)


def esta_publicado(url: str) -> bool:
    """Indica si el archivo existe en el servidor (sin descargarlo)."""
    for intento in range(1, INTENTOS + 1):
        try:
            with requests.head(url, timeout=TIEMPO_ESPERA, allow_redirects=True) as respuesta:
                if respuesta.status_code == 404:
                    return False
                if respuesta.status_code == 403 and url not in enlaces_publicados():
                    return False
                respuesta.raise_for_status()
                return True
        except requests.RequestException:
            if intento == INTENTOS:
                raise
    return False


def formato_tamanio(n: float) -> str:
    for unidad in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unidad == "GiB":
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GiB"


def descargar_archivo(url: str, destino: Path) -> int:
    """Descarga `url` en `destino`. Devuelve la cantidad de bytes escritos."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + SUFIJO_TEMPORAL)

    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        try:
            with requests.get(url, stream=True, timeout=TIEMPO_ESPERA) as respuesta:
                respuesta.raise_for_status()
                escritos = 0
                with temporal.open("wb") as archivo:
                    for bloque in respuesta.iter_content(chunk_size=BLOQUE):
                        if bloque:
                            archivo.write(bloque)
                            escritos += len(bloque)
            if escritos < 8:
                raise requests.RequestException("el servidor devolvio un archivo vacío o demasiado pequeño")
            esperado = respuesta.headers.get("Content-Length")
            if esperado is not None and escritos != int(esperado):
                raise requests.RequestException("el tamaño descargado no coincide con Content-Length")
            with temporal.open("rb") as archivo:
                inicio = archivo.read(4)
                archivo.seek(-4, 2)
                fin = archivo.read(4)
            if inicio != b"PAR1" or fin != b"PAR1":
                raise requests.RequestException("el archivo no tiene la firma de un Parquet")
            temporal.replace(destino)
            return escritos
        except requests.RequestException as error:
            ultimo_error = error
            temporal.unlink(missing_ok=True)
            if intento < INTENTOS:
                print(f"      intento {intento}/{INTENTOS} fallido ({error}); reintentando")

    raise requests.RequestException(f"no se pudo descargar {url}: {ultimo_error}")


def procesar_archivo(tarea, verificar: bool) -> dict:
    tipo, anio, mes = tarea
    destino = ruta_destino(tipo, mes, anio)
    url = construir_url(tipo, mes, anio)
    etiqueta = f"{tipo} {anio}-{mes:02d}"
    registro = {"tipo": tipo, "anio": anio, "mes": mes, "url": url,
                "ruta": str(destino)}
    existe = destino.exists() and destino.stat().st_size > 0
    if existe and not verificar:
        registro.update(estado="existente", bytes=destino.stat().st_size)
        print(f"  {etiqueta}  existente, se omite", flush=True)
        return registro
    try:
        publicado = esta_publicado(url)
    except requests.RequestException as error:
        registro.update(estado="error_publicacion", error=str(error))
        print(f"  {etiqueta}  ERROR al consultar publicación: {error}", flush=True)
        return registro
    if not publicado:
        registro["estado"] = "no_publicado"
        print(f"  {etiqueta}  no publicado", flush=True)
        return registro
    if existe:
        registro.update(estado="existente", bytes=destino.stat().st_size)
        print(f"  {etiqueta}  publicado y existente, se omite", flush=True)
        return registro
    print(f"  {etiqueta}  descargando...", flush=True)
    try:
        escritos = descargar_archivo(url, destino)
    except requests.RequestException as error:
        registro.update(estado="error_descarga", error=str(error))
        print(f"  {etiqueta}  ERROR: {error}", flush=True)
    else:
        registro.update(estado="descargado", bytes=escritos)
        print(f"  {etiqueta}  listo ({formato_tamanio(escritos)})", flush=True)
    return registro


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taxi", choices=(*TIPOS_TAXI, "all"), default="all")
    parser.add_argument("--years", nargs="+", type=int, default=[ANIO_POR_DEFECTO],
                        help="años a descargar (por defecto: 2026)")
    parser.add_argument("--workers", type=int, default=3,
                        help="descargas simultáneas, de 1 a 8 (por defecto: 3)")
    parser.add_argument("--verify-availability", action="store_true",
                        help="consulta la publicación incluso para archivos locales sin volver a descargarlos")
    parser.add_argument("--manifest", type=Path,
                        help="reporte JSON; por defecto data/processed/download_manifest_<años>.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers debe estar entre 1 y 8")
    if any(anio < 2009 or anio > datetime.now(timezone.utc).year for anio in args.years):
        parser.error("--years debe contener años desde 2009 hasta el año actual")
    os.chdir(ROOT)
    anios = sorted(set(args.years))
    tipos = list(TIPOS_TAXI) if args.taxi == "all" else [args.taxi]
    tareas = [(tipo, anio, mes) for tipo in tipos for anio in anios for mes in range(1, 13)]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        archivos = list(executor.map(lambda tarea: procesar_archivo(tarea, args.verify_availability), tareas))
    resumen = {
        "descargados": sum(r["estado"] == "descargado" for r in archivos),
        "omitidos": sum(r["estado"] == "existente" for r in archivos),
        "no_publicados": [f"{r['tipo']} {r['anio']}-{r['mes']:02d}" for r in archivos if r["estado"] == "no_publicado"],
        "fallidos": [f"{r['tipo']} {r['anio']}-{r['mes']:02d}" for r in archivos if r["estado"].startswith("error_")],
    }
    manifest = args.manifest or Path("data/processed") / ("download_manifest_" + "_".join(map(str, anios)) + ".json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "anios": anios, "tipos": tipos, "workers": args.workers,
        "catalogo_oficial": URL_CATALOGO,
        "enlaces_catalogo_consultado": sorted(enlaces_publicados())
            if enlaces_publicados.cache_info().currsize else None,
        "verificacion_publicacion": args.verify_availability,
        "resumen": resumen, "archivos": archivos,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nRESUMEN", json.dumps(resumen, ensure_ascii=False), flush=True)
    print("Reporte:", manifest, flush=True)
    return 1 if resumen["fallidos"] else 0


if __name__ == "__main__":
    sys.exit(main())
