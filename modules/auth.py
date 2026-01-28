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
            idx = row.index[0]

            # --- SUBSCRIPTION LOGIC START ---
            try:
                # Get relevant columns (case insensitive handled by lower() earlier, but we need original keys for updates sometimes? 
                # Actually conn.update logic needs careful handling of indices.
                # Let's rely on modifying 'df' then writing back using conn.update(..., data=df)
                
                # Check System Type
                sistema = str(user_data.get('sistema', '')).strip()
                if sistema in ['Suscripción', 'Pago Anual']:
                    
                    # 1. Check Date Columns
                    # Ensure columns exist in DF
                    cols_needed = ['fecha_suscripcion', 'proxima_renovacion', 'pago', 'estado']
                    for c in cols_needed:
                        if c not in df.columns: df[c] = ""
                    
                    # Get Subscription Date
                    f_susc_raw = str(user_data.get('fecha_suscripcion', '')).strip()
                    f_reno_raw = str(user_data.get('proxima_renovacion', '')).strip()
                    
                    f_susc_dt = None
                    if f_susc_raw:
                        try: f_susc_dt = pd.to_datetime(f_susc_raw, dayfirst=True)
                        except: pass
                    
                    # Calculate Renovation Date if missing
                    # If subscription date exists but renovation is empty, set it to 1 month later or 1 year later
                    if f_susc_dt and (not f_reno_raw or f_reno_raw == 'nan'):
                        if sistema == 'Pago Anual':
                            f_reno_dt = f_susc_dt + pd.DateOffset(years=1)
                        else:
                            f_reno_dt = f_susc_dt + pd.DateOffset(days=30)
                            
                        f_reno_str = f_reno_dt.strftime('%d/%m/%Y') # Save as DD/MM/YYYY to match sheet format
                        df.at[idx, 'proxima_renovacion'] = f_reno_str
                        conn.update(spreadsheet=sheet_url, data=df) # Persist immediately
                        f_reno_raw = f_reno_str # Update local var
                        user_data['proxima_renovacion'] = f_reno_str # CRITICAL: Update returned dict
                        st.toast(f"📅 Renovación ({sistema}) calculada: {f_reno_str}")
                    
                    # Check Expiration
                    if f_reno_raw and f_reno_raw != 'nan':
                         try:
                             f_reno_dt = pd.to_datetime(f_reno_raw, dayfirst=True)
                             today = pd.Timestamp.now().normalize()
                             
                             # DEBUG
                             # st.toast(f"Verificando: Hoy {today.date()} vs Vence {f_reno_dt.date()}")
                             
                             if today > f_reno_dt:
                                 # EXPIRED!
                                 # Update Status
                                 df.at[idx, 'pago'] = 'VENCIDO'
                                 df.at[idx, 'estado'] = 'INACTIVO'
                                 conn.update(spreadsheet=sheet_url, data=df)
                                 
                                 # Notify (Simulated/Console for now to avoid blocking login flow with Email errors)
                                 print(f"SUBSCRIPTION EXPIRED: {user_clean}")
                                 
                                 # Return Failure with Message
                                 # Return Failure with Message
                                 st.error("🚫 **Suscripción Vencida**")
                                 st.markdown(f"""
                                 <div style="background-color: #2b1c1c; padding: 15px; border-radius: 10px; border: 1px solid #ff4b4b;">
                                     <p style="color: #ffcccc;">Tu servicio ha finalizado. No se renueva automáticamente.</p>
                                     <h4 style="color: white; margin-top: 10px;">💳 Datos para Reactivación (Tenpo):</h4> 
                                     <ul style="color: #e0e0e0;">
                                         <li><b>Nombre:</b> ALAIN CESAR ANTINAO SEPULVEDA</li>
                                         <li><b>RUT:</b> 18581575-7</li>
                                         <li><b>Banco:</b> Tenpo (Prepago)</li>
                                         <li><b>Tipo:</b> Cuenta Vista</li>
                                         <li><b>Nro:</b> 111118581575</li>
                                         <li><b>Correo:</b> alain.antinao.s@gmail.com</li>
                                     </ul>
                                     <p style="color: #ffcccc; font-size: 0.9em;">📧 Informa el pago a: <b>alain.antinao.s@gmail.com</b></p>
                                 </div>
                                 """, unsafe_allow_html=True)
                                 
                                 return False, {}
                         except Exception as e:
                             print(f"Date Check Error: {e}")
            except Exception as e_subs:
                print(f"Subscription Logic Error: {e_subs}")
            # --- SUBSCRIPTION LOGIC END ---
            
            # 1. Verificar Estado (Re-read from DF in case we just updated it?)
            # Usage df.at[idx] update in memory dataframe 'df', so it is updated.
            # user_data is a dict copy from before. We should re-fetch status
            current_status = str(df.at[idx, 'estado']).upper().strip()
            
            if current_status != 'ACTIVO':
                st.warning(f"Cuenta {current_status}")
                return False, {}
            
            return True, user_data
            
    except Exception as e_secure:
        st.warning(f"⚠️ Conexión Segura falló ({e_secure}). Intentando acceso público...")
        # ... (Rest of fallback logic remains, potentially without sub logic update capabilities for safety)
        return False, {}
    
    return False, {}

"""
*   **Correo:** alain.antinao.s@gmail.com
"""

# --- NEW HELPERS FOR EMAIL HISTORY (RICH METADATA) ---
import json
import datetime

def get_user_history(user_data):
    """
    Parses history from user_data dict.
    Returns a dict with lists of objects: 
    {'mail': [{'id':..., 's':..., 'd':...}], 'tasks': [...], 'labels': [...]}
    Keys: id=ID, s=Summary, d=Date, t=Type
    """
    result = {'mail': [], 'tasks': [], 'labels': []}
    
    keys_map = {
        'lectura_mail': 'mail',
        'lectura_tareas': 'tasks',
        'lectura_mail': 'mail',
        'lectura_tareas': 'tasks',
        'lectura_etiquetas': 'labels',
        'registro_opti': 'opt_events'
    }
    
    for db_key, internal_key in keys_map.items():
        raw_val = str(user_data.get(db_key, '')).strip()
        if raw_val and raw_val.lower() != 'nan':
            try:
                data = json.loads(raw_val)
                # Handle Migration: If it's a list of strings (old format), convert to objects
                clean_data = []
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            clean_data.append({'id': item, 's': 'Histórico Legacy', 'd': ''})
                        elif isinstance(item, dict):
                            clean_data.append(item)
                result[internal_key] = clean_data
            except:
                # Fallback CSV
                try:
                    ids = [x.strip() for x in raw_val.split(',') if x.strip()]
                    result[internal_key] = [{'id': i, 's': 'Histórico CSV', 'd': ''} for i in ids]
                except: pass
            
    return result

def update_user_history(username, new_items_dict):
    """
    Updates the user's history in Google Sheets with rich objects.
    new_items_dict: {'mail': [{'id':.., 's':..}, ...], ...}
    """
    if not username: return False
    
    try:
        # 1. Fetch current Sheet Data
        if "private_sheet_url" not in st.secrets:
             sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"
        else:
             sheet_url = st.secrets["private_sheet_url"]
             
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        df.columns = df.columns.str.lower().str.strip()
        
        db_map = {
            'mail': 'lectura_mail', 
            'tasks': 'lectura_tareas', 
            'labels': 'lectura_etiquetas',
            'opt_events': 'registro_opti'
        }
        
        # Ensure columns
        for col in db_map.values():
            if col not in df.columns: df[col] = ""
        
        # Find User
        mask = df['user'].astype(str).str.strip() == username.strip()
        if not mask.any(): return False
        idx = df[mask].index[0]
        
        updated = False
        for internal_key, db_col in db_map.items():
            new_items = new_items_dict.get(internal_key, [])
            if not new_items: continue
            
            # Read Existing
            current_raw = str(df.at[idx, db_col])
            current_list = []
            existing_ids = set()
            
            if current_raw and current_raw.lower() != 'nan':
                try:
                    parsed = json.loads(current_raw)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, str): 
                                current_list.append({'id': item, 's': 'Legacy', 'd': ''})
                                existing_ids.add(item)
                            elif isinstance(item, dict):
                                current_list.append(item)
                                existing_ids.add(item.get('id'))
                except:
                    # CSV fallback
                     ids = [x.strip() for x in current_raw.split(',') if x.strip()]
                     for i in ids:
                         current_list.append({'id': i, 's': 'Legacy', 'd': ''})
                         existing_ids.add(i)
            
            # Merge New (Avoid Duplicates by ID)
            added_count = 0
            for item in new_items:
                if item.get('id') not in existing_ids:
                    current_list.append(item)
                    existing_ids.add(item.get('id'))
                    added_count += 1
            
            if added_count > 0:
                df.at[idx, db_col] = json.dumps(current_list)
                updated = True
                
        if updated:
            conn.update(spreadsheet=sheet_url, data=df)
            return True
            
        return True
        
    except Exception as e:
        print(f"Error updating history: {e}")
        return False
        
    except Exception as e:
        print(f"Error updating processed IDs: {e}")
        return False

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

def change_password(username, old_password, new_password):
    """
    Cambia la contraseña del usuario en Google Sheets.
    
    Args:
        username: Usuario actual
        old_password: Contraseña actual (para verificar)
        new_password: Nueva contraseña
        
    Returns:
        (bool, str): (success, message)
    """
    try:
        # 1. Validar nueva contraseña
        if len(new_password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres."
        
        if new_password == old_password:
            return False, "La nueva contraseña debe ser diferente a la actual."
        
        # 2. Verificar contraseña actual
        valid, user_data = login_user(username, old_password)
        if not valid:
            return False, "Contraseña actual incorrecta."
        
        # 3. Actualizar contraseña en Google Sheets
        success, msg = update_user_field(username, 'PASS', new_password)
        
        if success:
            return True, "✅ Contraseña actualizada correctamente."
        else:
            return False, f"Error al actualizar: {msg}"
            
    except Exception as e:
        return False, f"Error: {e}"

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
                 
                 # Check for 'modelo_ia'
                 if 'modelo_ia' in row:
                      col_name = next((c for c in original_df.columns if c.lower().strip() == 'modelo_ia'), 'MODELO_IA')
                      if col_name not in original_df.columns: original_df[col_name] = ""
                      original_df.at[real_idx, col_name] = str(row['modelo_ia'])
                 
                 count += 1
        
        # Single Write Back
        conn.update(spreadsheet=sheet_url, data=original_df)
        return True, f"{count} usuarios actualizados correctamente."

    except Exception as e:
        return False, f"Batch Error: {str(e)}"

        return True, f"{count} usuarios actualizados correctamente."

    except Exception as e:
        return False, f"Batch Error: {str(e)}"

def check_and_update_daily_quota(username, requested_amount=0):
    """
    Gestiona la cuota diaria de correos.
    Retorna: (is_allowed, remaining_quota, usage_today, limit)
    
    Lógica:
    1. Lee LIMIT (CANT_CORR), USAGE (USO_HOY), LAST_DATE (FECHA_USO)
    2. Si FECHA_USO != Hoy, reinicia USAGE = 0.
    3. Si USAGE + requested <= LIMIT, permite y actualiza.
    """
    try:
        import datetime
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        if "private_sheet_url" in st.secrets:
            sheet_url = st.secrets["private_sheet_url"]
        else:
            sheet_url = "https://docs.google.com/spreadsheets/d/1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ/edit?gid=0#gid=0"

        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, ttl=0)
        
        # Identify Case-Insensitive Columns
        col_map = {c.lower().strip(): c for c in df.columns}
        
        c_user = col_map.get('user')
        c_limit = col_map.get('cant_corr', 'CANT_CORR') # Limit
        c_usage = col_map.get('uso_hoy', 'USO_HOY')     # Current Usage
        c_date = col_map.get('fecha_uso', 'FECHA_USO')  # Last Usage Date
        
        if not c_user: return False, 0, 0, 0
        
        # Ensure cols exist in DF
        for c in [c_limit, c_usage, c_date]:
             if c not in df.columns: df[c] = ""
        
        # Find User
        idx_list = df.index[df[c_user].astype(str).str.strip() == username.strip()].tolist()
        if not idx_list: return False, 0, 0, 0
        idx = idx_list[0]
        
        # Get Current Values
        limit_val = pd.to_numeric(df.at[idx, c_limit], errors='coerce')
        limit = int(limit_val) if pd.notnull(limit_val) else 20 # Default Limit
        
        last_date = str(df.at[idx, c_date]).strip()
        usage_val = pd.to_numeric(df.at[idx, c_usage], errors='coerce')
        usage = int(usage_val) if pd.notnull(usage_val) else 0
        
        # RESET Logic
        if last_date != today_str:
            usage = 0
            # Update Date in memory (will write later if allowed or forcing reset)
            df.at[idx, c_date] = today_str
            df.at[idx, c_usage] = 0
            
        remaining = max(0, limit - usage)
        
        if requested_amount == 0:
            # Just checking status
            return True, remaining, usage, limit
            
        if usage + requested_amount <= limit:
            # ALLOWED: Update Usage
            new_usage = usage + requested_amount
            df.at[idx, c_usage] = new_usage
            df.at[idx, c_date] = today_str # Confirm date
            
            conn.update(spreadsheet=sheet_url, data=df)
            return True, limit - new_usage, new_usage, limit
        else:
            # DENIED
            return False, remaining, usage, limit

    except Exception as e:
        print(f"Quota Error: {e}")
        return False, 0, 0, 0
