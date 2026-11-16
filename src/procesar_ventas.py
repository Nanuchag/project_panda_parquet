"""Adquisición, limpieza, integración y exportación de datos de ventas.

Fuentes:
- data/raw/transacciones.csv
- data/raw/maestro_productos.xlsx

Salida:
- data/processed/ventas_normalizadas.parquet
"""

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUTA_TRANSACCIONES = ROOT / "data" / "raw" / "transacciones.csv"
RUTA_PRODUCTOS = ROOT / "data" / "raw" / "maestro_productos.xlsx"
RUTA_SALIDA = ROOT / "data" / "processed" / "ventas_normalizadas.parquet"


CAMPOS_CRITICOS_FINAL = [
    "id_producto",
    "cantidad",
    "fecha",
    "nombre_producto",
    "precio_unitario",
    "total_venta",
]


def normalizar_id(serie: pd.Series) -> pd.Series:
    """Convierte IDs numéricos a nullable Int64 para igualar tipos entre fuentes."""
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


def cargar_transacciones(ruta: Path) -> tuple[pd.DataFrame, int]:
    """Lee CSV, normaliza tipos y elimina registros sin datos transaccionales críticos."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo CSV: {ruta}")

    df = pd.read_csv(ruta, dtype={"id_producto": "string"})
    df.columns = df.columns.str.strip()

    requeridas = {"id_producto", "cantidad", "fecha"}
    faltantes = requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en transacciones.csv: {sorted(faltantes)}")

    filas_iniciales = len(df)
    df["id_producto"] = normalizar_id(df["id_producto"])
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # Se descartan filas sin ID, cantidad o fecha; también cantidades no positivas.
    df = df.dropna(subset=["id_producto", "cantidad", "fecha"])
    df = df.loc[df["cantidad"] > 0].copy()
    df["cantidad"] = df["cantidad"].astype("int64")

    eliminadas = filas_iniciales - len(df)
    return df, eliminadas


def cargar_productos(ruta: Path) -> tuple[pd.DataFrame, int]:
    """Lee Excel, normaliza tipos y depura el catálogo de productos."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo Excel: {ruta}")

    # pandas administra el lector de Excel; openpyxl funciona como motor de lectura.
    df = pd.read_excel(ruta, engine="openpyxl", dtype={"id_producto": "string"})
    df.columns = df.columns.str.strip()

    requeridas = {"id_producto", "nombre_producto", "precio_unitario"}
    faltantes = requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en maestro_productos.xlsx: {sorted(faltantes)}")

    filas_iniciales = len(df)
    df["id_producto"] = normalizar_id(df["id_producto"])
    df["nombre_producto"] = df["nombre_producto"].astype("string").str.strip()
    df["nombre_producto"] = df["nombre_producto"].replace("", pd.NA)
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce")

    df = df.dropna(subset=["id_producto", "nombre_producto", "precio_unitario"])
    df = df.loc[df["precio_unitario"] > 0].copy()
    # Un ID debe identificar un único producto para evitar duplicar ventas en el merge.
    df = df.drop_duplicates(subset=["id_producto"], keep="last")

    eliminadas = filas_iniciales - len(df)
    return df, eliminadas


def procesar_ventas() -> pd.DataFrame:
    """Ejecuta el pipeline completo y devuelve el dataset consolidado."""
    transacciones, transacciones_eliminadas = cargar_transacciones(RUTA_TRANSACCIONES)
    productos, productos_eliminados = cargar_productos(RUTA_PRODUCTOS)

    # El tipo de id_producto ya está homogeneizado como Int64 en ambas fuentes.
    resultado = transacciones.merge(
        productos,
        on="id_producto",
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    sin_producto = int((resultado["_merge"] != "both").sum())
    resultado = resultado.loc[resultado["_merge"] == "both"].drop(columns="_merge")

    # Columna calculada solicitada por la consigna.
    resultado["total_venta"] = resultado["cantidad"] * resultado["precio_unitario"]

    columnas_finales = [
        "id_producto",
        "cantidad",
        "fecha",
        "nombre_producto",
        "precio_unitario",
        "total_venta",
    ]
    resultado = resultado[columnas_finales].sort_values(
        by=["fecha", "id_producto"]
    ).reset_index(drop=True)

    # Control de calidad: ningún campo crítico puede quedar nulo.
    nulos_criticos = resultado[CAMPOS_CRITICOS_FINAL].isna().sum()
    if nulos_criticos.any():
        detalle = nulos_criticos[nulos_criticos > 0].to_dict()
        raise ValueError(f"El dataset final contiene nulos en campos críticos: {detalle}")

    if not pd.api.types.is_datetime64_any_dtype(resultado["fecha"]):
        raise TypeError("La columna 'fecha' no quedó en formato datetime.")

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_parquet(RUTA_SALIDA, engine="pyarrow", index=False)

    # Relectura del Parquet para comprobar que el archivo de salida es válido.
    verificacion = pd.read_parquet(RUTA_SALIDA, engine="pyarrow")
    if len(verificacion) != len(resultado):
        raise RuntimeError("La verificación del Parquet detectó una cantidad de filas diferente.")
    if verificacion[CAMPOS_CRITICOS_FINAL].isna().any().any():
        raise RuntimeError("La verificación del Parquet encontró valores nulos críticos.")

    print("PROCESO FINALIZADO CORRECTAMENTE")
    print(f"Filas válidas de transacciones: {len(transacciones)}")
    print(f"Filas eliminadas de transacciones por datos críticos inválidos: {transacciones_eliminadas}")
    print(f"Filas válidas del catálogo: {len(productos)}")
    print(f"Filas eliminadas del catálogo por datos inválidos/duplicados: {productos_eliminados}")
    print(f"Transacciones sin coincidencia en el catálogo: {sin_producto}")
    print(f"Filas del dataset final: {len(resultado)}")
    print(f"Archivo Parquet generado: {RUTA_SALIDA.relative_to(ROOT)}")
    print("Tipos de datos finales:")
    print(resultado.dtypes.to_string())

    return resultado


if __name__ == "__main__":
    try:
        procesar_ventas()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
