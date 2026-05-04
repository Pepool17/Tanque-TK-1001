# =============================================================================
# src/plots.py — Gráficas interactivas con Plotly
# =============================================================================

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import (
    ALERT_COLORS, PALETTE, PROJECT_SISTEMA,
    THRESH_H_CRIT_ACCUM, THRESH_H_CRIT_RATE,
    THRESH_H_WARN_ACCUM, THRESH_H_WARN_RATE,
    THRESH_V_CRIT_ACCUM, THRESH_V_CRIT_RATE,
    THRESH_V_WARN_ACCUM, THRESH_V_WARN_RATE,
)


DEFAULT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

def _rgba(hex_color: str, alpha: float) -> str:
    if hex_color.startswith('rgb'):
        if hex_color.startswith('rgba'): return hex_color
        return hex_color.replace('rgb', 'rgba').replace(')', f', {alpha})')
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def _base_layout(title: str, subtitle: str, yaxis_title: str, xaxis_title: str = "Fecha") -> dict:
    return dict(
        title=dict(text=f"<b>{title}</b><br><sup style='color:{PALETTE['muted']};font-size:12px'>{subtitle}</sup>",
                   x=0.01, xanchor="left", font=dict(size=18, color=PALETTE["text"], family="Arial")),
        xaxis=dict(title=dict(text=xaxis_title, font=dict(color=PALETTE["muted"], size=12)),
                   gridcolor=PALETTE["grid"], showline=True, linecolor=PALETTE["grid"], tickfont=dict(color=PALETTE["muted"])),
        yaxis=dict(title=dict(text=yaxis_title, font=dict(color=PALETTE["muted"], size=12)),
                   gridcolor=PALETTE["grid"], showline=True, linecolor=PALETTE["grid"], tickfont=dict(color=PALETTE["muted"]),
                   zeroline=True, zerolinecolor=PALETTE["grid"], zerolinewidth=1.5),
        plot_bgcolor=PALETTE["panel"], paper_bgcolor=PALETTE["bg"],
        legend=dict(
            orientation="v",       
            yanchor="top", 
            y=1.0,                 
            xanchor="left", 
            x=1.02,                
            bgcolor="rgba(255,255,255,0.92)", 
            bordercolor=PALETTE["grid"], 
            borderwidth=1, 
            font=dict(size=11)
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor=PALETTE["grid"], font=dict(size=12, color=PALETTE["text"])),
        margin=dict(t=90, b=60, l=80, r=40), 
        font=dict(family="Arial")
    )

def _hline(fig: go.Figure, y, label: str, color: str) -> None:
    if y is None:
        return
    fig.add_hline(y=y, line=dict(color=color, width=1.8, dash="dash"), opacity=0.9,
                  annotation_text=label, annotation_position="top right",
                  annotation_font=dict(size=11, color=color))

def _zone_band(fig: go.Figure, y0: float, y1: float, color: str, label: str = "") -> None:
    fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.07, layer="below", line_width=0,
                  annotation_text=f"  {label}" if label else "", annotation_position="top left",
                  annotation_font=dict(color=color, size=9, family="Arial"))

def plot_desplazamiento_horizontal(df: pd.DataFrame, points: list[str]) -> go.Figure:
    data = df[df["Monitoring_Number"] > 0]
    fig  = go.Figure()
    for i, point in enumerate(points):
        sub = data[data["Number"] == point].sort_values("Date")
        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        fig.add_trace(go.Scatter(x=sub["Date"], y=sub["Disp_H_mm"], name=point, mode="lines+markers",
            line=dict(color=color, width=2.5), marker=dict(size=7, color=color, line=dict(color="white", width=1)),
            hovertemplate=f"<b>{point}</b><br>Fecha: %{{x|%d/%m/%Y}}<br>Desplazamiento: <b>%{{y:.1f}} mm</b><br><extra></extra>"))    
    _hline(fig, THRESH_H_WARN_ACCUM, f"Umbral atención ({THRESH_H_WARN_ACCUM} mm)", ALERT_COLORS["ATENCIÓN"])
    _hline(fig, THRESH_H_CRIT_ACCUM, f"Umbral crítico ({THRESH_H_CRIT_ACCUM} mm)", ALERT_COLORS["CRÍTICO"])
    fig.update_layout(**_base_layout("Desplazamiento Horizontal Neto Acumulado", f"Movimiento total en planta · {PROJECT_SISTEMA}", "Desplazamiento acumulado (mm)"), yaxis_rangemode="tozero")
    return fig

def plot_tasa_horizontal(df: pd.DataFrame, points: list[str]) -> go.Figure:
    data = df[(df["Monitoring_Number"] > 0) & df["Rate_H_mm_day"].notna()]
    fig  = go.Figure()
    sub_pts = data[data["Number"].isin(points)]
    ymax = max(sub_pts["Rate_H_mm_day"].abs().max() if not sub_pts.empty else 0.5,
           (THRESH_H_CRIT_RATE or 0) * 1.6) or 0.5
    #_zone_band(fig, 0, THRESH_H_WARN_RATE, ALERT_COLORS["NORMAL"], "Normal")
    #_zone_band(fig, THRESH_H_WARN_RATE, THRESH_H_CRIT_RATE, ALERT_COLORS["ATENCIÓN"], "Atención")
    #_zone_band(fig, THRESH_H_CRIT_RATE, ymax * 1.1, ALERT_COLORS["CRÍTICO"], "Crítico")
    for i, point in enumerate(points):
        sub = data[data["Number"] == point].sort_values("Date")
        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        fig.add_trace(go.Scatter(x=sub["Date"], y=sub["Rate_H_mm_day"].abs(), name=point, mode="lines+markers",
            line=dict(color=color, width=2.5), marker=dict(size=7, line=dict(color="white", width=1)),
            hovertemplate=f"<b>{point}</b><br>Fecha: %{{x|%d/%m/%Y}}<br>Tasa: <b>%{{y:.3f}} mm/día</b><br><extra></extra>"))
    _hline(fig, THRESH_H_WARN_RATE, f"Atención  {THRESH_H_WARN_RATE} mm/día", ALERT_COLORS["ATENCIÓN"])
    _hline(fig, THRESH_H_CRIT_RATE, f"Crítico   {THRESH_H_CRIT_RATE} mm/día", ALERT_COLORS["CRÍTICO"])
    fig.update_layout(**_base_layout("Tasa de Desplazamiento Horizontal", "Velocidad de movimiento entre monitoreos", "Tasa (mm/día)"), yaxis_range=[0, ymax])
    return fig

def plot_desplazamiento_vertical(df: pd.DataFrame, points: list[str]) -> go.Figure:
    data = df[df["Monitoring_Number"] > 0]
    fig  = go.Figure()
    for i, point in enumerate(points):
        sub = data[data["Number"] == point].sort_values("Date")
        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        fig.add_trace(go.Scatter(x=sub["Date"], y=sub["Disp_V_mm"], name=point, mode="lines+markers",
            line=dict(color=color, width=2.5), marker=dict(size=7, line=dict(color="white", width=1)),
            hovertemplate=f"<b>{point}</b><br>Fecha: %{{x|%d/%m/%Y}}<br>Desplazamiento: <b>%{{y:.1f}} mm</b><br><extra></extra>"))
    sub_pts = data[data["Number"].isin(points)]
    ymin = sub_pts["Disp_V_mm"].min() if not sub_pts.empty else -400
    for thresh, label, alert_color in [
            (THRESH_V_WARN_ACCUM, f"Atención (−{THRESH_V_WARN_ACCUM} mm)", ALERT_COLORS["ATENCIÓN"]),
            (THRESH_V_CRIT_ACCUM, f"Crítico  (−{THRESH_V_CRIT_ACCUM} mm)", ALERT_COLORS["CRÍTICO"]),
        ]:
            if thresh is not None:
                y = -thresh
                if y > ymin * 1.2: _hline(fig, y, label, alert_color)
    fig.update_layout(**_base_layout("Desplazamiento Vertical Acumulado", "Hundimiento o levantamiento", "Desplazamiento vertical (mm)"))
    return fig

def plot_tasa_vertical(df: pd.DataFrame, points: list[str]) -> go.Figure:
    data = df[(df["Monitoring_Number"] > 0) & df["Rate_V_mm_day"].notna()]
    fig  = go.Figure()
    sub_pts = data[data["Number"].isin(points)]
    ylo = min(sub_pts["Rate_V_mm_day"].min() if not sub_pts.empty else -0.5,
            -(THRESH_V_CRIT_RATE or 0) * 1.6) or -0.5
    yhi = max(sub_pts["Rate_V_mm_day"].max() if not sub_pts.empty else 0.1,
            (THRESH_V_WARN_RATE or 0) * 0.5) or 0.1
    #_zone_band(fig, -THRESH_V_WARN_RATE, yhi * 1.1, ALERT_COLORS["NORMAL"], "Normal")
    #_zone_band(fig, -THRESH_V_CRIT_RATE, -THRESH_V_WARN_RATE, ALERT_COLORS["ATENCIÓN"], "Atención")
    #_zone_band(fig, ylo * 1.1, -THRESH_V_CRIT_RATE, ALERT_COLORS["CRÍTICO"], "Crítico")
    for i, point in enumerate(points):
        sub = data[data["Number"] == point].sort_values("Date")
        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        fig.add_trace(go.Scatter(x=sub["Date"], y=sub["Rate_V_mm_day"], name=point, mode="lines+markers",
            line=dict(color=color, width=2.5), marker=dict(size=7, line=dict(color="white", width=1)),
            hovertemplate=f"<b>{point}</b><br>Fecha: %{{x|%d/%m/%Y}}<br>Tasa: <b>%{{y:.3f}} mm/día</b><br><extra></extra>"))
    for thresh, label, alert_color in [
            (THRESH_V_WARN_RATE, f"Atención −{THRESH_V_WARN_RATE} mm/día", ALERT_COLORS["ATENCIÓN"]),
            (THRESH_V_CRIT_RATE, f"Crítico  −{THRESH_V_CRIT_RATE} mm/día", ALERT_COLORS["CRÍTICO"]),
        ]:
            if thresh is not None:
                y = -thresh
                if y > ylo: _hline(fig, y, label, alert_color)
    fig.update_layout(**_base_layout("Tasa de Desplazamiento Vertical", "Velocidad de hundimiento o levantamiento", "Tasa (mm/día)"), yaxis_range=[ylo, yhi])
    return fig

def _build_vector_traces(fig: go.Figure, df: pd.DataFrame, point: str, color: str, show_legend: bool = True, is_single_plot: bool = False) -> None:
    """
    Añade a fig las trazas de marcadores + flechas de un punto.
    is_single_plot=False APAGA las flechas intermedias para optimizar velocidad.
    """
    data = df[df["Monitoring_Number"] >= 0]
    sub  = data[data["Number"] == point].sort_values("Monitoring_Number")
    
    sub = sub.dropna(subset=["Delta_East_m", "Delta_North_m"])
    n    = len(sub)
    if n < 2: return
    
    x, y = sub["Delta_East_m"].values * 1000, sub["Delta_North_m"].values * 1000
    mon_nums, dates = sub["Monitoring_Number"].values, sub["Date"].values
    
    dx_partial, dy_partial = np.zeros(n), np.zeros(n)
    for i in range(1, n):
        dx_partial[i], dy_partial[i] = x[i] - x[i-1], y[i] - y[i-1]
        
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name=point, showlegend=show_legend,
        marker=dict(color=list(range(n)), colorscale=[[0, _rgba(color, 0.20)], [1, color]],
                    size=[14 if m == 0 else (12 if i == n - 1 else 8) for i, m in enumerate(mon_nums)],
                    symbol=["star" if m == 0 else ("diamond" if i == n - 1 else "circle") for i, m in enumerate(mon_nums)],
                    line=dict(color="white", width=1), showscale=False),
        hovertemplate="<b>%{name}</b><br>Este: %{x:.1f} mm<br>Norte: %{y:.1f} mm<extra></extra>"))

    if n >= 2:
        if is_single_plot:            
            for i in range(1, n - 1):
                if abs(dx_partial[i]) < 0.01 and abs(dy_partial[i]) < 0.01: continue
                alpha = 0.15 + 0.65 * ((i - 1) / max(1, n - 3)) if n > 3 else 0.5
                fig.add_annotation(x=x[i], y=y[i], ax=x[i - 1], ay=y[i - 1], xref="x", yref="y", axref="x", ayref="y",
                                   showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor=color, opacity=alpha, text="")
        else:
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=1.5), opacity=0.3,
                                     showlegend=False, hoverinfo="skip"))
        
        # Última flecha de desplazamiento (Roja)
        if abs(dx_partial[-1]) >= 0.01 or abs(dy_partial[-1]) >= 0.01:
            fig.add_annotation(x=x[-1], y=y[-1], ax=x[-2], ay=y[-2], xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2.5, arrowcolor="red", opacity=1.0, text="")

def _add_cardinal_axes(fig: go.Figure) -> None:
    fig.add_hline(y=0, line=dict(color=PALETTE["muted"], width=1, dash="dash"), opacity=0.45)
    fig.add_vline(x=0, line=dict(color=PALETTE["muted"], width=1, dash="dash"), opacity=0.45)
    for text, x_p, y_p, xanchor, yanchor in [("→ Este", 1.0, 0.5, "right", "middle"), ("← Oeste", 0.0, 0.5, "left", "middle"),
                                             ("↑ Norte", 0.5, 1.0, "center", "top"), ("↓ Sur", 0.5, 0.0, "center", "bottom")]:
        fig.add_annotation(x=x_p, y=y_p, xref="paper", yref="paper", text=f"<i>{text}</i>", showarrow=False,
                           font=dict(size=11, color=PALETTE["muted"]), xanchor=xanchor, yanchor=yanchor, opacity=0.7)

def _vector_axis_ranges(x_all: np.ndarray, y_all: np.ndarray, pad: float = 0.15) -> tuple[list, list]:
    def _range(arr):
        valid_arr = arr[~np.isnan(arr)]
        if len(valid_arr) == 0: return [-10, 10]
        lo, hi = valid_arr.min(), valid_arr.max()
        span = max(hi - lo, 20.0)
        margin = span * pad
        return [lo - margin, hi + margin]
    return _range(x_all), _range(y_all)

def plot_vectores(df: pd.DataFrame, points: list[str]) -> go.Figure:
    fig = go.Figure()
    all_x, all_y = [np.array([0])], [np.array([0])]
    for i, point in enumerate(points):
        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        # is_single_plot=False evita dibujar mil flechas
        _build_vector_traces(fig, df, point, color, show_legend=True, is_single_plot=False)
        sub = df[(df["Number"] == point) & (df["Monitoring_Number"] >= 0)]
        sub = sub.dropna(subset=["Delta_East_m", "Delta_North_m"])
        if not sub.empty:
            all_x.append(sub["Delta_East_m"].values * 1000)
            all_y.append(sub["Delta_North_m"].values * 1000)
    _add_cardinal_axes(fig)
    xr, yr = _vector_axis_ranges(np.concatenate(all_x), np.concatenate(all_y))
    fig.update_layout(**_base_layout("Vectores de Desplazamiento", f"Trayectoria acumulada · {PROJECT_SISTEMA}", "Norte (mm)", "Este (mm)"), xaxis_range=xr, yaxis_range=yr)
    return fig

def plot_vector_single(df: pd.DataFrame, point: str) -> tuple[go.Figure, dict]:
    fig = go.Figure()
    # is_single_plot=True habilita el degradado de todas las flechas
    _build_vector_traces(fig, df, point, DEFAULT_COLORS[0], show_legend=False, is_single_plot=True)
    _add_cardinal_axes(fig)

    sub = df[(df["Number"] == point) & (df["Monitoring_Number"] >= 0)].sort_values("Monitoring_Number")
    sub = sub.dropna(subset=["Delta_East_m", "Delta_North_m"]) 
    
    info = {}
    if sub.empty:
        x, y = np.array([0]), np.array([0])
    else:
        x, y = sub["Delta_East_m"].values * 1000, sub["Delta_North_m"].values * 1000
        z = sub["Disp_V_mm"].values 
        
        # Datos absolutos del último monitoreo
        info["date"] = pd.Timestamp(sub["Date"].iloc[-1]).strftime('%d/%m/%Y') if pd.notna(sub["Date"].iloc[-1]) else "N/A"
        info["n_abs"] = sub["North"].iloc[-1]
        info["e_abs"] = sub["East"].iloc[-1]
        info["z_abs"] = sub["Elevation"].iloc[-1]
        
        # Diferencias del último movimiento (paso actual - paso anterior)
        info["step_dx"] = x[-1] - x[-2] if len(x) >= 2 else 0.0
        info["step_dy"] = y[-1] - y[-2] if len(y) >= 2 else 0.0
        info["step_dz"] = z[-1] - z[-2] if len(z) >= 2 else 0.0
        
        # Magnitudes
        info["step_disp"] = np.sqrt(info["step_dx"]**2 + info["step_dy"]**2) # Magnitud del vector rojo en planta
        info["step_hundimiento"] = abs(info["step_dz"]) # Magnitud (absoluto) de la diferencia de elevación
        
        # Acumulado neto
        info["net_dx"] = x[-1]
        info["net_dy"] = y[-1]
        info["net_disp"] = np.sqrt(x[-1]**2 + y[-1]**2)

    xr, yr = _vector_axis_ranges(np.concatenate([np.array([0]), x]), np.concatenate([np.array([0]), y]))
    fig.update_layout(**_base_layout(f"Vector de Desplazamiento — {point}", f"Trayectoria acumulada · {PROJECT_SISTEMA}", "Norte (mm)", "Este (mm)"), xaxis_range=xr, yaxis_range=yr)
    return fig, info