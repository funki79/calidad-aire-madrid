"""
Descarga los datos horarios de calidad del aire de Madrid (2019-2025).

Fuente: Portal de Datos Abiertos del Ayuntamiento de Madrid
  - Datos horarios: https://datos.madrid.es/dataset/201200-0-calidad-aire-horario
  - Estaciones:     https://datos.madrid.es/dataset/212629-0-estaciones-control-aire
Licencia: Creative Commons Attribution 4.0 (CC BY 4.0)

Uso (desde la raíz del proyecto, con el venv activado):
    python datos/descargar_datos.py

Los ficheros se guardan en datos/ y Git los ignora (ver .gitignore).
Si un fichero ya existe, no se vuelve a descargar.
"""

import urllib.request
import zipfile
from pathlib import Path

# Carpeta donde está este script (datos/), sea cual sea el directorio actual
CARPETA_DATOS = Path(__file__).parent

BASE = "https://datos.madrid.es/dataset"

# Hasta 2024 hay un ZIP por año. Cada recurso tiene un identificador propio
# (no siguen un orden), copiado de la página de descargas del conjunto.
ZIPS_POR_ANIO = {
    2019: "201200-6-calidad-aire-horario-zip",
    2020: "201200-4-calidad-aire-horario-zip",
    2021: "201200-5-calidad-aire-horario-zip",
    2022: "201200-23-calidad-aire-horario-zip",
    2023: "201200-3-calidad-aire-horario-zip",
    2024: "201200-0-calidad-aire-horario-zip",
}

# Desde 2025 hay un único CSV que se actualiza cada mes (incluye el año en curso).
CSV_DESDE_2025 = "201200-1-calidad-aire-horario-csv"

# Listado de estaciones (nombre, tipo, coordenadas)
CSV_ESTACIONES = (
    f"{BASE}/212629-0-estaciones-control-aire/resource/"
    "212629-0-estaciones-control-aire-csv/download/"
    "212629-0-estaciones-control-aire-csv.csv"
)


def url_recurso(id_recurso: str, extension: str) -> str:
    """Construye la URL de descarga de un recurso del conjunto horario."""
    return (
        f"{BASE}/201200-0-calidad-aire-horario/resource/"
        f"{id_recurso}/download/{id_recurso}.{extension}"
    )


def descargar(url: str, destino: Path) -> None:
    """Descarga `url` en `destino`, salvo que ya exista."""
    if destino.exists():
        print(f"  ya existe: {destino.name}")
        return
    print(f"  descargando {destino.name} ...")
    urllib.request.urlretrieve(url, destino)


def main() -> None:
    carpeta_zip = CARPETA_DATOS / "zip"
    carpeta_csv = CARPETA_DATOS / "csv"
    carpeta_zip.mkdir(exist_ok=True)
    carpeta_csv.mkdir(exist_ok=True)

    print("1) ZIP anuales 2019-2024")
    for anio, id_recurso in ZIPS_POR_ANIO.items():
        ruta_zip = carpeta_zip / f"{anio}.zip"
        descargar(url_recurso(id_recurso, "zip"), ruta_zip)

        # Cada ZIP trae 12 meses en CSV, TXT y XML: extraemos solo los CSV
        carpeta_anio = carpeta_csv / str(anio)
        carpeta_anio.mkdir(exist_ok=True)
        with zipfile.ZipFile(ruta_zip) as z:
            for nombre in z.namelist():
                if nombre.lower().endswith(".csv"):
                    destino = carpeta_anio / Path(nombre).name
                    destino.write_bytes(z.read(nombre))

    print("2) CSV desde 2025")
    descargar(url_recurso(CSV_DESDE_2025, "csv"), carpeta_csv / "desde_2025.csv")

    print("3) Estaciones")
    descargar(CSV_ESTACIONES, CARPETA_DATOS / "estaciones.csv")

    print("Hecho.")


if __name__ == "__main__":
    main()
