import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. CONFIGURACIÓN DE PÁGINA Y SECRETOS
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")
api_key = st.secrets.get("gemini_api_key", None)

# Función para conectar con Google Sheets
def conectar_sheets():
    try:
        # Se asume que el JSON de credenciales está en los secretos de Streamlit
        creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Bitacora_Aura").sheet1
    except Exception:
        return None

# Función de registro dual (Local + Sheets)
def registrar_interaccion(pregunta, respuesta):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    # Registro Local (CSV)
    try:
        nuevo_registro = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": pregunta, "Respuesta": respuesta}])
        nuevo_registro.to_csv("consultas_local.csv", mode='a', header=not os.path.exists("consultas_local.csv"), index=False, encoding='utf-8')
    except: pass
    
    # Registro en Google Sheets
    sheet = conectar_sheets()
    if sheet:
        try:
            sheet.append_row([ahora, pregunta, respuesta])
        except: pass

@st.cache_data
def cargar_contexto_catedra():
    if os.path.exists("vector_store.json"):
        with open("vector_store.json", "r", encoding="utf-8") as f:
            datos = json.load(f)
            return "".join([f"\nDocumento: {item['nombre_archivo']}\nContenido: {item['texto_contenido']}\n---" for item in datos])
    return ""

CONTEXTO_LEGAL_CATEDRA = cargar_contexto_catedra()

# 2. INYECCIÓN DE ESTILOS CSS
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
    .custom-header { text-align: center; width: 100%; margin-top: 5px; margin-bottom: 15px; font-family: 'Inter', sans-serif; }
    .line-1 { color: #0A2540 !important; font-size: 2.4rem; font-weight: 700; }
    .line-2 { color: #1A202C !important; font-size: 1.4rem; font-weight: 600; }
    .line-3, .line-4 { color: #4A5568 !important; font-size: 1.05rem; }
    .line-divider { border-bottom: 1px solid #E2E8F0; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# Inicialización de estado
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "avatar": "✨", "content": "Bienvenido(a). Soy Aura, tu tutora en Derecho del Trabajo."}]
if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

# Encabezado
st.markdown("""
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
        <div class="line-4">Desarrollador: Luis Ignacio Chirinos Campos</div>
        <div class="line-divider"></div>
    </div>
""", unsafe_allow_html=True)

# Tabs
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    system_instruction = f"""Eres Aura, tutora experta en Derecho del Trabajo. 
    Tu creador es el profesor Luis Ignacio Chirinos Campos. 
    Responde estrictamente basándote en: {CONTEXTO_LEGAL_CATEDRA}"""

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    prompt = st.chat_input("Escribe tu consulta aquí...")

    if prompt:
        if time.time() - st.session_state.ultimo_envio < 15.0:
            st.warning("⏳ Por favor espera un momento.")
        else:
            st.session_state.ultimo_envio = time.time()
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})

            with st.chat_message("assistant", avatar="✨"):
                try:
                    client = genai.Client(api_key=api_key)
                    history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                               parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
                    
                    response = client.models.generate_content(model='gemini-2.5-flash', 
                               contents=history, 
                               config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3))
                    
                    registrar_interaccion(prompt, response.text)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": response.text})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    clave = st.text_input("Credencial:", type="password")
    if clave == "UCLA2026":
        if os.path.exists("consultas_local.csv"):
            df = pd.read_csv("consultas_local.csv")
            st.dataframe(df.iloc[::-1])
            st.download_button("📥 Descargar CSV", data=df.to_csv(index=False), file_name="bitacora.csv")
