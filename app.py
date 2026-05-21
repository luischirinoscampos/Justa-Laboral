import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import json

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")
ARCHIVO_BITACORA = "consultas_local_v2.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"

@st.cache_data
def cargar_conocimiento():
    """Carga el repositorio interno de conocimiento"""
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# --- IDENTIDAD Y ESTRUCTURA (BLINDADA) ---
def renderizar_cabecera():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #0A2540;">Aura</h1>
            <h2 style="color: #1A202C;">Tutora Académica en Línea</h2>
            <p style="color: #4A5568;">Unidad Curricular: Derecho del Trabajo | Prof: Luis Ignacio Chirinos Campos</p>
        </div>
        <div style="background-color: #F7FAFC; padding: 20px; border-radius: 10px; border-left: 5px solid #3182CE;">
            <h3>Bienvenido(a) a Aura</h3>
            <p>Plataforma de orientación pedagógica basada en el material autorizado de la unidad curricular.</p>
            <ul>
                <li><b>Orientación 24/7:</b> Basada estrictamente en doctrina y normativa vigente.</li>
                <li><b>Finalidad:</b> Solventar dudas y guiar el aprendizaje.</li>
                <li><b>Nota:</b> Aura no sustituye al profesor-curador. Úsala con integridad.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

renderizar_cabecera()

# --- LÓGICA DE CHAT ---
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    prompt = st.chat_input("Consulta jurídica...")
    if prompt:
        st.chat_message("user", avatar="👤").markdown(prompt)
        contenedor = st.chat_message("assistant", avatar="✨")
        
        try:
            # Uso del repositorio interno como contexto
            contexto = cargar_conocimiento()
            client = genai.Client(api_key=st.secrets["gemini_api_key"])
            
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=f"Eres Aura, tutora basada en este repositorio: {contexto}")
            )
            
            contenedor.markdown(response.text)
            
            # Bitácora
            ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": prompt, "Respuesta": response.text}]).to_csv(
                ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
            
        except Exception as e:
            if "429" in str(e):
                contenedor.warning("⏳ Aura está procesando el repositorio de conocimiento. Por favor, intenta de nuevo en unos segundos.")
            else:
                contenedor.error("Error al acceder a la base de conocimiento.")

with tab_profesor:
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA):
            st.dataframe(pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip'))
