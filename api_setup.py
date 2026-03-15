import requests
import streamlit as st

def get_secrets():
    """Streamlit Secrets에서 API 키를 안전하게 가져옵니다."""
    try:
        return {
            "GROQ": st.secrets["GROQ_API_KEY"],
            "GEMINI": st.secrets["GEMINI_API_KEY"],
            "DISCORD": st.secrets["DISCORD_WEBHOOK_URL"]
        }
    except KeyError:
        st.error("🚨 Streamlit Secrets에 API 키가 세팅되지 않았습니다!")
        st.stop()

@st.cache_data(ttl=3600)
def get_groq_models(api_key):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        res = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
        data = res.json()
        return [m["id"] for m in data["data"] if "whisper" not in m["id"]]
    except:
        return ["llama-3.3-70b-versatile"]

@st.cache_data(ttl=3600)
def get_gemini_models(api_key):
    try:
        res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")
        data = res.json()
        return [m["name"] for m in data["models"] if "generateContent" in m.get("supportedGenerationMethods", [])]
    except:
        return ["models/gemini-1.5-flash"]
