# =============================================================================
# src/extract.py — Extracción adaptada para Monitoreo de Tanques (Corrección)
# =============================================================================

import re
import unicodedata
import pandas as pd
from datetime import datetime

def clean_text(text) -> str:
    if text is None or pd.isna(text): return ""
    text_str = str(text).strip()
    text_sin_tildes = ''.join(
        c for c in unicodedata.normalize('NFD', text_str)
        if unicodedata.category(c) != 'Mn'
    )
    return text_sin_tildes.upper()

def parse_date_simple(date_text):
    if pd.isna(date_text) or not date_text: return None
    if isinstance(date_text, datetime): 
        return date_text.strftime("%d/%m/%Y")
    
    # Limpia prefijos comunes para dejar solo el texto de la fecha
    text = str(date_text).strip()
    text = re.sub(r"^(?:FECHA|DATOS TOMADOS EL)\s*[:.]?\s*", "", text, flags=re.IGNORECASE).strip()
    return text

def extract_data(filepath: str) -> pd.DataFrame:
    dict_sheets = pd.read_excel(filepath, header=None, sheet_name=None)
    records = []
    
    for sheet_name, df_sheet in dict_sheets.items():
        sheet_data = [[None if pd.isna(val) else val for val in row] for row in df_sheet.values.tolist()]
        
        header_row_idx = -1
        # 1. Buscar la fila principal que contiene los encabezados (Fila 14 aprox)
        for i, row in enumerate(sheet_data):
            row_text = " ".join([str(x).upper() for x in row if x])
            if "LINEA BASE" in row_text or "CONTROL #" in row_text or "CONTROL 1" in row_text:
                header_row_idx = i
                break
                
        if header_row_idx == -1:
            continue
            
        # 2. Identificar y procesar cada campaña en esa fila
        for c, cell_val in enumerate(sheet_data[header_row_idx]):
            val_clean = clean_text(cell_val)
            if "LINEA BASE" in val_clean or "CONTROL" in val_clean:
                monitoreo_name = str(cell_val).strip()
                
                # 3. Buscar "Altura de llenado" a la derecha (y hasta 2 filas abajo)
                altura = None
                for r_offset in range(3):
                    if header_row_idx + r_offset >= len(sheet_data): break
                    for c_offset in range(6):  
                        if c + c_offset >= len(sheet_data[0]): break
                        cell_text = str(sheet_data[header_row_idx + r_offset][c + c_offset])
                        if "ALTURA" in cell_text.upper():
                            m_alt = re.search(r"(\d+(?:\.\d+)?)", cell_text)
                            if m_alt:
                                altura = float(m_alt.group(1))
                                break
                    if altura is not None: break
                    
                # 4. Buscar fecha (exactamente 3 filas abajo en la sección del control actual)
                fecha = None
                date_row = header_row_idx + 3
                if date_row < len(sheet_data):
                    for c_offset in range(3): # Buscamos en las 3 celdas debajo del encabezado
                        if c + c_offset >= len(sheet_data[0]): break
                        cell_text = str(sheet_data[date_row][c + c_offset])
                        if "FECHA" in cell_text.upper() or "DATOS TOMADOS" in cell_text.upper():
                            fecha = parse_date_simple(sheet_data[date_row][c + c_offset])
                            break
                            
                # 5. Mapear columnas NORTE, ESTE, COTA de forma posicional estricta.
                # Como observamos, las coordenadas base siempre ocupan las 3 primeras 
                # columnas empezando desde donde está el título del Control.
                idx_norte = c
                idx_este = c + 1
                idx_cota = c + 2
                    
                # 6. Extraer los datos a partir de la 6ta fila hacia abajo (Fila 20 aprox)
                data_start_row = header_row_idx + 6
                for r in range(data_start_row, len(sheet_data)):
                    punto_nombre = sheet_data[r][0]  # El número del punto siempre está en la columna A
                    
                    if pd.isna(punto_nombre) or str(punto_nombre).strip() == "":
                        continue
                        
                    punto_clean = str(punto_nombre).strip()
                    if "PROMEDIO" in punto_clean.upper() or "TOTAL" in punto_clean.upper():
                        continue
                        
                    # Extracción usando los índices estáticos calculados arriba
                    norte_val = sheet_data[r][idx_norte]
                    este_val = sheet_data[r][idx_este]
                    cota_val = sheet_data[r][idx_cota]
                    
                    if pd.isna(norte_val) and pd.isna(este_val) and pd.isna(cota_val):
                        continue
                        
                    records.append({
                        "Monitoreo": monitoreo_name,
                        "Nombre_punto": punto_clean,
                        "Norte": norte_val,
                        "Este": este_val,
                        "Elevacion": cota_val,
                        "Fecha": fecha,
                        "Altura_tanque": altura
                    })
                    
    df = pd.DataFrame(records)
    # Convertir forzosamente las coordenadas a números decimales
    for col in ['Norte', 'Este', 'Elevacion']: 
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df