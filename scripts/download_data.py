#!/usr/bin/env python3
"""Descarga los archivos Parquet de 2026 del NYC TLC Trip Record Data.

Descarga los registros de viajes de taxis amarillos (yellow) y verdes (green)
correspondientes al anio 2026, que es el conjunto de datos inicial del
laboratorio. Este script solo contempla el anio 2026.

Fuente oficial de los datos:
    https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Uso:
    python scripts/download_data.py                 # amarillos y verdes
    python scripts/download_data.py --taxi yellow
    python scripts/download_data.py --taxi green

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
import json
from datetime import datetime, timezone
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import urljoin
from pathlib import Path

import requests

ANIO = 2026
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


def construir_nombre(tipo: str, mes: int) -> str:
    """Nombre del archivo publicado por la TLC, p. ej. yellow_tripdata_2026-01.parquet."""
    return f"{tipo}_tripdata_{ANIO}-{mes:02d}.parquet"


def construir_url(tipo: str, mes: int) -> str:
    """URL completa del archivo Parquet mensual."""
    return f"{URL_BASE}/{construir_nombre(tipo, mes)}"


def ruta_destino(tipo: str, mes: int) -> Path:
    """Ruta local donde se guarda el archivo."""
    return DIR_DESTINO / tipo / str(ANIO) / construir_nombre(tipo, mes)


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


def descargar(tipo: str, verificar: bool = False, archivos=None) -> dict:
    """Descarga todos los meses publicados de un tipo de taxi para 2026."""
    print(f"\n=== {tipo.upper()} {ANIO} ===")
    resumen = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}

    for mes in range(1, 13):
        etiqueta = f"{ANIO}-{mes:02d}"
        destino = ruta_destino(tipo, mes)

        registro = {"tipo": tipo, "anio": ANIO, "mes": mes,
                    "url": construir_url(tipo, mes), "ruta": str(destino)}
        if archivos is not None:
            archivos.append(registro)
        if not verificar and destino.exists() and destino.stat().st_size > 0:
            print(f"  {etiqueta}  ya existe, se omite")
            resumen["omitidos"] += 1
            registro.update(estado="existente", bytes=destino.stat().st_size)
            continue

        url = construir_url(tipo, mes)
        try:
            publicado = esta_publicado(url)
        except requests.RequestException as error:
            print(f"  {etiqueta}  ERROR al consultar publicación: {error}")
            resumen["fallidos"].append(etiqueta)
            registro.update(estado="error_publicacion", error=str(error))
            continue
        if not publicado:
            print(f"  {etiqueta}  aun no publicado por la TLC")
            resumen["no_publicados"].append(etiqueta)
            registro["estado"] = "no_publicado"
            continue

        if destino.exists() and destino.stat().st_size > 0:
            print(f"  {etiqueta}  publicado y existente, se omite")
            resumen["omitidos"] += 1
            registro.update(estado="existente", bytes=destino.stat().st_size)
            continue

        print(f"  {etiqueta}  descargando...")
        try:
            escritos = descargar_archivo(url, destino)
        except requests.RequestException as error:
            print(f"  {etiqueta}  ERROR: {error}")
            resumen["fallidos"].append(etiqueta)
            registro.update(estado="error_descarga", error=str(error))
        else:
            print(f"  {etiqueta}  listo ({formato_tamanio(escritos)}) -> {destino}")
            resumen["descargados"] += 1
            registro.update(estado="descargado", bytes=escritos)

    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Descarga los datos de taxis de {ANIO} del NYC TLC."
    )
    parser.add_argument(
        "--taxi", choices=(*TIPOS_TAXI, "all"), default="all",
        help="tipo de taxi a descargar (por defecto: all)",
    )
    parser.add_argument("--verify-availability", action="store_true",
                        help="consulta la publicación incluso para archivos locales; no los vuelve a descargar")
    parser.add_argument("--manifest", type=Path,
                        default=Path("data/processed/download_manifest_2026.json"),
                        help="ruta del reporte JSON de esta ejecución")
    argumentos = parser.parse_args()

    tipos = TIPOS_TAXI if argumentos.taxi == "all" else (argumentos.taxi,)

    total = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}
    archivos = []
    for tipo in tipos:
        resumen = descargar(tipo, argumentos.verify_availability, archivos)
        total["descargados"] += resumen["descargados"]
        total["omitidos"] += resumen["omitidos"]
        total["no_publicados"] += [f"{tipo} {m}" for m in resumen["no_publicados"]]
        total["fallidos"] += [f"{tipo} {m}" for m in resumen["fallidos"]]

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  descargados   : {total['descargados']}")
    print(f"  ya existian   : {total['omitidos']}")
    print(f"  no publicados : {len(total['no_publicados'])}")
    if total["no_publicados"]:
        print(f"      {', '.join(total['no_publicados'])}")
    print(f"  fallidos      : {len(total['fallidos'])}")
    if total["fallidos"]:
        print(f"      {', '.join(total['fallidos'])}")
    print("=" * 60)

    argumentos.manifest.parent.mkdir(parents=True, exist_ok=True)
    argumentos.manifest.write_text(json.dumps({
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "catalogo_oficial": URL_CATALOGO,
        "enlaces_catalogo_consultado": sorted(enlaces_publicados())
            if enlaces_publicados.cache_info().currsize else None,
        "verificacion_publicacion": argumentos.verify_availability,
        "resumen": total, "archivos": archivos,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  reporte      : {argumentos.manifest}")
    return 1 if total["fallidos"] else 0


if __name__ == "__main__":
    sys.exit(main())
