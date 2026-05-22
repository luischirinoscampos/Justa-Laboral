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
# 6. ESTILOS CSS
# ==========================================
st.markdown("""
    <style>
    html, body, .stApp, .stAppViewContainer, .main, .block-container,
    [data-testid="stAppViewContainer"], .stChatMessage,
    [data-testid="stChatMessage"], [data-testid="stChatMessageContent"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    p, span, li, label, .stMarkdown, h1, h2, h3, h4, div {
        color: #0A2540 !important;
    }
    
    .custom-header {
        text-align: center;
        margin-bottom: 25px;
        padding-bottom: 10px;
        border-bottom: 2px solid #0A2540;
    }
    .line-1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #0A2540 !important;
    }
    .line-2 {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1A3A5C !important;
    }
    .line-3 {
        font-size: 0.95rem;
        color: #4A5568 !important;
    }
    .line-4 {
        font-size: 0.85rem;
        color: #4A5568 !important;
        margin-top: 5px;
    }
    
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
    }
    
    .stButton button {
        background-color: transparent !important;
        color: #4A5568 !important;
        font-size: 1.3rem !important;
        padding: 4px 12px !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        min-width: 48px !important;
        height: 38px !important;
    }
    .stButton button:hover {
        color: #0A2540 !important;
        background-color: #F8FAFC !important;
        border-color: #0A2540 !important;
    }
    
    #MainMenu, footer, header, [data-testid="stToolbar"] {
        visibility: hidden !important;
        display: none !important;
    }
    
    .panel-profesor {
        margin-top: 20px;
        padding: 20px;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        background-color: #FFFFFF;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 7. ENCABEZADO VISUAL
# ==========================================
st.markdown("""
    <div class="custom-header">
        <div class="line-1">✨ Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
        <div class="line-4">Desarrollador: Prof. Luis Ignacio Chirinos Campos</div>
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
# 9. BOTONES SUPERIORES (EN EXTREMOS - TRES COLUMNAS)
# ==========================================
col_izq, col_centro, col_der = st.columns([1, 18, 1])

with col_izq:
    if st.button("🔒", key="btn_profesor", help="Acceso profesor"):
        if st.session_state.modo_profesor:
            st.session_state.modo_profesor = False
            st.session_state.profesor_autenticado = False
        else:
            st.session_state.modo_profesor = True
            st.session_state.profesor_autenticado = False
        st.rerun()

with col_der:
    if st.button("🔄", key="btn_reinicio", help="Reiniciar conversación"):
        reiniciar_conversacion()
        st.rerun()

# col_centro queda vacío

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 10. MODO NORMAL (CHAT VISIBLE)
# ==========================================
if not st.session_state.modo_profesor:
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])
    
    # ==========================================
    # 11. DETECCIÓN DE EVALUACIONES
    # ==========================================
    PALABRAS_EVALUACION = [
        "examen", "evaluación", "prueba", "cuestionario", "respuesta del examen",
        "dame la respuesta", "cuál es la opción", "qué pongo", "respuesta correcta"
    ]
    
    def es_intento_evaluacion(pregunta: str) -> bool:
        return any(palabra in pregunta.lower() for palabra in PALABRAS_EVALUACION)
    
    # ==========================================
    # 12. LÓGICA DINÁMICA DE TOKENS
    # ==========================================
    def calcular_max_tokens(pregunta: str) -> int:
        pregunta_lower = pregunta.lower()
        palabras_complejas = [
            "salario", "prestaciones", "contrato", "despido", "indemnización",
            "vacaciones", "utilidades", "liquidación", "beneficios", "artículo"
        ]
        palabras_cortas = ["qué es", "defina", "significa", "brevemente"]
        puntuacion = 0
        for palabra in palabras_complejas:
            if palabra in pregunta_lower:
                puntuacion += 2
        for palabra in palabras_cortas:
            if palabra in pregunta_lower:
                puntuacion -= 2
        if len(pregunta) > 150:
            puntuacion += 1
        if puntuacion >= 2:
            return 4096
        elif puntuacion <= -1:
            return 1024
        else:
            return 2048
    
    # ==========================================
    # 13. SYSTEM INSTRUCTION
    # ==========================================
    def get_system_instruction():
        return f"""
Eres AURA, tutora de Derecho del Trabajo del EDA creado por el Prof. Luis Ignacio Chirinos Campos.

CONTEXTO DE CÁTEDRA:
{CONTEXTO_BASE}

REGLAS:
- Responde con claridad, calidez y rigor jurídico.
- Usa **negritas** para conceptos clave.
- NO ayudas a resolver exámenes o evaluaciones.
- Usa SOLO Markdown estándar. NO uses fórmulas LaTeX ($$).
"""
    
    # ==========================================
    # 14. PROCESAMIENTO DEL CHAT (CON REINTENTOS SILENCIOSOS)
    # ==========================================
    prompt = st.chat_input("Escribe tu consulta jurídica aquí...")
    
    if prompt:
        tiempo_actual = time.time()
        if tiempo_actual - st.session_state.ultimo_envio < 15:
            st.warning(f"⏳ Espera {int(15 - (tiempo_actual - st.session_state.ultimo_envio))} segundos.")
        else:
            st.session_state.ultimo_envio = tiempo_actual
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})
            
            with st.chat_message("assistant", avatar="✨"):
                # Bloqueo de evaluaciones
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
                    st.info("⚡ Respuesta recuperada de memoria")
                    st.rerun()
                
                # Llamar a Gemini con reintentos silenciosos
                if not api_key:
                    st.error("Error: API Key no configurada.")
                else:
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
                    
                    # REINTENTOS SILENCIOSOS ANTE ERROR 503
                    reintentos = 0
                    exito = False
                    respuesta_texto = None
                    
                    while reintentos < 3 and not exito:
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=history,
                                config=config
                            )
                            respuesta_texto = response.text
                            exito = True
                        except Exception as e:
                            error_str = str(e)
                            reintentos += 1
                            if reintentos < 3 and ("503" in error_str or "UNAVAILABLE" in error_str or "RESOURCE_EXHAUSTED" in error_str or "429" in error_str):
                                time.sleep(1)  # Espera silenciosa
                                continue  # Reintentar
                            else:
                                # Si es el último reintento o error diferente, mostrar mensaje amigable
                                if "503" in error_str or "UNAVAILABLE" in error_str or "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                                    respuesta_texto = "📚 **Aura está recibiendo muchas consultas en este momento.** Por favor, espera 1 minuto y vuelve a intentar. Tu pregunta es importante."
                                else:
                                    respuesta_texto = f"⚠️ Error técnico: {error_str[:150]}"
                                exito = True  # Salir del bucle con mensaje de error
                    
                    # Mostrar respuesta (éxito o mensaje amigable)
                    st.markdown(respuesta_texto)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                    
                    # Guardar en caché solo si fue una respuesta exitosa (no mensaje de error)
                    if respuesta_texto and not respuesta_texto.startswith(("📚", "⚠️")):
                        guardar_cache(prompt, respuesta_texto)
                    
                    registrar_consulta(prompt, respuesta_texto)

# ==========================================
# 15. MODO PROFESOR (CHAT OCULTO)
# ==========================================
else:
    st.markdown('<div class="panel-profesor">', unsafe_allow_html=True)
    st.markdown("## 📋 Panel del Profesor")
    
    if not st.session_state.profesor_autenticado:
        clave = st.text_input("Credencial docente:", type="password", key="profesor_clave")
        if clave:
            if clave == "UCLA2026":
                st.session_state.profesor_autenticado = True
                st.success("✅ Acceso concedido")
                st.rerun()
            else:
                st.error("❌ Credencial incorrecta")
        
        if st.button("← Volver al chat", key="volver_chat"):
            st.session_state.modo_profesor = False
            st.session_state.profesor_autenticado = False
            st.rerun()
    
    else:
        st.markdown("### 📊 Bitácora de Consultas")
        
        if os.path.exists(ARCHIVO_BITACORA):
            try:
                df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
                if not df.empty:
                    st.dataframe(df.iloc[::-1], use_container_width=True)
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar bitácora (CSV)",
                        data=csv_data,
                        file_name=f"aura_bitacora_{datetime.now().strftime('%d_%m_%Y_%H%M')}.csv",
                        mime="text/csv"
                    )
                    
                    st.markdown("---")
                    st.markdown("### 📈 Estadísticas")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total de consultas", len(df))
                    with col2:
                        bloqueos = df[df["Respuesta de Aura"].str.contains("BLOQUEADO", na=False)].shape[0] if "Respuesta de Aura" in df.columns else 0
                        st.metric("Intentos bloqueados", bloqueos)
                    
                    st.markdown("---")
                    st.markdown("### 🕐 Últimas 5 consultas")
                    st.dataframe(df.tail(5), use_container_width=True)
                else:
                    st.info("📭 La bitácora está vacía.")
            except Exception as e:
                st.error(f"Error al leer la bitácora: {e}")
        else:
            st.warning("📭 Aún no hay registros en la bitácora.")
        
        st.markdown("---")
        if st.button("🔒 Cerrar sesión y volver al chat", key="cerrar_sesion"):
            st.session_state.modo_profesor = False
            st.session_state.profesor_autenticado = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
