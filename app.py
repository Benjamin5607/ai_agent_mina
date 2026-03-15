import streamlit as st
from api_setup import get_secrets, get_groq_models, get_gemini_models
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center (멀티 에이전트 군단)")

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
            groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], name="랍스타-01", role="만능 비서"
        )
    }

# ==========================================
# 3. 사이드바 (에이전트 채용소)
# ==========================================
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    groq_models = get_groq_models(secrets["GROQ"])
    gemini_models = get_gemini_models(secrets["GEMINI"])
    sel_groq = st.selectbox("🧠 사고력 (Groq)", groq_models)
    sel_gemini = st.selectbox("👐 실행력 (Gemini)", gemini_models)
    
    st.divider()
    st.header("🦞 군단 인력소")
    
    with st.expander("➕ 새 에이전트 채용하기"):
        new_name = st.text_input("이름 (예: 스티브)")
        new_role = st.text_input("직무 (예: 시니어 DB 아키텍트)")
        if st.button("채용 확정 🚀"):
            if new_name and new_role:
                new_agent = LobsterAgent(
                    groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], name=new_name, role=new_role
                )
                st.session_state.agent_roster[f"{new_name} ({new_role})"] = new_agent
                st.success(f"🎉 '{new_name}' 채용 완료!")
            else:
                st.warning("이름과 직무를 모두 입력해주세요!")

# ==========================================
# 4. 메인 화면: 탭으로 기능 분리!
# ==========================================
tab1, tab2 = st.tabs(["🗣️ 1:1 전담 마크", "🔥 원탁 회의실 (난장 토론)"])

# ------------------------------------------
# [탭 1] 기존 1:1 채팅 UI
# ------------------------------------------
with tab1:
    st.subheader("현재 대화 채널")
    selected_agent_key = st.selectbox("누구에게 지시할까요?", list(st.session_state.agent_roster.keys()), key="1on1_select")
    active_lobster = st.session_state.agent_roster[selected_agent_key]

    uploaded_file = st.file_uploader("📁 분석할 데이터 업로드", type=['txt', 'csv', 'md'], key="1on1_file")
    file_data = ""
    if uploaded_file:
        file_data = uploaded_file.getvalue().decode("utf-8")
        st.success(f"데이터 로드 완료! {active_lobster.name} 대기 중.")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "1:1 지시를 내려주세요! 🦞"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"[{active_lobster.name}]에게 지시하기...", key="chat_1on1"):
        full_prompt = prompt if not file_data else f"{prompt}\n\n[첨부 데이터:\n{file_data}\n]"
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"{active_lobster.name}가 뇌를 굴리는 중... 🧠"):
                history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                try:
                    action_type, text1, text2 = active_lobster.think_and_act(
                        full_prompt, history_for_agent, sel_groq, sel_gemini
                    )
                    if action_type == "chat":
                        st.markdown(text1)
                        report_to_discord(secrets["DISCORD"], f"💬 {active_lobster.name}의 대답", text1, 3447003)
                        final_memory = text1
                    elif action_type == "task":
                        st.markdown(f"**[계획 수립]**\n{text1}\n\n*(실무 작업 진행 중...)*")
                        report_to_discord(secrets["DISCORD"], f"🧠 {active_lobster.name} 기획", text1, 15105570)
                        report_to_discord(secrets["DISCORD"], f"✅ {active_lobster.name} 결과", text2[:4000], 3066993)
                        st.success("✅ 실무 작업 완료! 디스코드 확인.")
                        final_memory = f"업무 지시 완료.\n\n**[계획]**\n{text1}"
                except Exception as e:
                    st.error(f"오류: {e}")
                    final_memory = "오류 발생."

            st.session_state.messages.append({"role": "assistant", "content": final_memory})

# ------------------------------------------
# [탭 2] 🔥 신규: 에이전트 그룹 회의실
# ------------------------------------------
with tab2:
    st.subheader("토론 참석자 및 룰 세팅")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 회의에 참석할 에이전트 여러 명 고르기!
        attendees_keys = st.multiselect(
            "회의에 참석할 에이전트들을 호출하세요 (최소 2명 이상)", 
            list(st.session_state.agent_roster.keys()),
            key="meeting_attendees"
        )
    with col2:
        # 몇 번이나 티키타카 할지 턴 수 정하기
        meeting_turns = st.slider("토론 턴 수 (발언 횟수)", min_value=2, max_value=10, value=3)

    st.divider()
    
    # 회의록을 화면에 즉시 그려줄 빈 공간 마련
    meeting_board = st.container()

    # 회의 안건 입력!
    if agenda := st.chat_input("회의 안건 (예: Bean Atlas 커피 농장 리뷰 앱 글로벌 마케팅 전략 토론해봐)", key="chat_meeting"):
        
        if len(attendees_keys) < 2:
            st.warning("토론을 하려면 참석자가 최소 2명은 있어야 합니다! 위에서 에이전트를 더 골라주세요.")
        else:
            with meeting_board:
                st.chat_message("user").markdown(f"**[CEO 웡빈의 안건 발제]**\n{agenda}")
                
                # 에이전트들이 서로의 말을 듣기 위한 '공용 회의록(History)'
                meeting_history = [
                    {"role": "user", "content": f"우리 CEO 웡빈님이 다음 안건을 던지셨어: '{agenda}'\n너의 직무에 맞게 전문적인 의견을 내고, 앞사람이 한 말이 있다면 비판하거나 덧붙여줘."}
                ]
                
                full_meeting_log = f"**[회의 안건]** {agenda}\n\n"
                
                # 정해진 턴(Turn) 수만큼 빙글빙글 돌면서 발언권 넘기기
                for i in range(meeting_turns):
                    current_key = attendees_keys[i % len(attendees_keys)] # 순서대로 발언권 배분
                    current_agent = st.session_state.agent_roster[current_key]
                    
                    with st.chat_message("assistant"):
                        with st.spinner(f"🎤 {current_agent.name}({current_agent.role})가 발언을 준비 중입니다..."):
                            
                            # 해당 에이전트의 뇌를 가동 (앞선 회의록 전체를 읽게 함)
                            try:
                                action, reply, _ = current_agent.think_and_act(
                                    user_message="위 안건과 지금까지의 회의록을 바탕으로 너의 차례니 발언해봐.",
                                    chat_history=meeting_history,
                                    groq_model=sel_groq,
                                    gemini_model=sel_gemini
                                )
                                
                                # 화면에 출력
                                st.markdown(f"**{current_agent.name} ({current_agent.role})**\n{reply}")
                                
                                # 회의록에 추가해서 다음 사람이 읽을 수 있게 함
                                meeting_history.append({"role": "assistant", "content": f"[{current_agent.name}의 발언]: {reply}"})
                                full_meeting_log += f"**[{current_agent.name}]**\n{reply}\n\n"
                                
                            except Exception as e:
                                st.error(f"{current_agent.name} 발언 중 에러: {e}")

                st.success("✅ 토론이 종료되었습니다! 전체 회의록이 디스코드로 전송되었습니다.")
                report_to_discord(secrets["DISCORD"], f"🔥 그룹 회의 종료: {agenda[:20]}...", full_meeting_log[:4000], 15158332)
