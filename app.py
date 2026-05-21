import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

api_key = st.secrets.get("gemini_api_key", None)
ARCHIVO_BITACORA = "consultas_local_v2.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"

def registrar_consulta_local(texto_pregunta, texto_respuesta):
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nuevo_registro = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": texto_pregunta, "Respuesta": texto_respuesta}])
        nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    except Exception:
        pass

@st.cache_data
def cargar_contexto_catedra():
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return "".join([f"\nDocumento: {item['nombre_archivo']}\nContenido: {item['texto_contenido']}\n---" for item in datos])
    return ""

CONTEXTO_LEGAL_CATEDRA = cargar_contexto_catedra()

# 2. INYECCIÓN DE ESTILOS CSS (RESTAURADO)
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

# 3. ESTADO DE SESIÓN E IDENTIDAD (RESTAURADO)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "avatar": "✨", "content": "### ¡Bienvenido(a)!\n\nHola. Soy **Aura**, tutora académica en línea del EDA de **Derecho del Trabajo**, gestionado por el Prof: Luis Ignacio Chirinos Campos."}]

st.markdown("""
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
        <div class="line-4">Desarrollador: Luis Ignacio Chirinos Campos</div>
        <div class="line-divider"></div>
    </div>
""", unsafe_allow_html=True)

# 4. PESTAÑAS Y LÓGICA (RESTAURADA)
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    system_instruction = f"Eres Aura, tutora experta en Derecho del Trabajo. Creada por Luis Ignacio Chirinos Campos. Usa este contexto: {CONTEXTO_LEGAL_CATEDRA}"
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    prompt = st.chat_input("Escribe tu consulta aquí...")
    if prompt:
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        with st.chat_message("assistant", avatar="✨"):
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=types.GenerateContentConfig(system_instruction=system_instruction))
                registrar_consulta_local(prompt, response.text)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip')
            st.dataframe(df.iloc[::-1])
