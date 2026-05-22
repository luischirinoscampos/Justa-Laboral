import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json
import hashlib

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

api_key = st.secrets.get("gemini_api_key", None)

ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"

# ==========================================
# 2. FUNCIÓN PARA REINICIAR CONVERSACIÓN
# ==========================================
def reiniciar_conversacion():
    st.session_state.messages = [
        {
            "role": "assistant",
            "avatar": "✨",
            "content": (
                "📍 ¡Hola! Soy **Aura**, tu tutora académica en Derecho del Trabajo.\n\n"
                "Pertenezco al **Ecosistema Digital de Aprendizaje (EDA)** de esta unidad curricular, "
                "creada y desarrollada por el **Prof. Luis Ignacio Chirinos Campos**.\n\n"
                "Estoy aquí para acompañarte en tu **aprendizaje** con claridad, calidez y rigor jurídico.\n\n"
                "🛠️ **¿Qué puedo hacer por ti?**\n"
                "- Resolver dudas sobre los contenidos de la unidad\n"
                "- Explicar conceptos jurídicos complejos de forma sencilla\n"
                "- Ayudarte a preparar tus estudios\n"
                "- Orientarte en casos prácticos\n\n"
                "⚠️ **Importante**: No puedo ayudarte a resolver exámenes o evaluaciones.\n\n"
                "Cuéntame, ¿qué tema o consulta académica te trae hoy? 💬"
            )
        }
    ]
    st.session_state.ultimo_envio = 0.0
    st.session_state.modo_profesor = False
    st.session_state.profesor_autenticado = False

# ==========================================
# 3. CACHÉ DE RESPUESTAS
# ==========================================
CACHE_RESPUESTAS = {}
CACHE_MAX = 200

def obtener_cache(pregunta: str) -> str:
    clave = hashlib.md5(pregunta.lower().encode()).hexdigest()
    return CACHE_RESPUESTAS.get(clave)

def guardar_cache(pregunta: str, respuesta: str):
    clave = hashlib.md5(pregunta.lower().encode()).hexdigest()
    if len(CACHE_RESPUESTAS) >= CACHE_MAX:
        for k in list(CACHE_RESPUESTAS.keys())[:20]:
            del CACHE_RESPUESTAS[k]
    CACHE_RESPUESTAS[clave] = respuesta

# ==========================================
# 4. CARGA DEL CONOCIMIENTO
# ==========================================
@st.cache_data
def cargar_contexto_catedra():
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        try:
            with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
                contenido = f.read()
                if len(contenido) > 2500:
                    return contenido[:2500] + "\n...[Contenido adicional disponible]"
                return contenido
        except Exception:
            return ""
    return ""

CONTEXTO_BASE = cargar_contexto_catedra()

# ==========================================
# 5. REGISTRO EN CSV LOCAL
# ==========================================
def registrar_consulta(pregunta: str, respuesta: str):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    pregunta_limpia = str(pregunta).replace("\n", " ").replace("\r", " ").replace(",", " ").strip()
    respuesta_limpia = str(respuesta).replace("\n", " ").replace("\r", " ").replace(",", " ").strip()
    
    nuevo_registro = pd.DataFrame([{
        "Cuándo": ahora,
        "Qué preguntó": pregunta_limpia,
        "Respuesta de Aura": respuesta_limpia
    }])
    
    try:
        if os.path.exists(ARCHIVO_BITACORA):
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False, encoding='utf-8')
        else:
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False, encoding='utf-8')
    except Exception:
        pass

# ==========================================
# 6. ESTILOS CSS LIMPIOS
# ==========================================
st.markdown("""
    <style>
    /* Fondo blanco */
    html, body, .stApp, .stAppViewContainer, .main, .block-container {
        background-color: #FFFFFF !important;
    }
    
    /* Texto azul oscuro */
    p, span, li, label, .stMarkdown, h1, h2, h3, h4, div {
        color: #0A2540 !important;
    }
    
    /* Header simple */
    .custom-header {
        text-align: center;
        margin-bottom: 20px;
    }
    .line-1 {
        font-size: 2rem;
        font-weight: 700;
        color: #0A2540 !important;
    }
    .line-2 {
        font-size: 1rem;
        font-weight: 500;
        color: #1A3A5C !important;
    }
    .line-3 {
        font-size: 0.85rem;
        color: #4A5568 !important;
    }
    
    /* Input del chat */
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
    }
    
    /* Botones */
    .stButton button {
        background-color: transparent !important;
        color: #4A5568 !important;
        font-size: 1.2rem !important;
        padding: 4px 12px !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    .stButton button:hover {
        color: #0A2540 !important;
        background-color: #F8FAFC !important;
        border-color: #0A2540 !important;
    }
    
    /* Ocultar elementos de Streamlit */
    #MainMenu, footer, header, [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Panel del profesor */
    .panel-profesor {
        margin-top: 30px;
        padding: 20px;
        border-top: 2px solid #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 7. HEADER SIMPLE (SIN ICONO EXTRA)
# ==========================================
st.markdown("""
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Derecho del Trabajo | EDA - UCLA</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 8. INICIALIZACIÓN
# ==========================================
if "messages" not in st.session_state:
    reiniciar_conversacion()

if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

if "modo_profesor" not in st.session_state:
    st.session_state.modo_profesor = False

if "profesor_autenticado" not in st.session_state:
    st.session_state.profesor_autenticado = False

# ==========================================
# 9. BOTONES EN EXTREMOS (TRES COLUMNAS)
# ==========================================
col_izq, col_centro, col_der = st.columns([1, 10, 1])

with col_izq:
    if st.button("🔒", key="profesor_btn"):
        if st.session_state.modo_profesor:
            st.session_state.modo_profesor = False
            st.session_state.profesor_autenticado = False
        else:
            st.session_state.modo_profesor = True
            st.session_state.profesor_autenticado = False
        st.rerun()

with col_der:
    if st.button("🔄", key="reinicio_btn"):
        reiniciar_conversacion()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 10. MODO NORMAL (CHAT)
# ==========================================
if not st.session_state.modo_profesor:
    # Mostrar mensajes
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])
    
    # ==========================================
    # 11. DETECCIÓN DE EVALUACIONES
    # ==========================================
    PALABRAS_EVALUACION = [
        "examen", "evaluación", "prueba", "cuestionario",
        "dame la respuesta", "cuál es la opción", "respuesta correcta"
    ]
    
    def es_intento_evaluacion(pregunta: str) -> bool:
        return any(palabra in pregunta.lower() for palabra in PALABRAS_EVALUACION)
    
    # ==========================================
    # 12. LÓGICA DINÁMICA DE TOKENS
    # ==========================================
    def calcular_max_tokens(pregunta: str) -> int:
        pregunta_lower = pregunta.lower()
        palabras_largas = ["salario", "prestaciones", "contrato", "vacaciones", "utilidades"]
        palabras_cortas = ["qué es", "defina", "brevemente", "dos líneas"]
        puntos = 0
        for p in palabras_largas:
            if p in pregunta_lower:
                puntos += 2
        for p in palabras_cortas:
            if p in pregunta_lower:
                puntos -= 1
        if puntos >= 2:
            return 4096
        elif puntos <= 0:
            return 1024
        else:
            return 2048
    
    # ==========================================
    # 13. SYSTEM INSTRUCTION
    # ==========================================
    def get_system_instruction():
        return f"""Eres Aura, tutora de Derecho del Trabajo.

CONTEXTO:
{CONTEXTO_BASE}

REGLAS:
- Sé clara, cálida y pedagógica.
- Usa **negritas** para conceptos clave.
- NO ayudas a resolver exámenes.
- NO uses fórmulas LaTeX ($$). Usa solo Markdown normal.
- Si te piden "explicación fácil", usa ejemplos cotidianos.
"""
    
    # ==========================================
    # 14. INPUT Y PROCESAMIENTO
    # ==========================================
    prompt = st.chat_input("Escribe tu consulta jurídica aquí...")
    
    if prompt:
        ahora = time.time()
        if ahora - st.session_state.ultimo_envio < 15:
            st.warning(f"⏳ Espera {int(15 - (ahora - st.session_state.ultimo_envio))} segundos.")
        else:
            st.session_state.ultimo_envio = ahora
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})
            
            with st.chat_message("assistant", avatar="✨"):
                # Bloquear evaluación
                if es_intento_evaluacion(prompt):
                    respuesta = "📚 **Lo siento, no puedo ayudarte con evaluaciones.** Estoy para apoyar tu aprendizaje."
                    st.markdown(respuesta)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta})
                    registrar_consulta(prompt, "[BLOQUEADO]")
                    st.stop()
                
                # Verificar caché
                cache = obtener_cache(prompt)
                if cache:
                    st.markdown(cache)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": cache})
                    registrar_consulta(prompt, "[CACHÉ]")
                    st.rerun()
                
                if not api_key:
                    st.error("Error: API Key no configurada.")
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        history = []
                        for msg in st.session_state.messages[-4:]:
                            role = "model" if msg["role"] == "assistant" else "user"
                            history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                        
                        max_tokens = calcular_max_tokens(prompt)
                        config = types.GenerateContentConfig(
                            system_instruction=get_system_instruction(),
                            temperature=0.2,
                            max_output_tokens=max_tokens
                        )
                        
                        # Reintentos silenciosos
                        respuesta_texto = None
                        for intento in range(3):
                            try:
                                response = client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=history,
                                    config=config
                                )
                                respuesta_texto = response.text
                                break
                            except Exception as e:
                                if intento < 2 and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                                    time.sleep(1)
                                else:
                                    respuesta_texto = "📚 **Aura está recibiendo muchas consultas.** Espera 1 minuto e intenta de nuevo."
                        
                        st.markdown(respuesta_texto)
                        st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                        
                        if respuesta_texto and not respuesta_texto.startswith("📚"):
                            guardar_cache(prompt, respuesta_texto)
                        
                        registrar_consulta(prompt, respuesta_texto)
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")
                        registrar_consulta(prompt, f"ERROR: {str(e)[:100]}")

# ==========================================
# 15. MODO PROFESOR
# ==========================================
else:
    st.markdown('<div class="panel-profesor">', unsafe_allow_html=True)
    st.markdown("## 📋 Panel del Profesor")
    
    if not st.session_state.profesor_autenticado:
        clave = st.text_input("Credencial docente:", type="password")
        if clave:
            if clave == "UCLA2026":
                st.session_state.profesor_autenticado = True
                st.rerun()
            else:
                st.error("❌ Credencial incorrecta")
        
        if st.button("← Volver al chat"):
            st.session_state.modo_profesor = False
            st.rerun()
    else:
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
            if not df.empty:
                st.dataframe(df.iloc[::-1], use_container_width=True)
                st.download_button("📥 Descargar CSV", df.to_csv(index=False).encode('utf-8'), "bitacora.csv")
            else:
                st.info("Bitácora vacía")
        else:
            st.info("Aún no hay registros")
        
        if st.button("🔒 Cerrar sesión"):
            st.session_state.modo_profesor = False
            st.session_state.profesor_autenticado = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
