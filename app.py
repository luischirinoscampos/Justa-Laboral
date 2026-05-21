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

api_key = st.secrets.get("gemini_api_key", None)
ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"

# --- FUNCIONES DE OPTIMIZACIÓN ---

def obtener_contexto_relevante(query):
    """Implementación de RAG: recupera solo fragmentos relevantes."""
    if not os.path.exists(ARCHIVO_CONOCIMIENTO): return ""
    try:
        with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
            datos = json.load(f)
            query_words = set(query.lower().split())
            relevante = []
            for item in datos:
                contenido = item.get('texto_contenido', '').lower()
                if any(w in contenido for w in query_words):
                    relevante.append(item['texto_contenido'])
            return "\n".join(relevante[:3]) # Limita a los 3 más relevantes
    except: return ""

def conectar_google_sheets():
    """Conexión persistente almacenada en session_state."""
    if "gsheet_client" in st.session_state:
        return st.session_state["gsheet_client"]
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        private_key = st.secrets["gspread"]["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict({**st.secrets["gspread"], "private_key": private_key}, scope)
        gc = gspread.authorize(creds)
        st.session_state["gsheet_client"] = gc.open(NOMBRE_HOJA_SHEETS).sheet1
        return st.session_state["gsheet_client"]
    except Exception as e:
        st.session_state["error_gsheets"] = str(e)
        return None

def registrar_consulta_dual(texto_pregunta, respuesta_o_error):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia, r_limpia = [str(x).replace("\n", " ").strip() for x in [texto_pregunta, respuesta_o_error]]
    
    # CSV Local
    pd.DataFrame([{"Cuándo": ahora, "Pregunta": p_limpia, "Respuesta": r_limpia}]).to_csv(
        ARCHIVO_BITACORA, mode='a', header=not os.path.exists(ARCHIVO_BITACORA), index=False, encoding='utf-8')

    # Sheets
    hoja = conectar_google_sheets()
    if hoja: hoja.append_row([ahora, p_limpia, r_limpia])

# 2. INTERFAZ Y LÓGICA
st.markdown("""<style>...CSS_PREVIO...</style>""", unsafe_allow_html=True) # Mantener estilos previos

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "avatar": "✨", "content": "¡Hola! Soy Aura..."}]

st.markdown('<div class="custom-header">...ENCABEZADO...</div>', unsafe_allow_html=True)

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    if prompt := st.chat_input("Escribe tu consulta aquí..."):
        st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})
        
        with st.chat_message("assistant", avatar="✨"):
            try:
                contexto = obtener_contexto_relevante(prompt)
                system_instruction = f"Eres Aura, tutora académica experta. Contexto disponible: {contexto}. Usa lenguaje neutral e inclusivo, adecuado para modalidad virtual o a distancia."
                
                client = genai.Client(api_key=api_key)
                # Ventana deslizante: últimos 6 mensajes
                history = [types.Content(role="model" if m["role"]=="assistant" else "user", 
                           parts=[types.Part.from_text(m["content"])]) for m in st.session_state.messages[-6:]]
                
                response = client.models.generate_content(model='gemini-2.5-flash', contents=history, 
                                                        config=types.GenerateContentConfig(system_instruction=system_instruction))
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": response.text})
                registrar_consulta_dual(prompt, response.text)
            except Exception as e:
                st.error("Error al procesar la respuesta.")
                registrar_consulta_dual(prompt, str(e))

with tab_profesor:
    # ... Lógica de bitácora manteniendo la autenticación ya existente ...
