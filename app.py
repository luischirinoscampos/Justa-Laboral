import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Aura", page_icon="✨", layout="centered")
ARCHIVO_BITACORA = "consultas_local_v2.csv"

# --- FUNCIONES CORE ---
def registrar_en_bitacora(pregunta, respuesta):
    """Guarda siempre, independientemente de errores de la API"""
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        df = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": pregunta, "Respuesta": respuesta}])
        df.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    except Exception as e:
        st.error(f"Error crítico en bitácora: {e}")

# --- INTERFAZ ---
# ... (Mantén tu CSS y encabezado aquí) ...

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    prompt = st.chat_input("Consulta jurídica...")
    if prompt:
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        
        # 1. Registro PREVIO (Garantiza que el dato queda grabado)
        with st.chat_message("assistant", avatar="✨"):
            try:
                client = genai.Client(api_key=st.secrets["gemini_api_key"])
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                
                # 2. Guardado
                registrar_en_bitacora(prompt, response.text)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            except Exception as e:
                # 3. Guardado de respaldo en caso de error de API
                registrar_en_bitacora(prompt, "ERROR DE API: " + str(e))
                st.warning("⚠️ Aura procesó la consulta, pero hubo un error de conexión.")

with tab_profesor:
    st.subheader("Bitácora")
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip')
            st.dataframe(df)
            st.download_button("Descargar", data=df.to_csv(), file_name="bitacora.csv")
        else:
            st.info("Aún no hay datos.")
