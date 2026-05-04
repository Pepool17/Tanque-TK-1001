# =============================================================================
# src/enrich.py — Enriquecimiento del DataFrame
# =============================================================================

import re
import numpy as np
import pandas as pd
from datetime import datetime
from config import THRESH_H_CRIT_RATE, THRESH_H_WARN_RATE, MESES

# ── Parseo y corrección cronológica de fechas ─────────────────────────────────

def _parse_date_parts(text) -> tuple:
    """Extrae (día, mes_idx, año_o_None) de un string de fecha."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return None, None, None

    text = re.sub(r"^(?:DATOS TOMADOS EL|FECHA)\s*[:.]?\s*", "", str(text).strip(), flags=re.IGNORECASE)
    # Abreviatura de mes (SEPT. → SEPTIEMBRE)
    text = re.sub(r"\bSEPT?\.\s*", "SEPTIEMBRE ", text, flags=re.IGNORECASE)

    # Con año: "5 DE ABRIL 2013" / "5 DE ABRIL DEL 2013"
    m = re.search(r"(\d{1,2})\s+(?:DE\s+)?([A-Za-z]+)\s+(?:DEL?\s+)?(\d{4})", text, re.IGNORECASE)
    if m:
        d, mon, y = m.groups()
        return int(d), MESES.get(mon.lower()), int(y)

    # Sin año: "5 de Septiembre"
    m = re.search(r"(\d{1,2})\s+(?:DE\s+)?([A-Za-z]+)", text, re.IGNORECASE)
    if m:
        d, mon = m.groups()
        return int(d), MESES.get(mon.lower()), None

    return None, None, None


def _fix_chronological_years(date_parts_list: list) -> list:
    """Infiere años faltantes usando continuidad cronológica (igual que extract.py)."""
    n = len(date_parts_list)
    years = [p[2] for p in date_parts_list]

    first_idx = next((i for i, y in enumerate(years) if y is not None), None)
    if first_idx is None:
        this_year = datetime.now().year
        return [
            f"{p[0]:02d}/{p[1]:02d}/{this_year}" if p[0] and p[1] else None
            for p in date_parts_list
        ]

    # Propagar hacia atrás
    for i in range(first_idx - 1, -1, -1):
        m_curr = date_parts_list[i][1]
        m_next = date_parts_list[i + 1][1]
        if m_curr and m_next:
            years[i] = years[i + 1] - 1 if m_curr > m_next else years[i + 1]

    # Propagar hacia adelante
    for i in range(first_idx + 1, n):
        if years[i] is not None:
            continue
        m_curr = date_parts_list[i][1]
        m_prev = date_parts_list[i - 1][1]
        if m_curr and m_prev:
            years[i] = years[i - 1] + 1 if m_curr < m_prev else years[i - 1]

    return [
        f"{p[0]:02d}/{p[1]:02d}/{years[i]}" if p[0] and p[1] and years[i] else None
        for i, p in enumerate(date_parts_list)
    ]


def _fix_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte la columna Fecha (strings libres) a datetime,
    infiriendo años faltantes cronológicamente por monitoreo.
    """
    # Obtener una fecha representativa por número de monitoreo (orden ya conocido)
    monitoreos_ordenados = sorted(df["Monitoreo"].unique())
    fecha_por_monitoreo = (
        df.drop_duplicates("Monitoreo")
        .set_index("Monitoreo")["Fecha"]
        .to_dict()
    )

    date_parts_list = [_parse_date_parts(fecha_por_monitoreo[m]) for m in monitoreos_ordenados]
    fixed = _fix_chronological_years(date_parts_list)
    year_map = {m: fixed[i] for i, m in enumerate(monitoreos_ordenados)}

    # Aplicar: si la fecha original tiene año, parsear normalmente;
    # si no, usar el año inferido del mapa
    def _resolve(row):
        parts = _parse_date_parts(row["Fecha"])
        if parts[0] is None:
            return pd.NaT
        if parts[2] is not None:
            # Tiene año propio → formatear directamente
            return pd.to_datetime(f"{parts[0]:02d}/{parts[1]:02d}/{parts[2]}", dayfirst=True, errors="coerce")
        # Sin año → tomar el año inferido del monitoreo
        fixed_str = year_map.get(row["Monitoreo"])
        if fixed_str is None:
            return pd.NaT
        return pd.to_datetime(fixed_str, dayfirst=True, errors="coerce")

    df["Fecha"] = df.apply(_resolve, axis=1)
    return df


# ── Pipeline principal ────────────────────────────────────────────────────────

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Corregir fechas ANTES de renombrar columnas
    df = _fix_dates(df)

    # Renombrar columnas del CSV al esquema interno
    df = df.rename(columns={
        "Monitoreo":    "Monitoring_Number",
        "Nombre_punto": "Number",
        "Norte":        "North",
        "Este":         "East",
        "Elevacion":    "Elevation",
        "Fecha":        "Date",
    })

    # Reconstruir columna "Monitoring" textual
    df["Monitoring"] = df["Monitoring_Number"].apply(
        lambda n: "BASELINE" if n == 0 else f"MONITOREO {n}"
    )

    df = df.sort_values(by=["Number", "Date"]).reset_index(drop=True)

    # Baseline por punto (Monitoreo == 0)
    baseline = (
        df[df["Monitoring_Number"] == 0]
        .dropna(subset=["North", "East", "Elevation"])
        .groupby("Number")[["North", "East", "Elevation", "Date"]]
        .first()
    )

    # Deltas acumulados
    df["Delta_North_m"] = df["North"] - df["Number"].map(baseline["North"])
    df["Delta_East_m"]  = df["East"]  - df["Number"].map(baseline["East"])
    df["Delta_Elev_m"]  = df["Elevation"] - df["Number"].map(baseline["Elevation"])

    # Desplazamientos acumulados (mm)
    df["Disp_H_mm"]  = np.sqrt(df["Delta_North_m"]**2 + df["Delta_East_m"]**2) * 1000
    df["Disp_V_mm"]  = df["Delta_Elev_m"] * 1000
    df["Disp_3D_mm"] = np.sqrt(
        df["Delta_North_m"]**2 + df["Delta_East_m"]**2 + df["Delta_Elev_m"]**2
    ) * 1000

    # Dirección del desplazamiento
    df["Bearing_deg"] = np.degrees(
        np.arctan2(df["Delta_East_m"], df["Delta_North_m"])
    ) % 360

    # Días desde baseline
    baseline_dates = df["Number"].map(baseline["Date"])
    df["Days_Since_Baseline"] = (df["Date"] - baseline_dates).dt.days

    # Diferencias parciales y tasas
    for col in ("Delta_Partial_H_mm", "Delta_Partial_V_mm",
                "Days_Since_Prev", "Rate_H_mm_day", "Rate_V_mm_day", "Rate_3D_mm_day"):
        df[col] = np.nan

    df = df.sort_values(["Number", "Monitoring_Number"]).reset_index(drop=True)

    for point in df["Number"].unique():
        idx = df[df["Number"] == point].index.tolist()
        valid_indices = [i for i in idx if pd.notna(df.loc[i, "Disp_H_mm"])]
        if not valid_indices:
            continue
        last_valid_idx = valid_indices[0]

        for k in range(1, len(idx)):
            cur = idx[k]
            if pd.isna(df.loc[cur, "Disp_H_mm"]):
                continue
            dh = df.loc[cur, "Disp_H_mm"]  - df.loc[last_valid_idx, "Disp_H_mm"]
            dv = df.loc[cur, "Disp_V_mm"]  - df.loc[last_valid_idx, "Disp_V_mm"]
            d3 = df.loc[cur, "Disp_3D_mm"] - df.loc[last_valid_idx, "Disp_3D_mm"]
            dd = (df.loc[cur, "Date"] - df.loc[last_valid_idx, "Date"]).days

            df.loc[cur, "Delta_Partial_H_mm"] = dh
            df.loc[cur, "Delta_Partial_V_mm"] = dv
            df.loc[cur, "Days_Since_Prev"]    = dd

            if dd and dd > 0:
                df.loc[cur, "Rate_H_mm_day"]  = dh / dd
                df.loc[cur, "Rate_V_mm_day"]  = dv / dd
                df.loc[cur, "Rate_3D_mm_day"] = d3 / dd
            last_valid_idx = cur

    # Nivel de alerta
    def _alert(row) -> str:
        rate = abs(row["Rate_H_mm_day"]) if pd.notna(row["Rate_H_mm_day"]) else 0.0
        if THRESH_H_CRIT_RATE is not None and rate >= THRESH_H_CRIT_RATE: return "CRÍTICO"
        if THRESH_H_WARN_RATE is not None and rate >= THRESH_H_WARN_RATE: return "ATENCIÓN"
        return "NORMAL"

    df["Alert_Level"] = df.apply(_alert, axis=1)
    return df