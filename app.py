import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# --- CONOCIMIENTO EMBEBIDO ---
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
    api_key = st.secrets.get("gemini_api_key")
    client = genai.Client(api_key=api_key)
    prompt_cat = f"Clasifica: '{consulta}' en: {list(MODULOS_AURA.keys())}. Devuelve SOLO la clave."
    try:
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_cat)
        return MODULOS_AURA.get(resp.text.strip(), MODULOS_AURA["LEGAL"])
    except: return MODULOS_AURA["LEGAL"]

# --- LÓGICA DE INTERFAZ ---
st.markdown('<div class="custom-header"><div class="line-1">Aura</div><div class="line-2">Tutora Académica</div></div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "avatar": "✨", "content": "¡Hola! ¿En qué te ayudo hoy?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg.get("avatar")): st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu consulta..."):
    # 1. Mostrar usuario
    with st.chat_message("user", avatar="👤"): st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})

    # 2. Generar respuesta (PROTEGIDO DENTRO DEL IF)
    with st.chat_message("assistant", avatar="✨"):
        contexto = enrutador_y_contexto(prompt)
        client = genai.Client(api_key=st.secrets.get("gemini_api_key"))
        
        config = types.GenerateContentConfig(
            system_instruction=f"Eres Aura. Contexto: {contexto}. Responde pedagógicamente.",
            temperature=0.3
        )
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt, 
            config=config
        )
        
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": response.text})
