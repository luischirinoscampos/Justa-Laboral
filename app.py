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

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# --- MÓDULO DE CONOCIMIENTO EMBEBIDO (Producción Segura) ---
MODULOS_AURA = {
    "PROGRAMA": "Derecho del Trabajo: Sujetos, contrato, jornada, extinción, derechos colectivos.",
    "LEGAL": "LOTTT (Ley Orgánica del Trabajo): Principios de justicia social, estabilidad, carácter remunerativo del salario, progresividad.",
    "U1": "Principios: Trabajo como hecho social, irrenunciabilidad, primacía de la realidad, in dubio pro operario, estabilidad laboral.",
    "U2": "Sujetos: Trabajador, Patrono. Contrato: Consensual, oneroso, subordinado. Extinción: Despido y retiro.",
    "U3": "Salario: Normal e Integral. Jornada: Diurna (8h), Nocturna (7h), Mixta (7.5h). Prestaciones: Garantía trimestral, cálculo de vacaciones.",
    "U4": "Derecho Colectivo: Libertad sindical, fuero, negociación colectiva, conflictos colectivos, huelga.",
    "EJERCICIOS": "Liquidación: Definir salario base, días de vacaciones, recargos de horas extra (50% diurnas, 80% nocturnas)."
}

def enrutador_y_contexto(consulta):
    """Clasifica la consulta para extraer el contexto necesario."""
    api_key = st.secrets.get("gemini_api_key")
    client = genai.Client(api_key=api_key)
    prompt = f"Clasifica: '{consulta}' en una de estas categorías: {list(MODULOS_AURA.keys())}. Devuelve SOLO la clave."
    try:
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        cat = resp.text.strip()
        return MODULOS_AURA.get(cat, MODULOS_AURA["LEGAL"])
    except:
        return MODULOS_AURA["LEGAL"]

# Configuración de variables
api_key = st.secrets.get("gemini_api_key", None)
ARCHIVO_BITACORA = "consultas_local.csv"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"

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
        sh = gc.open(NOMBRE_HOJA_SHEETS)
        return sh.sheet1
    except Exception as e:
        st.session_state["error_gsheets_conexion"] = str(e)
        return None

def registrar_consulta_dual(texto_pregunta, respuesta_o_error):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia, r_limpia = str(texto_pregunta).replace("\n", " ").strip(), str(respuesta_o_error).replace("\n", " ").strip()
    # CSV
    df = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": p_limpia, "Respuesta de Aura": r_limpia}])
    if os.path.exists(ARCHIVO_BITACORA): df.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False, encoding='utf-8')
    else: df.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False, encoding='utf-8')
    # Sheets
    hoja = conectar_google_sheets()
    if hoja: hoja.append_row([ahora, p_limpia, r_limpia])

# CSS E INTERFAZ
st.markdown("""<style>
    .custom-header { text-align: center; margin-bottom: 15px; }
    .line-1 { color: #0A2540; font-size: 2.4rem; font-weight: 700; }
    .line-2 { color: #1A202C; font-size: 1.4rem; font-weight: 600; }
    .line-3 { color: #4A5568; font-size: 1.05rem; }
</style>""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "avatar": "✨", "content": "¡Bienvenido! ¿En qué puedo apoyarte hoy?"}]

st.markdown('<div class="custom-header"><div class="line-1">Aura</div><div class="line-2">Tutora Académica en Línea</div></div>', unsafe_allow_html=True)

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=msg.get("avatar")): st.markdown(msg["content"])
    
    if prompt := st.chat_input("Escribe tu consulta jurídica..."):
        # Integración optimizada
        contexto_aura = enrutador_y_contexto(prompt)
        system_instruction = f"Eres Aura, experta en Derecho. Contexto: {contexto_aura}. Responde pedagógicamente."
        
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt, config=types.GenerateContentConfig(system_instruction=system_instruction))
        
        st.markdown(response.text)
        registrar_consulta_dual(prompt, response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA): st.dataframe(pd.read_csv(ARCHIVO_BITACORA))
        if st.button("Probar GSheets"): st.write("Conexión activa" if conectar_google_sheets() else "Error")
