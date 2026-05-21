import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import json

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

api_key = st.secrets.get("gemini_api_key", None)
ARCHIVO_BITACORA = "consultas_local_v2.csv"

def registrar_en_bitacora(pregunta, respuesta):
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        df = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": pregunta, "Respuesta": respuesta}])
        df.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    except Exception:
        pass

# 2. ENCABEZADO E IDENTIDAD (RESTAURADO EXACTAMENTE)
st.markdown("""
    <div style="text-align: center;">
        <h1 style="color: #0A2540;">Aura</h1>
        <h2 style="color: #1A202C;">Tutora Académica en Línea</h2>
        <p style="color: #4A5568;">Unidad Curricular: Derecho del Trabajo | Prof: Luis Ignacio Chirinos Campos</p>
    </div>
""", unsafe_allow_html=True)

# 3. MENSAJE PRELIMINAR DE PRESENTACIÓN (RESTAURADO EXACTAMENTE)
st.info("""
### Bienvenido(a) a Aura
Esta plataforma está diseñada para brindar orientación pedagógica y acompañamiento en el estudio del Derecho del Trabajo. 
* **Orientación 24/7:** Respuestas basadas estrictamente en la doctrina y normativa laboral vigente.
* **Finalidad:** Solventar dudas, repasar conceptos esenciales y guiar tu proceso de aprendizaje.
* **Nota:** Aura no sustituye al profesor-curador. Úsala con integridad académica.
""")

# 4. LÓGICA DE PESTAÑAS Y CHAT
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    prompt = st.chat_input("Consulta jurídica...")
    if prompt:
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        with st.chat_message("assistant", avatar="✨"):
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                registrar_en_bitacora(prompt, response.text)
                st.markdown(response.text)
            except Exception as e:
                if "429" in str(e):
                    st.warning("⏳ Aura está descansando un momento para procesar tanta información. Por favor, intenta de nuevo en unos segundos.")
                else:
                    st.error("Ocurrió un error al procesar tu consulta.")

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip')
            st.dataframe(df)
            st.download_button("Descargar", data=df.to_csv(), file_name="bitacora.csv")
