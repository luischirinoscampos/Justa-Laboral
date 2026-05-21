import streamlit as st
from datetime import datetime
import pandas as pd
import os
from google import genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")
ARCHIVO_BITACORA = "consultas_local_v2.csv"

# --- ESTRUCTURA VISUAL (FUERA DE LA LÓGICA DE IA) ---
def mostrar_interfaz():
    st.markdown("""
        <div style="text-align: center;">
            <h1 style="color: #0A2540;">Aura</h1>
            <h2 style="color: #1A202C;">Tutora Académica en Línea</h2>
            <p style="color: #4A5568;">Unidad Curricular: Derecho del Trabajo | Prof: Luis Ignacio Chirinos Campos</p>
        </div>
        <div style="background-color: #EBF8FF; padding: 15px; border-radius: 10px;">
            <h3>Bienvenido(a) a Aura</h3>
            <p>Esta plataforma brinda orientación pedagógica y acompañamiento en el estudio del Derecho del Trabajo.</p>
            <ul>
                <li><b>Orientación 24/7:</b> Basada en doctrina y normativa vigente.</li>
                <li><b>Finalidad:</b> Solventar dudas y guiar tu aprendizaje.</li>
                <li><b>Nota:</b> Aura no sustituye al profesor-curador. Úsala con integridad.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# --- EJECUCIÓN ---
mostrar_interfaz() # Esto se muestra SIEMPRE, no importa si la IA falla

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    prompt = st.chat_input("Consulta jurídica...")
    if prompt:
        st.chat_message("user", avatar="👤").markdown(prompt)
        contenedor = st.chat_message("assistant", avatar="✨")
        
        try:
            client = genai.Client(api_key=st.secrets["gemini_api_key"])
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            contenedor.markdown(response.text)
            
            # Registro en bitácora
            ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            df = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": prompt, "Respuesta": response.text}])
            df.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
            
        except Exception as e:
            if "429" in str(e):
                contenedor.warning("⏳ Límite de consultas alcanzado. Por favor, intenta de nuevo en unos segundos.")
            else:
                contenedor.error("Error al procesar la consulta.")

with tab_profesor:
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip')
            st.dataframe(df)
