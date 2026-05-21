import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json
import hashlib
import re

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
    st.session_state.show_profesor = False
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
# 5. REGISTRO EN CSV LOCAL (único almacén)
# ==========================================
def registrar_consulta(pregunta: str, respuesta: str):
    """Registra la consulta en el archivo CSV local"""
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    # Limpiar textos para evitar problemas con comas y saltos de línea
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
    except Exception as e:
        st.error(f"Error al guardar en bitácora: {e}")

# ==========================================
# 6. ESTILOS CSS
# ==========================================
st.markdown("""
    <style>
    /* Fondo blanco absoluto */
    html, body, .stApp, .stAppViewContainer, .main, .block-container,
    [data-testid="stAppViewContainer"], .stChatMessage,
    [data-testid="stChatMessage"], [data-testid="stChatMessageContent"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Texto azul oscuro */
    p, span, li, label, .stMarkdown, h1, h2, h3, h4, div {
        color: #0A2540 !important;
    }
    
    /* Encabezado */
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
    
    /* Input del chat */
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
    }
    
    /* Botones en los extremos */
    div[data-testid="column"]:first-child .stButton button {
        background-color: transparent !important;
        color: #4A5568 !important;
        font-size: 1.3rem !important;
        padding: 4px 12px !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    div[data-testid="column"]:first-child .stButton button:hover {
        color: #0A2540 !important;
        background-color: #F8FAFC !important;
        border-color: #0A2540 !important;
    }
    
    div[data-testid="column"]:last-child .stButton button {
        background-color: transparent !important;
        color: #4A5568 !important;
        font-size: 1.3rem !important;
        padding: 4px 12px !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    div[data-testid="column"]:last-child .stButton button:hover {
        color: #0A2540 !important;
        background-color: #F8FAFC !important;
        border-color: #0A2540 !important;
    }
    
    /* Ocultar elementos */
    #MainMenu, footer, header, [data-testid="stToolbar"] {
        visibility: hidden !important;
        display: none !important;
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

if "show_profesor" not in st.session_state:
    st.session_state.show_profesor = False

if "profesor_autenticado" not in st.session_state:
    st.session_state.profesor_autenticado = False

# ==========================================
# 9. BOTONES EN LOS EXTREMOS
# ==========================================
col_izq, col_espacio, col_der = st.columns([1, 10, 1])

with col_izq:
    if st.button("🔒", key="btn_profesor", help="Acceso profesor"):
        st.session_state.show_profesor = not st.session_state.show_profesor
        st.session_state.profesor_autenticado = False
        st.rerun()

with col_der:
    if st.button("🔄", key="btn_reinicio", help="Reiniciar conversación"):
        reiniciar_conversacion()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 10. PANEL DEL PROFESOR (solo CSV local)
# ==========================================
if st.session_state.show_profesor:
    with st.container():
        st.markdown("---")
        st.markdown("### 📋 Panel del Profesor - Bitácora de Consultas")
        
        if not st.session_state.profesor_autenticado:
            clave = st.text_input("Credencial docente:", type="password", key="profesor_clave")
            if clave:
                if clave == "UCLA2026":
                    st.session_state.profesor_autenticado = True
                    st.success("✅ Acceso concedido")
                    st.rerun()
                else:
                    st.error("❌ Credencial incorrecta")
        else:
            st.success("✅ Sesión activa - Bitácora disponible")
            
            # Verificar si existe el archivo de bitácora
            if os.path.exists(ARCHIVO_BITACORA):
                try:
                    df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
                    
                    if not df.empty:
                        # Mostrar la bitácora completa (más reciente primero)
                        st.subheader("📋 Registro completo de consultas")
                        st.dataframe(df.iloc[::-1], use_container_width=True)
                        
                        # Botón de descarga
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar bitácora (CSV)",
                            data=csv_data,
                            file_name=f"aura_bitacora_{datetime.now().strftime('%d_%m_%Y_%H%M')}.csv",
                            mime="text/csv"
                        )
                        
                        # Estadísticas
                        st.markdown("---")
                        st.subheader("📊 Estadísticas")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total de consultas", len(df))
                        with col2:
                            if "Respuesta de Aura" in df.columns:
                                bloqueos = df[df["Respuesta de Aura"].str.contains("BLOQUEADO", na=False)].shape[0]
                                st.metric("Intentos bloqueados", bloqueos)
                        
                        # Últimas 5 consultas
                        st.markdown("---")
                        st.subheader("🕐 Últimas 5 consultas")
                        st.dataframe(df.tail(5), use_container_width=True)
                        
                    else:
                        st.info("📭 La bitácora está vacía. Realiza una consulta de prueba para comenzar a registrar.")
                except Exception as e:
                    st.error(f"Error al leer la bitácora: {e}")
                    st.info("💡 Puede deberse a un formato incorrecto. Realiza una nueva consulta para regenerar el archivo.")
            else:
                st.warning("📭 Aún no hay registros en la bitácora.")
                st.info("💡 Realiza una consulta de prueba desde el chat para crear el archivo de bitácora.")
                
                # Botón para forzar creación del archivo
                if st.button("📝 Crear archivo de bitácora"):
                    registrar_consulta("Prueba de inicialización", "Bitácora creada correctamente")
                    st.success("✅ Archivo de bitácora creado. Realiza una consulta real para comenzar a registrar.")
                    st.rerun()
            
            # Botón para cerrar panel
            st.markdown("---")
            if st.button("🔒 Cerrar panel", key="cerrar_panel"):
                st.session_state.show_profesor = False
                st.session_state.profesor_autenticado = False
                st.rerun()

# ==========================================
# 11. DETECCIÓN DE EVALUACIONES
# ==========================================
PALABRAS_EVALUACION = [
    "examen", "evaluación", "prueba", "cuestionario", "respuesta del examen",
    "dame la respuesta", "cuál es la opción", "qué pongo", "respuesta correcta",
    "pregunta del parcial", "quiz", "test", "calificación", "nota", "aprobar"
]

def es_intento_evaluacion(pregunta: str) -> bool:
    pregunta_lower = pregunta.lower()
    return any(palabra in pregunta_lower for palabra in PALABRAS_EVALUACION)

# ==========================================
# 12. LÓGICA DINÁMICA DE TOKENS
# ==========================================
def calcular_max_tokens(pregunta: str) -> int:
    pregunta_lower = pregunta.lower()
    
    palabras_complejas = [
        "salario", "prestaciones", "contrato", "despido", "indemnización",
        "vacaciones", "utilidades", "liquidación", "beneficios", "artículo",
        "explique", "compare", "diferencia", "procedimiento", "cálculo",
        "cómo se", "cuál es", "derechos", "obligaciones", "LOTTT"
    ]
    
    palabras_cortas = [
        "qué es", "defina", "significa", "brevemente", "resumido", "sí o no"
    ]
    
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
- Cita las fuentes del contexto cuando las uses.
"""

# ==========================================
# 14. INTERFAZ DE CHAT
# ==========================================
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=message.get("avatar")):
        st.markdown(message["content"])

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
            # === BLOQUEO DE EVALUACIONES ===
            if es_intento_evaluacion(prompt):
                respuesta_bloqueo = (
                    "📚 **Lo siento, no puedo ayudarte con eso.**\n\n"
                    "Mis funciones como Aura están diseñadas exclusivamente para acompañar tu proceso de **aprendizaje**, "
                    "no para resolver evaluaciones. El Prof. Luis Ignacio Chirinos Campos me ha instruido para proteger "
                    "la integridad académica del EDA.\n\n"
                    "✨ Te invito a estudiar el material de la unidad y formularme una duda genuina sobre el contenido."
                )
                st.markdown(respuesta_bloqueo)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_bloqueo})
                registrar_consulta(prompt, "[BLOQUEADO] Intento de evaluación")
                st.stop()
            
            # === VERIFICAR CACHÉ ===
            cache = obtener_cache(prompt)
            if cache:
                st.markdown(cache)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": cache})
                registrar_consulta(prompt, "[RESPUESTA DESDE CACHÉ]")
                st.info("⚡ Respuesta recuperada de memoria (consulta previa idéntica)")
                st.rerun()
            
            # === LLAMAR A GEMINI ===
            if not api_key:
                error_msg = "❌ Error: Configuración de API ausente. Contacta al profesor."
                st.error(error_msg)
                registrar_consulta(prompt, error_msg)
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    
                    # Historial limitado a últimos 4 mensajes
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
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=history,
                        config=config
                    )
                    
                    respuesta_texto = response.text
                    st.markdown(respuesta_texto)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                    
                    # Guardar en caché y bitácora
                    guardar_cache(prompt, respuesta_texto)
                    registrar_consulta(prompt, respuesta_texto)
                    
                except Exception as e:
                    error_str = str(e)
                    if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                        clean_error = "📚 **Aura está recibiendo muchas consultas en este momento.** Por favor, espera 1 minuto y vuelve a intentar."
                    elif "quota" in error_str.lower():
                        clean_error = "📚 **Aura ha alcanzado su límite de consultas por hoy.** El servicio se restablecerá automáticamente."
                    else:
                        clean_error = f"⚠️ Error técnico: {error_str[:150]}"
                    
                    st.error(clean_error)
                    registrar_consulta(prompt, clean_error)
