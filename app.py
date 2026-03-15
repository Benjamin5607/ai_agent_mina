import streamlit as st
from api_setup import get_secrets, get_groq_models, get_gemini_models
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center (멀티 에이전트 인력소)")

# ==========================================
# 1. 환경 세팅 및 비밀열쇠 로드
# ==========================================
secrets = get_secrets()

# ==========================================
# 2. 에이전트 대기실 (Roster) 초기화
# ==========================================
if "agent_roster" not in st.session_state:
    st.session_state.agent_roster = {
        "랍스타-01 (만능 비서)": LobsterAgent(
            groq_key=secrets["GROQ"], 
            gemini_key=secrets["GEMINI"], 
            name="랍스타-01", 
            role="만능 비서"
        )
    }

# ==========================================
# 3. 사이드바 (모델 선택 및 에이전트 인력소)
# ==========================================
with st.sidebar:
    st.header("⚙️ 시스템 및 모델 설정")
    groq_models = get_groq_models(secrets["GROQ"])
    gemini_models = get_gemini_models(secrets["GEMINI"])
    
    sel_groq = st.selectbox("🧠 사고력 (Groq)", groq_models)
    sel_gemini = st.selectbox("👐 실행력 (Gemini)", gemini_models)
    
    st.divider()
    st.header("🦞 랍스타 군단 인력소")
    
    # 📌 UI에서 즉석으로 에이전트 생성하기
    with st.expander("➕ 새 에이전트 채용하기"):
        st.caption("새로운 특기를 가진 에이전트를 생성합니다.")
        new_name = st.text_input("이름 (예: 스티브)")
        new_role = st.text_input("직무 (예: 파이썬 시니어 개발자)")
        
        if st.button("채용 확정 🚀"):
            if new_name and new_role:
                new_agent = LobsterAgent(
                    groq_key=secrets["GROQ"], 
                    gemini_key=secrets["GEMINI"], 
                    name=new_name, 
                    role=new_role
                )
                dict_key = f"{new_name} ({new_role})"
                st.session_state.agent_roster[dict_key] = new_agent
                st.success(f"🎉 '{new_name}' 채용 완료!")
            else:
                st.warning("이름과 직무를 모두 입력해주세요!")
                
    # 📌 대화할 에이전트 선택하기
    st.subheader("현재 대화 채널")
    selected_agent_key = st.selectbox(
        "누구에게 지시할까요?", 
        list(st.session_state.agent_roster.keys())
    )
    # 선택한 랍스타 활성화!
    active_lobster = st.session_state.agent_roster[selected_agent_key]

# ==========================================
# 4. 메인 화면: 파일 업로드
# ==========================================
uploaded_file = st.file_uploader("📁 분석할 데이터나 문서를 올려주세요 (txt, csv, md)", type=['txt', 'csv', 'md'])
file_data = ""
if uploaded_file:
    try:
        file_data = uploaded_file.getvalue().decode("utf-8")
        st.success(f"'{uploaded_file.name}' 데이터 로드 완료! {active_lobster.name}가 읽을 준비가 되었습니다.")
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

# ==========================================
# 5. 메인 화면: 채팅 UI
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요 웡빈님! 인력소에서 에이전트를 고르고 명령을 내려주세요! 🦞"}]

# 기존 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 채팅 입력창
if prompt := st.chat_input(f"[{active_lobster.name}]에게 지시할 내용을 입력하세요..."):
    
    # 파일 데이터가 첨부되어 있으면 프롬프트에 몰래 끼워넣음 (UI에는 숨김)
    full_prompt = prompt
    if file_data:
        full_prompt += f"\n\n[웡빈님이 첨부한 파일 데이터:\n{file_data}\n]"
    
    # 내 채팅 화면에 띄우기
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 에이전트 응답 로직
    with st.chat_message("assistant"):
        with st.spinner(f"{active_lobster.name}({active_lobster.role})가 뇌를 굴리는 중입니다... 🧠"):
            
            # 에이전트에게 보낼 과거 기억 조립
            history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
            
            try:
                # 활성화된 에이전트의 메서드 실행!
                action_type, text1, text2 = active_lobster.think_and_act(
                    user_message=full_prompt,
                    chat_history=history_for_agent,
                    groq_model=sel_groq,
                    gemini_model=sel_gemini
                )
                
                # 결과 처리
                if action_type == "chat":
                    st.markdown(text1)
                    report_to_discord(secrets["DISCORD"], f"💬 {active_lobster.name}의 대답", text1, 3447003)
                    final_memory = text1
                    
                elif action_type == "task":
                    st.markdown(f"**[데이터 분석 및 계획 수립 완료 - by {active_lobster.name}]**\n{text1}\n\n*(제미나이가 실무 작업을 시작합니다...)*")
                    
                    report_to_discord(secrets["DISCORD"], f"🧠 {active_lobster.name}의 전략", text1, 15105570)
                    report_to_discord(secrets["DISCORD"], f"✅ {active_lobster.name}의 결과물", text2[:4000], 3066993)
                    
                    st.success(f"✅ 실무 작업 완료! 디스코드 보고서를 확인하세요.")
                    final_memory = f"업무 지시를 확인하고 디스코드로 결과를 전송했습니다.\n\n**[세운 계획]**\n{text1}"
                    
            except Exception as e:
                st.error(f"오류 발생: {e}")
                final_memory = "네트워크 오류로 답변을 완료하지 못했습니다."

        # 대답을 메모리에 저장
        st.session_state.messages.append({"role": "assistant", "content": final_memory})
