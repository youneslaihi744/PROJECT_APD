# Detección de outliers

Script `deteccion_outliers.py`: busca valores atípicos con cuatro métodos y añade el resultado como columnas nuevas al CSV.

| Método | Tipo | Qué columnas usa |
|---|---|---|
| IQR (diagrama de cajas) | univariante (cada columna por separado) | **todas** las columnas numéricas |
| Isolation Forest | multivariante | las indicadas en `--columnas` |
| LOF (Local Outlier Factor) | multivariante | las indicadas en `--columnas` |
| DBSCAN | multivariante | las indicadas en `--columnas` |

## Requisitos

Python 3 con `pandas`, `numpy`, `scikit-learn` y `matplotlib`:

```
pip install pandas numpy scikit-learn matplotlib
```

## Uso

Desde la carpeta raíz del proyecto (`PROJECT_APD-main`):

```
python scripts\deteccion_outliers\deteccion_outliers.py --input processed_csv\temporal\<csv_de_caracteristicas>.csv
```

El CSV de entrada debe usar `;` como separador (se puede cambiar con `--sep`). Acepta decimales con punto o con coma (`5.42` o `5,42`).

## Argumentos

| Argumento | Obligatorio | Por defecto | Descripción |
|---|---|---|---|
| `--input RUTA` | sí | — | CSV de entrada. |
| `--output RUTA` | no | `<input>_outliers.csv` (junto al de entrada) | CSV de salida con las columnas nuevas. |
| `--figdir CARPETA` | no | `outliers_graficos` (junto al CSV de salida) | Carpeta donde se guardan los gráficos y los resúmenes. |
| `--columnas COL1 COL2 ...` | no | ver abajo | Columnas para Isolation Forest, LOF y DBSCAN. |
| `--grupo COLUMNA` | no | `Periodo` | Columna con la que se separan los datos: cada grupo (cada año) se analiza por separado. |
| `--sin-grupo` | no | desactivado | Analiza todas las filas juntas, sin separar por grupo. |
| `--contaminacion VALOR` | no | `0.05` | Proporción de filas que Isolation Forest y LOF marcan como outlier en cada grupo (0.05 = 5 %). También acepta `auto`. |
| `--sep SEPARADOR` | no | `;` | Separador del CSV de entrada y de salida. |

### `--columnas`

Acepta **una o más** columnas separadas por espacios, sin límite:

```
# sin --columnas: usa las 5 columnas por defecto
python scripts\deteccion_outliers\deteccion_outliers.py --input datos.csv

# solo 2 columnas
python scripts\deteccion_outliers\deteccion_outliers.py --input datos.csv --columnas precio_m2_vivienda alquiler_mensual_mediana

# 4 columnas
python scripts\deteccion_outliers\deteccion_outliers.py --input datos.csv --columnas precio_m2_vivienda alquiler_mensual_mediana rentabilidad_bruta_alquiler num_hogares
```

Si no se indica, se usan estas 5 (las que existan en el CSV):

- `precio_m2_vivienda`
- `alquiler_mensual_mediana`
- `alquiler_anual_m2_mediana`
- `rentabilidad_bruta_alquiler`
- `dispersion_mensual_relativa`

Si se indica, **sustituye** a la lista por defecto (no se suma a ella). Si una columna no existe o no es numérica, el script se detiene y muestra las columnas disponibles.

Cómo elegirlas:

- Elige columnas relacionadas con la pregunta que quieres responder (p. ej. precio y alquiler). Una columna sin relación cambia el resultado: Isolation Forest gasta cortes en ella, y en LOF y DBSCAN entra en el cálculo de todas las distancias.
- Evita columnas redundantes: `ratio_precio_alquiler` es la inversa de `rentabilidad_bruta_alquiler`, así que meter las dos cuenta lo mismo dos veces.
- Los modelos solo usan las filas que tienen **todas** las columnas elegidas sin valores vacíos. Una columna que solo existe algunos años (p. ej. `pct_viviendas_vacias`) deja fuera muchas filas.

### `--grupo` / `--sin-grupo`

Por defecto el análisis se hace **por año** (`Periodo`): los precios suben con el tiempo, y mezclando años los "outliers" serían simplemente los años más caros. Un grupo con menos de 10 filas completas se omite (en estos datos, 2010 y 2025, que no tienen datos de alquiler).

### `--contaminacion`

Fija cuántas filas marcan como outlier Isolation Forest y LOF en cada grupo. Con `0.05` y unos 107 municipios por año, cada método marca unos 6 por año. Con `auto` Isolation Forest marcaba alrededor del 20 % de las filas, por eso el valor por defecto es `0.05`. No afecta a DBSCAN ni al IQR.

## Salidas

```
<carpeta del output>/
├── <input>_outliers.csv              CSV original + columnas nuevas
└── outliers_graficos/
    ├── boxplots/<columna>.png         un diagrama de cajas por columna numérica (una caja por año)
    ├── dbscan_kdist_<año>.png         curva k-distancia usada para elegir eps de DBSCAN
    ├── resumen_outliers_iqr.csv       un registro por cada outlier IQR
    └── resumen_multivariante.csv      filas marcadas por algún método multivariante
```

### `<input>_outliers.csv`

Todas las columnas del CSV de entrada se mantienen sin cambios (las que venían con coma decimal se escriben con punto). Se añaden estas:

| Columna | Valores | Significado |
|---|---|---|
| `iqr_n_outliers` | entero ≥ 0 | En cuántas columnas numéricas está el valor de esa fila fuera de [Q1 − 1.5·IQR, Q3 + 1.5·IQR] de su año. |
| `iqr_columnas` | texto | Nombres de esas columnas separados por `\|` (p. ej. `precio_m2_vivienda\|precio_m2_piso`). Vacío si no hay ninguna. |
| `if_score` | número | Puntuación de anomalía de Isolation Forest. **Mayor = más anómalo.** Sirve para ordenar; solo se compara entre filas del mismo año. |
| `if_outlier` | 0 / 1 | 1 si Isolation Forest la marca como outlier (las del `--contaminacion` % con mayor `if_score`). |
| `lof_score` | número ≥ ~1 | Factor LOF: densidad de los vecinos dividida entre la del punto. **≈ 1 normal; > 1.5 claramente anómalo.** |
| `lof_outlier` | 0 / 1 | 1 si LOF la marca como outlier. |
| `dbscan_cluster` | entero | Grupo asignado por DBSCAN dentro de su año (0, 1, …). **−1 = ruido** (no pertenece a ningún grupo). |
| `dbscan_outlier` | 0 / 1 | 1 si `dbscan_cluster` = −1. |
| `n_metodos_outlier` | 0 – 3 | Cuántos de los tres métodos multivariantes (IF, LOF, DBSCAN) la marcan. **3 = outlier fiable; 1 = dudoso.** |

Las columnas multivariantes (`if_*`, `lof_*`, `dbscan_*`, `n_metodos_outlier`) quedan **vacías** en las filas que no se pudieron analizar: les falta alguna de las `--columnas` o su año tiene menos de 10 filas completas.

### `resumen_outliers_iqr.csv`

Una fila por cada valor fuera de los límites IQR (un municipio puede aparecer varias veces, una por columna).

| Columna | Significado |
|---|---|
| `grupo` | Año (o `todos` con `--sin-grupo`). |
| `Municipio` | Municipio. |
| `columna` | Columna en la que el valor es atípico. |
| `valor` | Valor del municipio en esa columna. |
| `lim_inf` | Q1 − 1.5·IQR de esa columna en ese año. |
| `lim_sup` | Q3 + 1.5·IQR de esa columna en ese año. |
| `tipo` | `alto` (por encima de `lim_sup`) o `bajo` (por debajo de `lim_inf`). |

### `resumen_multivariante.csv`

Solo las filas con `n_metodos_outlier` ≥ 1, ordenadas de más a menos fiable (primero por `n_metodos_outlier` y luego por `if_score`).

| Columna | Significado |
|---|---|
| `Municipio`, `Periodo` | Identificación de la fila. |
| *(columnas de `--columnas`)* | Valores originales usados por los modelos, para ver por qué es raro. |
| `if_score`, `lof_score`, `dbscan_cluster`, `n_metodos_outlier` | Igual que en el CSV principal. |

## Cómo interpretar los resultados

1. Empieza por `resumen_multivariante.csv`: las filas con `n_metodos_outlier` = 3 son las más claras.
2. Mira sus valores en las columnas del modelo y `iqr_columnas` en el CSV principal para entender **por qué** son raras.
3. Decide en cada caso:
   - **Error** (dato mal cargado, municipio mal cruzado): corregir o eliminar.
   - **Real** (p. ej. Eivissa o Sant Cugat, caros todos los años): **conservar** y comentarlo en el análisis.
4. Si DBSCAN marca demasiadas o muy pocas filas, revisa `dbscan_kdist_<año>.png`: la línea roja es el `eps` elegido (el "codo" de la curva).

## Detalles técnicos

- Antes de los modelos multivariantes las columnas se escalan con `RobustScaler` (mediana e IQR) para que todas pesen parecido en las distancias.
- Isolation Forest: 300 árboles, `random_state=42` (resultados reproducibles).
- LOF: `n_neighbors = min(20, n − 1)`.
- DBSCAN: `min_samples = max(2 × nº de columnas, 4)`; `eps` = codo de la curva de distancias al vecino `min_samples`-ésimo.
