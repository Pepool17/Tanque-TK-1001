# =============================================================================
# src/clean.py — Limpieza y deduplicación del DataFrame de monitoreo
# =============================================================================

import pandas as pd


COORD_COLS = ["North", "East", "Elevation"]


def _has_coords(row: pd.Series) -> bool:
    return all(pd.notna(row[c]) for c in COORD_COLS)


def _resolve_duplicate_group(group: pd.DataFrame) -> pd.Series:
    """
    Dado un grupo de filas con el mismo (Monitoring, Number):
    - Si alguna tiene coordenadas y otra no → mantiene la que tiene datos.
    - Si todas tienen coordenadas idénticas → mantiene la primera (error de entrada).
    - Si todas tienen coordenadas distintas → lanza un aviso y mantiene la primera
      (caso ambiguo; requiere revisión manual).
    """
    with_coords = group[group.apply(_has_coords, axis=1)]

    if len(with_coords) == 0:
        # Ninguna tiene coordenadas: mantener la primera y avisar
        print(f"  ⚠  Sin coordenadas: {group.iloc[0]['Monitoring']} / {group.iloc[0]['Number']}")
        return group.iloc[0]

    if len(with_coords) == 1:
        return with_coords.iloc[0]

    # Más de una fila con coordenadas: verificar si son idénticas
    coords = with_coords[COORD_COLS].drop_duplicates()
    if len(coords) == 1:
        # Duplicado exacto, mantener primera
        return with_coords.iloc[0]

    # Coordenadas distintas: mantener primera y advertir
    monitoring = group.iloc[0]["Monitoring"]
    number     = group.iloc[0]["Number"]
    print(
        f"  ⚠  Coordenadas distintas en duplicado: {monitoring} / {number}. "
        "Se mantiene la primera ocurrencia. Revisa el Excel."
    )
    return with_coords.iloc[0]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el DataFrame bruto:
      1. Convierte fechas a datetime.
      2. Elimina monitoreos enteros que están duplicados exactamente.
      3. Elimina filas con coordenadas parciales (pero respeta las 100% vacías).
      4. Renombra puntos genéricos (OVER, SAG, LT) basándose en sus vecinos.
      5. Resuelve duplicados conflictivos.
      6. Renumera las campañas sin dejar saltos.
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    
    # Eliminar monitoreos completos duplicados
    n_inicial = len(df)
    df = df.drop_duplicates(
        subset=["Number", "Date", "North", "East", "Elevation"], 
        keep="first"
    )
    n_final = len(df)
    if n_inicial > n_final:
        print(f"  → Limpieza: Se eliminaron {n_inicial - n_final} filas por ser duplicados exactos de datos.")

    # Eliminar filas con coordenadas parciales
    n_original = len(df)
    
    has_north = df["North"].notna()
    has_east = df["East"].notna()
    has_elev = df["Elevation"].notna()
    
    has_any = has_north | has_east | has_elev
    has_all = has_north & has_east & has_elev
    
    partial_coords = has_any & ~has_all
    df = df[~partial_coords].reset_index(drop=True)
    
    n_borradas = n_original - len(df)
    if n_borradas > 0:
        print(f"  → Limpieza: Se eliminaron {n_borradas} filas por tener coordenadas parciales (ej. tiene North pero falta East).")

    # Renombrar puntos genéricos intermedios (OVER, SAG, LT)
    generic_names = ["OVER", "SAG", "LT", "OVER/LT", "SAG/LT"]
    
    def _get_short_name(full_name: str) -> str:
        if not isinstance(full_name, str):
            return str(full_name)
        parts = full_name.split("/")
        return parts[-1] if len(parts) > 1 else full_name
    
    renamed_count = 0
    for monitoring in df["Monitoring"].unique():
        idx = df[df["Monitoring"] == monitoring].index.tolist()
        
        for i, row_idx in enumerate(idx):
            current_name = str(df.loc[row_idx, "Number"]).strip().upper()
            
            if current_name in generic_names:
                prev_short = "N/A"
                for j in range(i - 1, -1, -1):
                    prev_name = str(df.loc[idx[j], "Number"]).strip().upper()
                    if prev_name not in generic_names and not prev_name.startswith("ETB"):
                        prev_short = _get_short_name(prev_name)
                        break
                        
                next_short = "N/A"
                for j in range(i + 1, len(idx)):
                    next_name = str(df.loc[idx[j], "Number"]).strip().upper()
                    if next_name not in generic_names and not next_name.startswith("ETB"):
                        next_short = _get_short_name(next_name)
                        break
                
                new_name = f"{current_name} - {prev_short}/{next_short}"
                df.loc[row_idx, "Number"] = new_name
                renamed_count += 1
                
    if renamed_count > 0:
         print(f"  → Limpieza: Se renombraron {renamed_count} puntos genéricos (OVER/SAG/LT).")

    # Resolver duplicados residuales
    n_before = len(df)
    groups = df.groupby(["Monitoring", "Number"], sort=False)
    needs_dedup = [name for name, g in groups if len(g) > 1]

    if needs_dedup:
        print(f"  Duplicados detectados en {len(needs_dedup)} combinaciones (Monitoring, Punto):")
        for monitoring, number in needs_dedup:
            count = len(groups.get_group((monitoring, number)))
            print(f"    · {monitoring} / {number}  ({count} filas)")

        cleaned_rows = [
            _resolve_duplicate_group(g) for _, g in groups
        ]
        df = pd.DataFrame(cleaned_rows).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    n_after = len(df)
    removed = n_before - n_after
    if removed:
        print(f"  → {removed} fila(s) eliminada(s) por deduplicación residual.")

    # Renumerar monitoreos secuencialmente (Sin saltos)
    unique_campaigns = df["Monitoring"].unique()
    renamed_dict = {old_name: f"MONITOREO {i+1}" for i, old_name in enumerate(unique_campaigns)}
    
    df["Monitoring"] = df["Monitoring"].map(renamed_dict)

    # Ordenar final
    df = df.sort_values(["Number", "Date"]).reset_index(drop=True)

    return df