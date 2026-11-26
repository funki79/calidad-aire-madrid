"""
Funciones de carga y limpieza de los datos horarios de calidad del aire de Madrid.

Flujo:
    1. leer_csv_horarios()      -> lee todos los CSV y los junta (formato ancho)
    2. filtrar_contaminante()   -> se queda con un contaminante (8 = NO2)
    3. pasar_a_formato_largo()  -> una fila por hora en vez de una por día
    4. filtrar_validos()        -> se queda solo con los datos validados ("V")
    5. anadir_fecha_hora()      -> une fecha y hora en una sola columna
    7. anadir_estaciones()      -> añade nombre y tipo de cada estación

    cargar_no2() ejecuta todos los pasos seguidos.
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
# Paso 4: quedarnos solo con los datos válidos
# --------------------------------------------------------------------------
def filtrar_validos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo las filas cuya columna 'validez' es "V".

    Además, imprime un pequeño resumen: cuántas filas había, cuántas se
    quedan y cuántas se descartan.
    """
    # 1) Máscara: una columna de True/False, True donde validez es "V"
    es_valido = df["validez"] == "V"

    # 2) Filtro: nos quedamos solo con las filas donde la máscara es True
    validos = df[es_valido]

    # 3) Resumen: contamos filas antes y después
    total = len(df)
    quedan = len(validos)
    descartadas = total - quedan
    print(f"Filas totales: {total}")
    print(f"Filas válidas: {quedan}")
    print(f"Descartadas:   {descartadas} ({descartadas / total:.1%})")

    # 4) Devolvemos la tabla filtrada
    return validos


# --------------------------------------------------------------------------
# Paso 5: una sola columna con la fecha y la hora
# --------------------------------------------------------------------------
def anadir_fecha_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Crea la columna 'fecha_hora' a partir de 'fecha' y 'hora'.

    Según la documentación oficial, H24 es la media de 23:00 a 24:00, así que
    Hk es la media del intervalo que va de la hora (k-1) a la hora k.
    Etiquetamos cada dato con el INICIO de su intervalo:
        H01 -> 00:00   (media de 00:00 a 01:00)
        H24 -> 23:00   (media de 23:00 a 24:00, mismo día)
    Así ningún dato "salta" al día siguiente y la hora del día va de 0 a 23.

    Es hora local de Madrid, tal como la publica el Ayuntamiento (sin zona
    horaria). Los días de cambio de hora tienen 23 o 25 horas; el Ayuntamiento
    elimina la hora repetida, así que no hay duplicados.
    """
    df = df.copy()  # trabajamos sobre una copia para no tocar la tabla original
    # pd.to_timedelta convierte un número en una duración ("3 horas")
    df["fecha_hora"] = df["fecha"] + pd.to_timedelta(df["hora"] - 1, unit="h")
    return df


# --------------------------------------------------------------------------
# Paso 7: nombre y tipo de cada estación
# --------------------------------------------------------------------------
def leer_estaciones(ruta: Path = RAIZ / "datos" / "estaciones.csv") -> pd.DataFrame:
    """Lee el listado oficial de estaciones y deja solo las columnas útiles."""
    est = pd.read_csv(ruta, sep=";", encoding="utf-8-sig")
    est = est.rename(columns={
        "CODIGO_CORTO": "estacion",
        "ESTACION": "nombre_estacion",
        "NOM_TIPO": "tipo_estacion",
        "LATITUD": "latitud",
        "LONGITUD": "longitud",
    })
    return est[["estacion", "nombre_estacion", "tipo_estacion", "latitud", "longitud"]]


def anadir_estaciones(df: pd.DataFrame) -> pd.DataFrame:
    """Añade nombre y tipo de estación (equivale a un BUSCARV en Excel).

    how="left" -> se conservan todas las filas de df aunque una estación no
    estuviera en el listado (en ese caso el nombre quedaría vacío).
    """
    est = leer_estaciones()[["estacion", "nombre_estacion", "tipo_estacion"]]
    return df.merge(est, on="estacion", how="left")


# --------------------------------------------------------------------------
# Todo seguido
# --------------------------------------------------------------------------
def cargar_no2() -> pd.DataFrame:
    """Devuelve la tabla limpia de NO2 2019-2025, una fila por hora y estación.

    Columnas: fecha_hora, estacion, nombre_estacion, tipo_estacion, valor (µg/m³)
    """
    df = leer_csv_horarios()
    df = filtrar_contaminante(df, magnitud=8)
    df = pasar_a_formato_largo(df)
    df = filtrar_validos(df)
    df = anadir_fecha_hora(df)
    df = anadir_estaciones(df)
    return df[["fecha_hora", "estacion", "nombre_estacion", "tipo_estacion", "valor"]]


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

    con_fecha = anadir_fecha_hora(validos)
    print("Paso 5 - primeras horas de un día:")
    print(con_fecha.sort_values(["estacion", "fecha_hora"]).head(3))

    final = anadir_estaciones(con_fecha)
    print("Paso 7 - estaciones sin nombre:", final["nombre_estacion"].isna().sum())
    print(final.head())
