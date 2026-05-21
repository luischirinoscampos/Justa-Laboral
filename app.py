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

ARCHIVO_BITACORA = "consultas_local_v2.csv"

# --- FUNCIONES DE REGISTRO Y CONEXIÓN ---
def registrar_en_bitacora(pregunta, respuesta):
    """Registra la interacción de forma segura."""
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        df = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": pregunta, "Respuesta": respuesta}])
        df.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    except Exception as e:
        st.error(f"Error al registrar: {e}")

# --- CSS E IDENTIDAD VISUAL ---
st.markdown("""
    <style>
    .custom-header { text-align: center; margin-bottom: 20px; font-family: sans-serif; }
    .line-1 { font-size: 2.5rem; font-weight: 800; color: #0A2540; }
    .line-2 { font-size: 1.5rem; font-weight: 600; color: #1A202C; }
    .line-3 { font-size: 1.1rem; color: #4A5568; }
    </style>
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo | Prof: Luis Ignacio Chirinos Campos</div>
    </div>
""", unsafe_allow_html=True)

# --- MENSAJE PRELIMINAR DE PRESENTACIÓN Y UTILIDAD ---
st.info("""
### Bienvenido(a) a Aura
Esta plataforma está diseñada para brindar orientación pedagógica y acompañamiento en el estudio del Derecho del Trabajo. 
* **Orientación 24/7:** Respuestas basadas estrictamente en la doctrina y normativa laboral vigente.
* **Finalidad:** Solventar dudas, repasar conceptos esenciales y guiar tu proceso de aprendizaje.
* **Nota:** Aura no sustituye al profesor-curador. Úsala con integridad académica.
""")

# --- LÓGICA DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- PESTAÑAS ---
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    prompt = st.chat_input("Consulta jurídica...")
    if prompt:
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        
        with st.chat_message("assistant", avatar="✨"):
            try:
                client = genai.Client(api_key=st.secrets["gemini_api_key"])
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                
                registrar_en_bitacora(prompt, response.text)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    st.warning("⏳ Aura está descansando un momento para procesar tanta información. Por favor, intenta de nuevo en unos segundos.")
                else:
                    registrar_en_bitacora(prompt, "ERROR: " + error_msg)
                    st.error("Ocurrió un error al procesar tu consulta.")

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip')
            st.dataframe(df)
            st.download_button("Descargar Bitácora", data=df.to_csv(), file_name="bitacora.csv")
