import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN Y MÓDULOS ---
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

MODULOS_AURA = {
    "PROGRAMA": "Derecho del Trabajo: Sujetos, contrato, jornada, extinción, derechos colectivos.",
    "LEGAL": "LOTTT: Principios de justicia social, estabilidad, carácter remunerativo del salario, progresividad.",
    "U1": "Principios: Trabajo como hecho social, irrenunciabilidad, primacía de la realidad, in dubio pro operario, estabilidad laboral.",
    "U2": "Sujetos: Trabajador, Patrono. Contrato: Consensual, oneroso, subordinado. Extinción: Despido y retiro.",
    "U3": "Salario: Normal e Integral. Jornada: Diurna (8h), Nocturna (7h), Mixta (7.5h). Prestaciones: Garantía trimestral, cálculo de vacaciones.",
    "U4": "Derecho Colectivo: Libertad sindical, fuero, negociación colectiva, conflictos colectivos, huelga.",
    "EJERCICIOS": "Liquidación: Definir salario base, días de vacaciones, recargos de horas extra (50% diurnas, 80% nocturnas)."
}

ARCHIVO_BITACORA = "consultas_local.csv"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"

# --- 2. FUNCIONES DE APOYO ---
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
        return gc.open(NOMBRE_HOJA_SHEETS).sheet1
    except: return None

def registrar_consulta_dual(p, r):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia, r_limpia = str(p).replace("\n", " "), str(r).replace("\n", " ")
    df = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": p_limpia, "Respuesta de Aura": r_limpia}])
    if os.path.exists(ARCHIVO_BITACORA): df.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False)
    else: df.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False)
    hoja = conectar_google_sheets()
    if hoja: hoja.append_row([ahora, p_limpia, r_limpia])

def obtener_respuesta_aura(prompt_usuario):
    """Función protegida para generar respuesta solo cuando es llamada."""
    try:
        client = genai.Client(api_key=st.secrets.get("gemini_api_key"))
        # Enrutador
        cat_prompt = f"Clasifica: '{prompt_usuario}' en: {list(MODULOS_AURA.keys())}. Devuelve SOLO la clave."
        resp_cat = client.models.generate_content(model="gemini-2.0-flash", contents=cat_prompt)
        contexto = MODULOS_AURA.get(resp_cat.text.strip(), MODULOS_AURA["LEGAL"])
        
        # Generación
        config = types.GenerateContentConfig(system_instruction=f"Eres Aura. Contexto: {contexto}. Responde pedagógicamente.", temperature=0.3)
        return client.models.generate_content(model='gemini-2.0-flash', contents=prompt_usuario, config=config).text
    except Exception as e:
        return f"Error de conexión: {str(e)}"

# --- 3. INTERFAZ Y CSS ---
st.markdown("""<style>
    .custom-header { text-align: center; font-family: 'Inter', sans-serif; }
    .line-1 { color: #0A2540; font-size: 2.4rem; font-weight: 700; }
    .line-2 { color: #1A202C; font-size: 1.4rem; font-weight: 600; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="custom-header"><div class="line-1">Aura</div><div class="line-2">Tutora Académica</div></div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! ¿En qué puedo apoyarte hoy?"}]

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

with tab_eda:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("Escribe tu consulta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            respuesta = obtener_respuesta_aura(prompt)
            st.markdown(respuesta)
            registrar_consulta_dual(prompt, respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
            st.rerun()

with tab_profesor:
    st.subheader("Bitácora")
    if st.text_input("Credencial:", type="password") == "UCLA2026":
        if os.path.exists(ARCHIVO_BITACORA): st.dataframe(pd.read_csv(ARCHIVO_BITACORA))
        if st.button("Probar GSheets"): st.write("Conexión activa" if conectar_google_sheets() else "Error")
