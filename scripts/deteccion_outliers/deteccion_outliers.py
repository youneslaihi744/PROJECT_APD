"""
Deteccion de outliers: IQR (univariante) + Isolation Forest, LOF y DBSCAN (multivariantes).

Uso basico:
    python scripts/deteccion_outliers/deteccion_outliers.py --input processed_csv/temporal/aspectos_sociales_caracteristicas.csv

Opciones utiles:
    --columnas a b c      columnas para los modelos multivariantes (por defecto: precio/alquiler)
    --sin-grupo           no separar por año (mezcla todos los periodos)
    --contaminacion 0.05  proporcion esperada de outliers en IF y LOF (por defecto 0.05; o "auto")
    --output ruta.csv     CSV de salida (por defecto <input>_outliers.csv)
    --figdir carpeta      carpeta de graficos (por defecto <carpeta del output>/outliers_graficos)

Salida: el mismo CSV con columnas nuevas:
    iqr_n_outliers, iqr_columnas        -> en cuantas/cuales columnas el valor cae fuera de [Q1-1.5IQR, Q3+1.5IQR]
    if_score, if_outlier                -> Isolation Forest (score mayor = mas anomalo)
    lof_score, lof_outlier              -> Local Outlier Factor (~1 normal, >1.5 claramente anomalo)
    dbscan_cluster, dbscan_outlier      -> cluster de DBSCAN (-1 = ruido = outlier)
    n_metodos_outlier                   -> cuantos de los 3 multivariantes lo marcan (0-3)
Ademas genera en la carpeta de graficos:
    boxplots/<columna>.png              -> diagrama de cajas por año
    dbscan_kdist_<grupo>.png            -> curva k-distancia usada para elegir eps
    resumen_outliers_iqr.csv            -> listado de cada outlier IQR con sus limites
    resumen_multivariante.csv           -> filas marcadas por al menos un metodo multivariante
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana, solo guarda PNG
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.preprocessing import RobustScaler

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Columnas que identifican la fila: nunca se analizan como variables
COLUMNAS_ID = {"Municipio", "Periodo", "cod_municipio", "cod_provincia", "cod_ccaa",
               "municipio", "provincia", "ccaa"}

# Subconjunto por defecto para los modelos multivariantes: variables de precio y alquiler
# (no redundantes: ratio_precio_alquiler es la inversa de rentabilidad, no se incluye)
COLUMNAS_MODELO_DEFECTO = [
    "precio_m2_vivienda",
    "alquiler_mensual_mediana",
    "alquiler_anual_m2_mediana",
    "rentabilidad_bruta_alquiler",
    "dispersion_mensual_relativa",
]


def leer_csv(ruta, sep):
    df = pd.read_csv(ruta, sep=sep, encoding="utf-8")
    # Pentaho a veces escribe decimales con coma ("5,42"): convertir texto numerico a float
    for c in df.columns:
        if c in COLUMNAS_ID or pd.api.types.is_numeric_dtype(df[c]):
            continue
        convertida = pd.to_numeric(df[c].astype(str).str.strip().str.replace(",", ".", regex=False),
                                   errors="coerce")
        # solo se acepta la conversion si no se pierden valores que existian
        if convertida.notna().sum() == df[c].notna().sum():
            df[c] = convertida
    return df


# ----------------------------------------------------------------------------- IQR
def iqr_outliers(df, columnas, grupo, figdir):
    """Marca outliers univariantes por columna (dentro de cada grupo) y dibuja boxplots."""
    box_dir = figdir / "boxplots"
    box_dir.mkdir(parents=True, exist_ok=True)

    flags = pd.DataFrame(False, index=df.index, columns=columnas)
    filas_resumen = []
    grupos = df.groupby(grupo) if grupo else [("todos", df)]

    for g, sub in grupos:
        for c in columnas:
            x = sub[c].dropna()
            if len(x) < 4:
                continue
            q1, q3 = x.quantile([0.25, 0.75])
            iqr = q3 - q1
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            fuera = sub[c].notna() & ((sub[c] < lo) | (sub[c] > hi))
            flags.loc[sub.index[fuera], c] = True
            for i in sub.index[fuera]:
                filas_resumen.append({
                    "grupo": g, "Municipio": df.at[i, "Municipio"] if "Municipio" in df else i,
                    "columna": c, "valor": df.at[i, c], "lim_inf": lo, "lim_sup": hi,
                    "tipo": "alto" if df.at[i, c] > hi else "bajo",
                })

    # Boxplots: uno por columna, una caja por año
    for c in columnas:
        if grupo:
            datos = [(g, s[c].dropna().values) for g, s in df.groupby(grupo)]
            datos = [(g, v) for g, v in datos if len(v) > 0]
        else:
            datos = [("todos", df[c].dropna().values)]
        if not datos:
            continue
        fig, ax = plt.subplots(figsize=(max(6, 0.6 * len(datos) + 2), 4.5))
        ax.boxplot([v for _, v in datos], whis=1.5, flierprops=dict(marker="o", markersize=3,
                                                                     markerfacecolor="tab:red", alpha=.6))
        ax.set_xticks(range(1, len(datos) + 1), [str(g) for g, _ in datos], rotation=45)
        ax.set_title(f"{c}  (bigotes = 1.5·IQR, puntos rojos = outliers)")
        ax.set_xlabel(grupo or "")
        ax.grid(axis="y", alpha=.3)
        fig.tight_layout()
        fig.savefig(box_dir / f"{c}.png", dpi=110)
        plt.close(fig)

    df["iqr_n_outliers"] = flags.sum(axis=1)
    df["iqr_columnas"] = flags.apply(lambda r: "|".join(r.index[r]), axis=1)
    return pd.DataFrame(filas_resumen)


# ----------------------------------------------------------------------------- DBSCAN eps
def elegir_eps(X, min_samples, ruta_png, titulo):
    """Heuristica k-distancia: distancia al k-esimo vecino ordenada; eps = 'codo' de la curva."""
    nn = NearestNeighbors(n_neighbors=min_samples).fit(X)
    kdist = np.sort(nn.kneighbors(X)[0][:, -1])
    # codo = punto mas alejado de la recta que une el primer y el ultimo punto
    n = len(kdist)
    p1, p2 = np.array([0, kdist[0]]), np.array([n - 1, kdist[-1]])
    pts = np.column_stack([np.arange(n), kdist])
    d = np.abs(np.cross(p2 - p1, pts - p1)) / (np.linalg.norm(p2 - p1) + 1e-12)
    eps = float(kdist[int(np.argmax(d))]) if kdist[-1] > kdist[0] else float(kdist[-1]) or 0.5

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(kdist)
    ax.axhline(eps, color="tab:red", ls="--", label=f"eps = {eps:.2f}")
    ax.set_title(f"k-distancia (k={min_samples}) {titulo}")
    ax.set_xlabel("puntos ordenados")
    ax.set_ylabel(f"distancia al vecino {min_samples}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=110)
    plt.close(fig)
    return eps


# ----------------------------------------------------------------------------- multivariante
def multivariante(df, columnas, grupo, contaminacion, figdir, semilla=42):
    for c in ["if_score", "if_outlier", "lof_score", "lof_outlier",
              "dbscan_cluster", "dbscan_outlier"]:
        df[c] = np.nan

    grupos = df.groupby(grupo) if grupo else [("todos", df)]
    for g, sub in grupos:
        sub = sub[columnas].dropna()          # los modelos necesitan filas completas
        n, p = sub.shape
        if n < 10:
            print(f"  [{g}] solo {n} filas completas -> se omite")
            continue

        X = RobustScaler().fit_transform(sub.values)   # escala robusta (mediana/IQR)

        # Isolation Forest: aisla puntos con cortes aleatorios; los raros se aislan antes
        iso = IsolationForest(n_estimators=300, contamination=contaminacion, random_state=semilla)
        etiquetas = iso.fit_predict(X)
        df.loc[sub.index, "if_score"] = -iso.score_samples(X)       # mayor = mas anomalo
        df.loc[sub.index, "if_outlier"] = (etiquetas == -1).astype(int)

        # LOF: compara la densidad local de un punto con la de sus vecinos
        k = min(20, n - 1)
        lof = LocalOutlierFactor(n_neighbors=k, contamination=contaminacion)
        etiquetas = lof.fit_predict(X)
        df.loc[sub.index, "lof_score"] = -lof.negative_outlier_factor_  # ~1 normal
        df.loc[sub.index, "lof_outlier"] = (etiquetas == -1).astype(int)

        # DBSCAN: agrupa por densidad; lo que no cae en ningun cluster es ruido (-1)
        min_samples = max(2 * p, 4)
        eps = elegir_eps(X, min_samples, figdir / f"dbscan_kdist_{g}.png", f"[{g}]")
        lab = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
        df.loc[sub.index, "dbscan_cluster"] = lab
        df.loc[sub.index, "dbscan_outlier"] = (lab == -1).astype(int)

        print(f"  [{g}] n={n}  IF={int((df.loc[sub.index, 'if_outlier'] == 1).sum())}  "
              f"LOF={int((df.loc[sub.index, 'lof_outlier'] == 1).sum())}  "
              f"DBSCAN ruido={int((lab == -1).sum())} (eps={eps:.2f}, clusters={len(set(lab) - {-1})})")

    marcas = df[["if_outlier", "lof_outlier", "dbscan_outlier"]]
    df["n_metodos_outlier"] = marcas.sum(axis=1, min_count=1)
    for c in ["if_outlier", "lof_outlier", "dbscan_cluster", "dbscan_outlier", "n_metodos_outlier"]:
        df[c] = df[c].astype("Int64")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output")
    ap.add_argument("--figdir")
    ap.add_argument("--sep", default=";")
    ap.add_argument("--columnas", nargs="+", help="columnas para IF/LOF/DBSCAN")
    ap.add_argument("--grupo", default="Periodo", help="columna por la que separar (por defecto Periodo)")
    ap.add_argument("--sin-grupo", action="store_true", help="no separar por grupo")
    ap.add_argument("--contaminacion", default="0.05",
                    help="'auto' o proporcion esperada de outliers (p.ej. 0.05)")
    args = ap.parse_args()

    entrada = Path(args.input)
    salida = Path(args.output) if args.output else entrada.with_name(entrada.stem + "_outliers.csv")
    figdir = Path(args.figdir) if args.figdir else salida.parent / "outliers_graficos"
    figdir.mkdir(parents=True, exist_ok=True)
    contaminacion = args.contaminacion if args.contaminacion == "auto" else float(args.contaminacion)

    df = leer_csv(entrada, args.sep)
    grupo = None if args.sin_grupo or args.grupo not in df.columns else args.grupo

    numericas = [c for c in df.columns if c not in COLUMNAS_ID and pd.api.types.is_numeric_dtype(df[c])]
    columnas_modelo = args.columnas or [c for c in COLUMNAS_MODELO_DEFECTO if c in df.columns]
    faltan = [c for c in columnas_modelo if c not in numericas]
    if faltan:
        sys.exit(f"Columnas no encontradas o no numericas: {faltan}\nDisponibles: {numericas}")

    print(f"Filas: {len(df)}  | grupo: {grupo or 'ninguno'}")
    print(f"IQR sobre {len(numericas)} columnas numericas")
    resumen_iqr = iqr_outliers(df, numericas, grupo, figdir)

    print(f"Multivariante sobre: {columnas_modelo}")
    multivariante(df, columnas_modelo, grupo, contaminacion, figdir)

    df.to_csv(salida, sep=args.sep, index=False, encoding="utf-8")
    resumen_iqr.to_csv(figdir / "resumen_outliers_iqr.csv", sep=args.sep, index=False, encoding="utf-8")
    id_cols = [c for c in ["Municipio", grupo] if c and c in df.columns]
    marcados = df[df["n_metodos_outlier"].fillna(0) > 0]
    (marcados[id_cols + columnas_modelo + ["if_score", "lof_score", "dbscan_cluster", "n_metodos_outlier"]]
        .sort_values(["n_metodos_outlier", "if_score"], ascending=False)
        .to_csv(figdir / "resumen_multivariante.csv", sep=args.sep, index=False, encoding="utf-8"))

    print(f"\nCSV con columnas nuevas: {salida}")
    print(f"Graficos y resumenes:    {figdir}")
    if len(marcados):
        print("\nTop 10 por consenso (n_metodos_outlier, if_score):")
        print(marcados.sort_values(["n_metodos_outlier", "if_score"], ascending=False)
              [id_cols + ["n_metodos_outlier", "if_score", "lof_score"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
