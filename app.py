import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# --- SECRETOS ---
api_key = st.secrets.get("gemini_api_key", None)
ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"

# --- FUNCIONES DE SERVICIO ---
def conectar_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        private_key = st.secrets["gspread"]["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict({
            "type": st.secrets["gspread"]["type"],
            "project_id": st.secrets["gspread"]["project_id"],
            "private_key_id": st.secrets["gspread"]["private_key_id"],
            "private_key": private_key,
            "client_email": st.secrets["gspread"]["client_email"],
            "client_id": st.secrets["gspread"]["client_id"],
            "auth_uri": st.secrets["gspread"]["auth_uri"],
            "token_uri": st.secrets["gspread"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gspread"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gspread"]["client_x509_cert_url"]
        }, scope)
        gc = gspread.authorize(creds)
        return gc.open(NOMBRE_HOJA_SHEETS).sheet1
    except:
        return None

def registrar_consulta_dual(p, r):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia, r_limpia = str(p).replace("\n", " ").strip(), str(r).replace("\n", " ").strip()
    
    # CSV
    df = pd.DataFrame([{"Cuándo": ahora, "Pregunta": p_limpia, "Respuesta": r_limpia}])
    df.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    
    # Sheets
    hoja = conectar_google_sheets()
    if hoja:
        try: hoja.append_row([ahora, p_limpia, r_limpia])
        except: pass

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .custom-header { text-align: center; margin-bottom: 20px; font-family: 'Inter', sans-serif; }
    .line-1 { color: #0A2540; font-size: 2.4rem; font-weight: 700; margin-bottom: 2px; }
    .line-2 { color: #1A202C; font-size: 1.4rem; font-weight: 600; margin-bottom: 6px; }
    .line-3 { color: #4A5568; font-size: 1.05rem; }
    </style>
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
    </div>
""", unsafe_allow_html=True)

# --- APP ---
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Bienvenido, ¿qué consulta tienes hoy?"}]
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
    if prompt := st.chat_input("Escribe tu consulta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
            
        with st.chat_message("assistant"):
            respuesta = ""
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
                respuesta = response.text
            except Exception as e:
                err = str(e)
                respuesta = "ERROR: Cuota de API agotada." if any(x in err for x in ["429", "RESOURCE_EXHAUSTED"]) else f"ERROR: {err}"
                st.error(respuesta)
            
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
            # El registro ocurre SIEMPRE aquí abajo, independientemente del éxito de la API
            registrar_consulta_dual(prompt, respuesta)

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    if st.text_input("Credencial Docente", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA): st.dataframe(pd.read_csv(ARCHIVO_BITACORA))
        else: st.info("Sin registros.")
