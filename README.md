# Pre-entrega 2 — Adquisición y Normalización con Pandas

## Objetivo

Integrar datos de ventas provenientes de dos fuentes con formatos diferentes —un CSV de transacciones y un Excel con el maestro de productos—, limpiar y normalizar sus campos, calcular el importe total de cada venta y exportar el resultado en formato Parquet.

## Estructura del repositorio

```text
pre_entrega_2_pandas/
├── data/
│   ├── raw/
│   │   ├── transacciones.csv
│   │   └── maestro_productos.xlsx
│   └── processed/
│       └── ventas_normalizadas.parquet
├── src/
│   └── procesar_ventas.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Fuentes de datos

**`data/raw/transacciones.csv`** contiene:

- `id_producto`: identificador del producto.
- `cantidad`: unidades vendidas.
- `fecha`: fecha de la transacción.

**`data/raw/maestro_productos.xlsx`** contiene:

- `id_producto`: identificador del producto.
- `nombre_producto`: descripción del producto.
- `precio_unitario`: precio por unidad.

Los archivos incluidos son datos ficticios de ejemplo. El CSV contiene algunas filas con datos incompletos y un producto que no existe en el catálogo para mostrar cómo se controlan los problemas de calidad.

## Requisitos

- Python 3.10 o superior.
- pandas: lectura, limpieza, transformación y combinación de datos.
- openpyxl: motor para leer el archivo Excel `.xlsx`.
- pyarrow: escritura y lectura del formato Parquet.

## Instalación y ejecución

Desde la carpeta raíz del repositorio:

### 1. Crear y activar un entorno virtual

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar las librerías

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Ejecutar el proceso

```bash
python src/procesar_ventas.py
```

El script lee las fuentes desde `data/raw/` y genera `data/processed/ventas_normalizadas.parquet`. Las rutas son relativas al proyecto, por lo que no es necesario modificarlas al clonar el repositorio.

## Proceso de adquisición y transformación

1. **Lectura:** `pandas.read_csv()` carga el CSV y `pandas.read_excel()` carga el Excel usando `openpyxl` como motor.
2. **Normalización de tipos:** `id_producto` se convierte a tipo entero nullable (`Int64`) en ambas fuentes; `cantidad` y `precio_unitario` se convierten a valores numéricos; `fecha` se convierte con `pandas.to_datetime()` a `datetime64`.
3. **Tratamiento de nulos:** se eliminan las transacciones sin `id_producto`, `cantidad` o `fecha`, y las cantidades no positivas. Del catálogo se eliminan registros sin ID, nombre o precio válido, precios no positivos y duplicados de `id_producto`.
4. **Integración:** se realiza un `merge` `left` por `id_producto`, con `validate="many_to_one"` para comprobar que cada ID del catálogo identifique un solo producto. Las transacciones sin coincidencia se excluyen del dataset consolidado.
5. **Columna calculada:** `total_venta = cantidad * precio_unitario`.
6. **Control de calidad:** el script verifica que los campos críticos no tengan valores nulos y que `fecha` conserve el tipo datetime.
7. **Exportación:** `DataFrame.to_parquet()` genera el archivo Parquet. Luego se vuelve a leer para validar que el archivo se haya creado correctamente y conserve los registros.

## Resultado esperado

El archivo `data/processed/ventas_normalizadas.parquet` contiene las columnas:

| Columna | Descripción |
|---|---|
| `id_producto` | ID del producto |
| `cantidad` | Unidades vendidas |
| `fecha` | Fecha de la transacción (`datetime`) |
| `nombre_producto` | Nombre obtenido del catálogo |
| `precio_unitario` | Precio por unidad |
| `total_venta` | Cantidad por precio unitario |

El programa imprime un resumen con filas válidas, registros descartados, transacciones sin producto asociado, cantidad final de filas y tipos de datos.

# project_panda_parquet
