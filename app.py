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
ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"

# 2. FUNCIONES DE SERVICIO
def conectar_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        private_key = st.secrets["gspread"]["private_key"].replace("\\n", "\n")
        credenciales_dict = {
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
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        gc = gspread.authorize(creds)
        return gc.open(NOMBRE_HOJA_SHEETS).sheet1
    except Exception as e:
        st.session_state["error_gsheets_conexion"] = str(e)
        return None

def registrar_consulta_dual(p, r):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia, r_limpia = str(p).replace("\n", " ").strip(), str(r).replace("\n", " ").strip()
    
    # Registro CSV
    df = pd.DataFrame([{"Cuándo": ahora, "Pregunta": p_limpia, "Respuesta": r_limpia}])
    df.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    
    # Registro Sheets
    hoja = conectar_google_sheets()
    if hoja:
        try:
            hoja.append_row([ahora, p_limpia, r_limpia])
        except Exception as e:
            st.session_state["error_gsheets_escritura"] = str(e)

# 3. INTERFAZ
st.markdown("<h1 style='text-align: center;'>Aura - Tutora Virtual</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hola, soy Aura. ¿En qué puedo ayudarte hoy?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu consulta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        respuesta = ""
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt
            )
            respuesta = response.text
        except Exception as e:
            err = str(e)
            respuesta = "ERROR DE CONEXIÓN: Se ha agotado la cuota de la API." if "429" in err or "RESOURCE" in err else f"ERROR: {err}"
            st.error(respuesta)
        
        st.markdown(respuesta)
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        registrar_consulta_dual(prompt, respuesta)
