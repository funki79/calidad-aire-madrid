"""
Funciones de carga y limpieza de los datos horarios de calidad del aire de Madrid.

Flujo:
    1. leer_csv_horarios()      -> lee todos los CSV y los junta (formato ancho)
    2. filtrar_contaminante()   -> se queda con un contaminante (8 = NO2)
    3. pasar_a_formato_largo()  -> una fila por hora en vez de una por día
    4. filtrar_validos()        -> se queda solo con los datos validados ("V")
"""

from pathlib import Path

import pandas as pd

# Raíz del proyecto (la carpeta que contiene src/)
RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CSV = RAIZ / "datos" / "csv"

ANIOS = range(2019, 2026)  # 2019 a 2025, ambos incluidos

# Columnas que identifican cada fila del fichero original (todo lo que no son horas)
COLUMNAS_ID = ["PROVINCIA", "MUNICIPIO", "ESTACION", "MAGNITUD",
               "PUNTO_MUESTREO", "ANO", "MES", "DIA"]

# Nombres de las 24 columnas de valores (H01..H24) y de validez (V01..V24)
COLUMNAS_H = [f"H{h:02d}" for h in range(1, 25)]
COLUMNAS_V = [f"V{h:02d}" for h in range(1, 25)]


# --------------------------------------------------------------------------
# Paso 1: leer
# --------------------------------------------------------------------------
def leer_csv_horarios(carpeta: Path = CARPETA_CSV) -> pd.DataFrame:
    """Lee todos los CSV horarios de 2019-2025 y devuelve una única tabla.

    - 2019-2024: un CSV por mes dentro de datos/csv/<año>/
    - 2025: está dentro de datos/csv/desde_2025.csv, que también trae 2026;
      nos quedamos solo con los años de ANIOS.

    Se lee todo como texto (dtype=str) para que pandas no adivine tipos:
    así los valores "00017" (2019-2021) y "17" (2022 en adelante) se tratan
    igual y los convertimos a número de forma explícita más adelante.
    """
    ficheros = sorted(carpeta.glob("20*/*.csv")) + [carpeta / "desde_2025.csv"]

    tablas = []
    for fichero in ficheros:
        # sep=";" -> el separador es punto y coma
        # encoding="utf-8-sig" -> ignora el BOM del CSV de 2025 (y no afecta a los demás)
        tabla = pd.read_csv(fichero, sep=";", encoding="utf-8-sig", dtype=str)
        tablas.append(tabla)

    # concat apila las tablas una debajo de otra (tienen las mismas columnas)
    df = pd.concat(tablas, ignore_index=True)

    # Quitamos los años fuera del periodo (los meses de 2026 del CSV de 2025)
    df = df[df["ANO"].astype(int).isin(ANIOS)]
    return df


# --------------------------------------------------------------------------
# Paso 2: quedarnos con un contaminante
# --------------------------------------------------------------------------
def filtrar_contaminante(df: pd.DataFrame, magnitud: int = 8) -> pd.DataFrame:
    """Devuelve solo las filas de un contaminante (por defecto 8 = NO2)."""
    return df[df["MAGNITUD"].astype(int) == magnitud]


# --------------------------------------------------------------------------
# Paso 3: de formato ancho (1 fila = 1 día) a formato largo (1 fila = 1 hora)
# --------------------------------------------------------------------------
def pasar_a_formato_largo(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte las 24 parejas (Hxx, Vxx) en filas.

    Entrada (ancho), una fila por día:
        ESTACION  ANO  MES  DIA  H01  V01  H02  V02 ...
        4         2024 01   01   12   V    10   V   ...

    Salida (largo), una fila por hora:
        estacion  magnitud  fecha       hora  valor  validez
        4         8         2024-01-01  1     12.0   V
        4         8         2024-01-01  2     10.0   V
    """
    # melt "derrite" las columnas H01..H24 en dos columnas: el nombre de la
    # columna original (hora) y su contenido (valor). Lo hacemos dos veces:
    # una para los valores y otra para los códigos de validez.
    valores = df.melt(id_vars=COLUMNAS_ID, value_vars=COLUMNAS_H,
                      var_name="hora", value_name="valor")
    validez = df.melt(id_vars=COLUMNAS_ID, value_vars=COLUMNAS_V,
                      var_name="hora", value_name="validez")

    # "H01" -> 1, "V01" -> 1, para poder unir ambas tablas por la hora
    valores["hora"] = valores["hora"].str[1:].astype(int)
    validez["hora"] = validez["hora"].str[1:].astype(int)

    # merge une las dos tablas por las columnas comunes (como un BUSCARV)
    largo = valores.merge(validez, on=COLUMNAS_ID + ["hora"])

    # Tipos y nombres cómodos
    largo["fecha"] = pd.to_datetime(
        largo["ANO"] + "-" + largo["MES"] + "-" + largo["DIA"], format="%Y-%m-%d"
    )
    largo["estacion"] = largo["ESTACION"].astype(int)
    largo["magnitud"] = largo["MAGNITUD"].astype(int)
    largo["valor"] = pd.to_numeric(largo["valor"]).astype(float)  # "00017" -> 17.0

    return largo[["estacion", "magnitud", "fecha", "hora", "valor", "validez"]]


# --------------------------------------------------------------------------
# Paso 4: quedarnos solo con los datos válidos  ->  LO ESCRIBE SERGIO
# --------------------------------------------------------------------------
def filtrar_validos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo las filas cuya columna 'validez' es "V".

    Además, imprime un pequeño resumen: cuántas filas había, cuántas se
    quedan y cuántas se descartan.
    """
    # TODO (Sergio): escribe aquí el filtro y el resumen
    raise NotImplementedError("Paso 4 pendiente")


# --------------------------------------------------------------------------
# Prueba rápida: ejecuta este archivo (botón Run de PyCharm o
# `python src/carga.py` desde la raíz) para ver cada paso.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    datos = leer_csv_horarios()
    print("Paso 1 - filas leídas (1 fila = 1 día, estación y contaminante):", len(datos))

    no2 = filtrar_contaminante(datos, magnitud=8)
    print("Paso 2 - filas de NO2:", len(no2))

    largo = pasar_a_formato_largo(no2)
    print("Paso 3 - filas en formato largo (1 fila = 1 hora):", len(largo))
    print(largo.head())

    validos = filtrar_validos(largo)
    print("Paso 4 - filas válidas:", len(validos))
    print(validos.head())
