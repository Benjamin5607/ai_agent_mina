import os
import streamlit as st
import requests
from groq import Groq
import google.generativeai as genai

# ==========================================
# 1. 페이지 세팅 및 UI 디자인
# ==========================================
st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center")

# ==========================================
# 2. 시크릿 키(보안) 불러오기
# ==========================================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
except KeyError:
    st.error("🚨 Streamlit Secrets에 API 키가 세팅되지 않았습니다! (설정 탭에서 입력 필요)")
    st.stop()

# 클라이언트 초기화
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 3. 모델 리스트 실시간 불러오기 (캐싱 적용)
# ==========================================
# 깃허브 액션(정찰병) 없이 파이썬이 직접 그록과 제미나이를 찔러서 가져옵니다.
# @st.cache_data를 쓰면 1시간 동안은 API를 찌르지 않고 기억(캐시)해서 속도가 미치게 빠릅니다!
@st.cache_data(ttl=3600)
def get_groq_models():
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        res = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
        data = res.json()
        return [m["id"] for m in data["data"] if "whisper" not in m["id"]]
    except:
        return ["llama-3.3-70b-versatile"]

@st.cache_data(ttl=3600)
def get_gemini_models():
    try:
        res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}")
        data = res.json()
        return [m["name"] for m in data["models"] if "generateContent" in m.get("supportedGenerationMethods", [])]
    except:
        return ["models/gemini-1.5-flash"]

# ==========================================
# 4. 사이드바 (설정 메뉴)
# ==========================================
with st.sidebar:
    st.header("⚙️ 랍스타 시스템 설정")
    
    st.subheader("1. 뇌(Groq) & 손발(Gemini) 선택")
    groq_models = get_groq_models()
    selected_groq = st.selectbox("🧠 사고력 (Groq)", groq_models, index=0 if "llama-3.3-70b-versatile" not in groq_models else groq_models.index("llama-3.3-70b-versatile"))
    
    gemini_models = get_gemini_models()
    selected_gemini = st.selectbox("👐 실행력 (Gemini)", gemini_models, index=0)
    
    st.subheader("2. 직무 할당 및 도구")
    tasks = {
        "ops_risk": ("BPO Ops / Risk Management", ["RISK_RADAR_ENDPOINT", "CRAWLER_API_KEY"]),
        "coding": ("Coding / Developer", ["NEWS_API_KEY"]),
        "contents": ("Contents Creator", ["YOUTUBE_API_KEY", "PIXABAY_KEY"]),
        "data": ("Data Analysis / Documentation", ["OPENWEATHER_KEY"])
    }
    
    task_keys = list(tasks.keys())
    task_names = [tasks[k][0] for k in task_keys]
    selected_task_name = st.selectbox("직무 선택", task_names)
    
    # 선택된 직무에 맞춰 추가 API 입력창 동적 생성
    selected_task_key = task_keys[task_names.index(selected_task_name)]
    required_apis = tasks[selected_task_key][1]
    
    extra_keys = {}
    if required_apis:
        st.caption("선택사항: 직무 특화 API 키 입력")
        for api in required_apis:
            extra_keys[api] = st.text_input(api, type="password")
            
    st.divider()
    st.caption("비밀번호나 API 키는 Streamlit Cloud 서버단에서 안전하게 처리됩니다.")

# ==========================================
# 5. 디스코드 보고 로직
# ==========================================
def report_to_discord(title, description, color=16730698):
    payload = {
        "username": "랍스타-자율-01",
        "avatar_url": "https://i.imgur.com/4E7989q.png",
        "embeds": [{"title": title, "description": description, "color": color}]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        st.toast(f"디스코드 전송 실패: {e}")

# ==========================================
# 6. 채팅 UI 및 핵심 실행 로직
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요 웡빈님! 파이썬 뇌로 완전 이식되었습니다. 왼쪽 사이드바에서 직무를 세팅하고 명령을 내려주세요! 🦞"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("랍스타에게 지시할 내용을 입력하세요..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("랍스타가 뇌를 굴리는 중입니다... 🧠"):
            
            system_prompt = f"""
            너의 이름은 '랍스타-01'. 주인님 이름은 '웡빈'.
            현재 네가 담당하고 있는 직무 파트: {selected_task_name}
            
            [행동 지침]
            1. 일상 대화나 질문이면 자연스럽게 대답하고 [CHAT] 태그 부착.
            2. 구체적인 업무 지시면 [TASK] 태그 부착 후 3단계 계획 작성.
            """
            
            messages_for_groq = [{"role": "system", "content": system_prompt}] + [
                {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
            ]
            
            try:
                # Groq 뇌 가동
                chat_completion = groq_client.chat.completions.create(
                    messages=messages_for_groq,
                    model=selected_groq
                )
                groq_response = chat_completion.choices[0].message.content
                
                # 행동 분기
                if "[CHAT]" in groq_response:
                    clean_reply = groq_response.replace("[CHAT]", "").strip()
                    st.markdown(clean_reply)
                    report_to_discord("💬 랍스타와 대화", clean_reply, 3447003)
                    final_memory_text = clean_reply
                    
                elif "[TASK]" in groq_response:
                    clean_plan = groq_response.replace("[TASK]", "").strip()
                    st.markdown(f"**[업무 계획 수립 완료]**\n{clean_plan}\n\n*(제미나이가 실무 작업을 시작합니다...)*")
                    report_to_discord("🧠 업무 전략 수립", clean_plan, 15105570)
                    
                    # Gemini 손발 가동 (이때 extra_keys 딕셔너리에 담긴 추가 API들을 활용하도록 프롬프트를 확장할 수 있습니다!)
                    model = genai.GenerativeModel(selected_gemini)
                    result = model.generate_content(f"계획:\n{clean_plan}\n\n이 계획을 바탕으로 구체적인 최종 결과물을 작성해.").text
                    
                    st.success("✅ 실무 작업 완료! 디스코드 보고서를 확인하세요.")
                    report_to_discord("✅ 실무 결과물", result[:4000], 3066993)
                    
                    final_memory_text = f"업무 지시를 확인하고 디스코드로 결과를 전송했습니다.\n\n**[세운 계획]**\n{clean_plan}"
                    
                else:
                    st.markdown(groq_response)
                    final_memory_text = groq_response
            
            except Exception as e:
                st.error(f"오류 발생: {e}")
                final_memory_text = "네트워크 오류로 답변을 완료하지 못했습니다."

        st.session_state.messages.append({"role": "assistant", "content": final_memory_text})
