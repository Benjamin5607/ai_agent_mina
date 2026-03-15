import streamlit as st
from api_setup import get_secrets, get_groq_models, get_gemini_models
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center (모듈화 완료)")

# 1. 환경 세팅
secrets = get_secrets()

# 2. 사이드바 UI
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    groq_models = get_groq_models(secrets["GROQ"])
    gemini_models = get_gemini_models(secrets["GEMINI"])
    
    sel_groq = st.selectbox("🧠 사고력 (Groq)", groq_models)
    sel_gemini = st.selectbox("👐 실행력 (Gemini)", gemini_models)
    sel_role = st.selectbox("담당 직무", ["BPO Ops", "Coding", "Data Analysis"])

# 3. 에이전트 소환 (Class 객체 생성)
# 나중에 멀티 에이전트가 되면 여기서 에이전트를 여러 명 소환하면 됩니다!
lobster = LobsterAgent(
    groq_key=secrets["GROQ"], 
    gemini_key=secrets["GEMINI"], 
    name="랍스타-01", 
    role=sel_role
)

# 4. 파일 업로드 UI
uploaded_file = st.file_uploader("📁 분석할 파일을 올려주세요", type=['txt', 'csv', 'md'])
file_data = ""
if uploaded_file:
    file_data = uploaded_file.getvalue().decode("utf-8")
    st.success("파일 로드 완료!")

# 5. 채팅 UI
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "명령을 내려주세요! 🦞"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("메시지 입력..."):
    # 파일이 있으면 프롬프트에 합치기
    full_prompt = prompt if not file_data else f"{prompt}\n\n[첨부 데이터]\n{file_data}"
    
    st.session_state.messages.append({"role": "user", "content": prompt}) # 화면용 (파일내용 숨김)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("랍스타가 생각 중입니다... 🧠"):
            
            # 여기서 에이전트에게 뇌 활동 지시!
            # 주의: 에이전트에게 과거 기억을 넘길 때 파일 데이터가 묻은 full_prompt를 마지막에 넣어줍니다.
            history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
            
            action_type, text1, text2 = lobster.think_and_act(
                user_message=full_prompt,
                chat_history=history_for_agent,
                groq_model=sel_groq,
                gemini_model=sel_gemini
            )
            
            if action_type == "chat":
                st.markdown(text1)
                report_to_discord(secrets["DISCORD"], "💬 대화", text1, 3447003)
                final_memory = text1
                
            elif action_type == "task":
                st.markdown(f"**[계획 수립]**\n{text1}\n\n*(실무 작업 완료!)*")
                st.success("✅ 디스코드 보고서를 확인하세요.")
                
                report_to_discord(secrets["DISCORD"], "🧠 계획", text1, 15105570)
                report_to_discord(secrets["DISCORD"], "✅ 결과", text2[:4000], 3066993)
                
                final_memory = f"[업무 수행 완료] 계획:\n{text1}"

        st.session_state.messages.append({"role": "assistant", "content": final_memory})
