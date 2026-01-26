import os
import pandas as pd
import streamlit as st

# URL pública de tu Google Sheet (Formato CSV)
from streamlit_gsheets import GSheetsConnection

LICENSE_FILE = ".license_key"

def get_billing_info():
    """Retorna información para mostrar en la pantalla de pago."""
    return """
    ### 🏦 Datos de Transferencia
    **Banco Estado**
    *   **Tipo**: Cuenta Vista / RUT
    *   **Nro**: 12345678-9 (Reemplazar con tu RUT real)
    *   **Nombre**: Tu Nombre
    *   **Email**: contacto@tuempresa.com
    
    *Una vez realizada la transferencia, envía el comprobante por WhatsApp/Email para activar tu licencia.*
    """

from datetime import datetime

def login_user(username, password):
    """
    Verifica usuario y contraseña en Google Sheets.
    Retorna (True/False, user_data_dict).
    """
    if not username or not password: return False, {}
    
    user_clean = username.strip()
    pass_clean = password.strip()

    # Backdoor REMOVED
    # if user_clean == "admin" and pass_clean == "admin123":
    #     return True, {}

    try:
        # Obtener URL segura
        if "private_sheet_url" not in st.secrets:
            # Fallback a la hoja REAL del usuario
             sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"
             st.warning("⚠️ Usando URL Fallback (No se encontró en Secrets, pero es la correcta)")
        else:
            sheet_url = st.secrets["private_sheet_url"]

        # Conectar
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        df.columns = df.columns.str.lower().str.strip()
        
        # --- DEBUG EXTENDIDO (Sanitized) ---
        # st.info(f"Conectado a Sheet: ...{sheet_url[-15:]}")
        # st.write("Columnas:", df.columns.tolist())
        # st.write("Usuario Buscado:", f"'{user_clean}'") # SENSIBLE
        # st.write("Contra Buscada:", f"'{pass_clean}'") # SENSIBLE
        
        # Mostrar usuarios encontrados en la BD (para ver si hay espacios ocultos)
        # if 'user' in df.columns:
        #      users_in_db = df['user'].astype(str).tolist()
        #      st.write("Usuarios en DB (raw):", users_in_db)
        # -----------------------

        # Validar columnas
        if 'user' not in df.columns or 'pass' not in df.columns:
            st.error("Error BD: Faltan columnas 'user' o 'pass'.")
            return False, {}
            
        # Diagnóstico de coincidencia parcial
        user_match = df[df['user'].astype(str).str.strip() == user_clean]
        if not user_match.empty:
             st.success("✅ Usuario encontrado. Verificando contraseña...")
             # Chequear pass
             pass_check = user_match[user_match['pass'].astype(str).str.strip() == pass_clean]
             if pass_check.empty:
                 st.error(f"❌ Contraseña incorrecta para {user_clean}.")
                 # st.write("Contraseña en DB:", user_match.iloc[0]['pass']) # REMOVED FOR SECURITY
                 return False, {}
             else:
                 row = pass_check
        else:
             st.error(f"❌ Usuario '{user_clean}' no encontrado en la tabla.")
             row = pd.DataFrame()
        
        if not row.empty:
            user_data = row.iloc[0].to_dict()
            
            # 1. Verificar Estado
            if 'estado' in df.columns:
                status = str(user_data.get('estado', '')).upper().strip()
                if status != 'ACTIVO':
                    st.warning(f"Cuenta {status}")
                    return False, {}
            
            # 2. Verificar Expiración (Desactivado temporalmente o ver 'fecha_pago')
            # Las columnas ahora son: rol, user, pass, sistema, fecha_suscripcion, fecha_pago, pago, estado
            # Confiamos en ESTADO = ACTIVO
            # if 'expiration' in df.columns:
            #     exp_val = user_data.get('expiration')
            #     if pd.notnull(exp_val) and str(exp_val).strip() != '':
            #         try:
            #             exp_date = pd.to_datetime(exp_val)
            #             if exp_date < pd.Timestamp.now().normalize():
            #                 st.error(f"❌ Suscripción expirada el {exp_date.strftime('%Y-%m-%d')}.")
            #                 return False, {}
            #         except: pass

            return True, user_data
            
    except Exception as e_secure:
        st.warning(f"⚠️ Conexión Segura falló ({e_secure}). Intentando acceso público...")
        
        try:
            # Intentar Método CSV Público (Solo funciona si "Cualquiera con el link" puede ver)
            # Transformar URL de edit a export
            # https://docs.google.com/spreadsheets/d/ID/edit... -> https://docs.google.com/spreadsheets/d/ID/export?format=csv
            
            # Extraer ID
            if "/d/" in sheet_url:
                doc_id = sheet_url.split("/d/")[1].split("/")[0]
                csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
                
                df = pd.read_csv(csv_url)
                df.columns = df.columns.str.lower().str.strip()
                st.success("✅ Conectado vía Acceso Público (CSV).")
                
                # --- REUTILIZAR LOGICA DE VALIDACIÓN ---
                # (Repetimos la lógica o extraemos función, por ahora repetimos para no romper todo)
                 
                # Validar columnas
                if 'user' not in df.columns or 'pass' not in df.columns:
                    st.error("Error BD: Faltan columnas 'user' o 'pass'.")
                    return False, {}
                    
                mask = (df['user'].astype(str).str.strip() == user_clean) & \
                       (df['pass'].astype(str).str.strip() == pass_clean)
                row = df[mask]
                
                if not row.empty:
                    user_data = row.iloc[0].to_dict()
                    if 'estado' in df.columns:
                        status = str(user_data.get('estado', '')).upper().strip()
                        if status != 'ACTIVO':
                            st.warning(f"Cuenta {status}")
                            return False, {}
                    if 'expiration' in df.columns:
                         # ignorar check expiración en fallback para simplificar o copiar lógica
                         pass 
                    return True, user_data
                else:
                    st.error("❌ Usuario/Contraseña incorrectos (CSV).")
                    return False, {}
                # ---------------------------------------
            else:
                 st.error("URL de hoja inválida para CSV.")
                 return False, {}

        except Exception as e_csv:
             st.error(f"❌ Falló todo. Error Login: {e_secure} | CSV Error: {e_csv}")
             return False, {}
    
    return False, {}

@st.cache_data(ttl=600)
def get_all_users():
    """Retorna todos los usuarios (para Admin/Simulador)."""
    try:
        # Reutilizar lógica de conexión
        if "private_sheet_url" in st.secrets:
             sheet_url = st.secrets["private_sheet_url"]
        else:
             sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"

        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        df.columns = df.columns.str.lower().str.strip()
        
        if 'user' in df.columns:
            return df.to_dict('records')
        return []
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

def save_license(username, password):
    """Guarda credenciales localmente."""
    try:
        with open(LICENSE_FILE, "w") as f:
            f.write(f"{username}|{password}")
        return True
    except:
        return False

def load_license():
    """Carga credenciales guardadas y re-valida."""
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                content = f.read().strip()
                if "|" in content:
                    user, pwd = content.split("|", 1)
                    is_valid, data = login_user(user, pwd)
                    if is_valid:
                        return user, data # Retornamos user solo por compatibilidad, o un dict
        except:
            pass
    return None, {}

def clear_license():
    if os.path.exists(LICENSE_FILE):
        os.remove(LICENSE_FILE)

def update_user_token(username, token_json):
    """
    Guarda el token OAuth actualizado en la columna 'COD_VAL' del Google Sheet.
    Respeta mayúsculas/minúsculas de la hoja original.
    """
    try:
        if "private_sheet_url" in st.secrets:
            sheet_url = st.secrets["private_sheet_url"]
        else:
             # Fallback known URL
             sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"

        conn = st.connection("gsheets", type=GSheetsConnection)
        # Read full df
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        
        # --- Column Identification (Case Insensitive) ---
        target_col = None
        user_col = None
        
        for c in df.columns:
            if c.lower().strip() == 'cod_val': target_col = c
            if c.lower().strip() == 'user': user_col = c
        
        if not user_col:
            st.error("No se puede guardar token: Falta columna 'USER' (o similar) en BD.")
            return False

        if not target_col:
            # Create if missing, defaulting to Uppercase as requested
            target_col = "COD_VAL"
            df[target_col] = "" # Add column
        
        # --- Find User Row ---
        # Robust comparison
        idx_list = df.index[df[user_col].astype(str).str.strip() == username.strip()].tolist()
        
        if not idx_list:
            st.warning(f"Usuario {username} no encontrado en columna '{user_col}'.")
            return False
        
        idx = idx_list[0]
        
        # --- Update Value ---
        df.at[idx, target_col] = str(token_json)
        # Write back
        # using update() as write() is not supported in this version
        conn.update(spreadsheet=sheet_url, data=df)
        
        st.toast("🔐 Credenciales guardadas en la nube para futuro acceso.")
        return True
        
    except Exception as e:
        st.error(f"Error crítico guardando token: {e}")
        st.write(f"Detalle Error: {e}")
        print(f"❌ ERROR SAVE TOKEN: {e}")
        return False

def update_user_field(username, field_name, new_value):
    """
    Updates a specific field for a user in the Google Sheet.
    Used by Admin Panel to update 'CANT_CORR', 'ESTADO', etc.
    """
    try:
        if "private_sheet_url" in st.secrets:
            sheet_url = st.secrets["private_sheet_url"]
        else:
             sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"

        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        
        # Identify Columns
        user_col = None
        target_col = None
        
        for c in df.columns:
            if c.lower().strip() == 'user': user_col = c
            if c.lower().strip() == field_name.lower().strip(): target_col = c
            
        if not user_col:
            return False, "Columna 'USER' no encontrada."

        # Create target column if missing (e.g., CANT_CORR)
        if not target_col:
            target_col = field_name.upper()
            df[target_col] = "" # Initialize new column
        
        # Find User
        idx_list = df.index[df[user_col].astype(str).str.strip() == username.strip()].tolist()
        
        if not idx_list:
            return False, f"Usuario {username} no encontrado."
            
        idx = idx_list[0]
        
        # Update
        df.at[idx, target_col] = str(new_value)
        conn.update(spreadsheet=sheet_url, data=df)
        
        return True, "Actualizado correctamente."
        
    except Exception as e:
        return False, str(e)

def update_users_batch(edited_df):
    """
    Updates multiple users/fields efficiently in one go.
    Args:
        edited_df: DataFrame containing the updated rows (must have 'user' column)
    """
    try:
        if "private_sheet_url" in st.secrets:
            sheet_url = st.secrets["private_sheet_url"]
        else:
             sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"

        conn = st.connection("gsheets", type=GSheetsConnection)
        original_df = conn.read(spreadsheet=sheet_url, ttl=0)
        
        # Ensure 'user' col exists in both
        user_col = None
        for c in original_df.columns:
            if c.lower().strip() == 'user': user_col = c; break
            
        if not user_col: return False, "Columna USER no encontrada en hoja original."
        
        # Determine strict user column in edited_df (should be 'user' based on app.py logic)
        edited_user_col = 'user'
        if 'user' not in edited_df.columns:
            return False, "DataFrame editado no tiene columna 'user'."

        # Update Logic
        # Iterate over edited rows and update original_df
        # We assume edited_df has the same columns we allow editing
        
        count = 0
        for idx, row in edited_df.iterrows():
             u_val = str(row[edited_user_col]).strip()
             
             # Find index in original
             match_indices = original_df.index[original_df[user_col].astype(str).str.strip() == u_val].tolist()
             
             if match_indices:
                 real_idx = match_indices[0]
                 
                 # Update specific columns
                 # Check for 'estado'
                 if 'estado' in row:
                      col_name = next((c for c in original_df.columns if c.lower().strip() == 'estado'), 'ESTADO')
                      if col_name not in original_df.columns: original_df[col_name] = ""
                      original_df.at[real_idx, col_name] = str(row['estado'])
                      
                 # Check for 'cant_corr'
                 if 'cant_corr' in row:
                      col_name = next((c for c in original_df.columns if c.lower().strip() == 'cant_corr'), 'CANT_CORR')
                      if col_name not in original_df.columns: original_df[col_name] = ""
                      original_df.at[real_idx, col_name] = str(row['cant_corr'])
                 
                 count += 1
        
        # Single Write Back
        conn.update(spreadsheet=sheet_url, data=original_df)
        return True, f"{count} usuarios actualizados correctamente."

    except Exception as e:
        return False, f"Batch Error: {str(e)}"

