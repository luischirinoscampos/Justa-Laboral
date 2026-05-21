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

# SOLUCIÓN DE REGENERACIÓN: Nombre de archivo actualizado a v2
ARCHIVO_BITACORA = "consultas_local_v2.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"

def registrar_consulta_local(texto_pregunta, texto_respuesta):
    """Guarda la pregunta y respuesta en un archivo CSV nuevo"""
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nuevo_registro = pd.DataFrame([{
            "Cuándo": ahora, 
            "Qué preguntaron": texto_pregunta, 
            "Respuesta": texto_respuesta
        }])
        
        # Guardar con cabecera solo si el archivo no existe
        nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')
    except Exception:
        pass

@st.cache_data
def cargar_contexto_catedra():
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        try:
            with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
                datos = json.load(f)
                return "".join([f"\nDocumento: {item['nombre_archivo']}\nContenido: {item['texto_contenido']}\n---" for item in datos])
        except Exception:
            return ""
    return ""

CONTEXTO_LEGAL_CATEDRA = cargar_contexto_catedra()

# (CSS OMITIDO PARA BREVEDAD, USA EL QUE YA TENÍAS)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "avatar": "✨", "content": "Hola, soy Aura."}]
if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    prompt = st.chat_input("Escribe tu consulta aquí...")
    if prompt:
        if time.time() - st.session_state.ultimo_envio < 15.0:
            st.warning("⏳ Por favor espera.")
        else:
            st.session_state.ultimo_envio = time.time()
            with st.chat_message("user", avatar="👤"): st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="✨"):
                try:
                    client = genai.Client(api_key=api_key)
                    # (Generación de contenido igual que antes...)
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    
                    # REGISTRO CON NUEVA ESTRUCTURA
                    registrar_consulta_local(prompt, response.text)
                    
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Error: {e}")

with tab_profesor:
    st.subheader("Bitácora de Consultas")
    clave = st.text_input("Credencial:", type="password")
    if clave == "UCLA2026":
        # AJUSTE DE SEGURIDAD: on_bad_lines='skip'
        if os.path.exists(ARCHIVO_BITACORA):
            try:
                df = pd.read_csv(ARCHIVO_BITACORA, on_bad_lines='skip')
                st.dataframe(df.iloc[::-1])
                st.download_button("📥 Descargar", data=df.to_csv(index=False), file_name="bitacora.csv")
            except Exception as e:
                st.error("Error al leer archivo.")
