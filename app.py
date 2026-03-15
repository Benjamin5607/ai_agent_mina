import streamlit as st
from api_setup import get_secrets, get_groq_models, get_gemini_models
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center (어벤져스 군단)")

# ==========================================
# 1. 환경 세팅 및 비밀열쇠 로드
# ==========================================
secrets = get_secrets()

# 모델 특성 가이드 사전 (UI 표시용)
def get_model_desc(model_name):
    m = model_name.lower()
    if "70b" in m: return "🧠 [압도적 지능] 복잡한 논리 추론 및 프로젝트 리드에 최적"
    if "8b" in m: return "⚡ [보조 두뇌] 가볍고 빠름, 단순 리서치 및 요약에 적합"
    if "mixtral" in m: return "🎨 [창의력 대장] 유연한 사고와 아이디어 브레인스토밍 특화"
    if "gemma" in m: return "📝 [서기/정리] 구글 경량 모델, 깔끔한 텍스트 및 코드 리뷰"
    if "pro" in m: return "💎 [고급 실무] 방대한 문서 분석 및 고품질 코딩/문서 작성"
    if "flash" in m: return "⚡ [가속 실무] 초고속 실무 처리 및 즉각적인 반응"
    return "💡 일반 범용 모델"

# ==========================================
# 2. 에이전트 대기실 (Roster) 초기화
# ==========================================
# 처음 켜질 때 기본으로 제공되는 랍스타 1호
if "agent_roster" not in st.session_state:
    default_agent = LobsterAgent(
        groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], name="랍스타-01", role="만능 비서"
    )
    # 랍스타 1호에게 기본 모델 장착
    default_agent.model_groq = "llama-3.3-70b-versatile"
    default_agent.model_gemini = "models/gemini-1.5-flash"
    
    st.session_state.agent_roster = {"랍스타-01 (만능 비서)": default_agent}

# ==========================================
# 3. 사이드바 (★ 에이전트 맞춤 채용소)
# ==========================================
with st.sidebar:
    st.header("🦞 군단 인력소 (채용/배치)")
    
    # API에서 모델 리스트 가져오기
    groq_models = get_groq_models(secrets["GROQ"])
    gemini_models = get_gemini_models(secrets["GEMINI"])
    
    with st.expander("➕ 새 에이전트 채용 (모델 직접 선택)", expanded=True):
        st.caption("이름, 직무, 그리고 사용할 뇌/손발 모델을 골라주세요.")
        
        # 기본 정보
        new_name = st.text_input("이름 (예: 스티브)")
        new_role = st.text_input("직무 (예: 시니어 DB 아키텍트)")
        
        st.divider()
        
        # 맞춤형 모델 선택
        sel_groq = st.selectbox("🧠 사고력 뇌 (Groq)", groq_models)
        st.info(get_model_desc(sel_groq)) # 선택한 모델 특성 즉시 보여주기
        
        sel_gemini = st.selectbox("👐 실무용 손발 (Gemini)", gemini_models)
        st.info(get_model_desc(sel_gemini))
        
        if st.button("채용 확정 🚀"):
            if new_name and new_role:
                # 1. 뼈대 생성
                new_agent = LobsterAgent(
                    groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], name=new_name, role=new_role
                )
                # 2. 선택한 두뇌와 손발을 에이전트 몸에 이식! (이게 핵심입니다)
                new_agent.model_groq = sel_groq
                new_agent.model_gemini = sel_gemini
                
                # 3. 인력소 대기실에 등록
                st.session_state.agent_roster[f"{new_name} ({new_role})"] = new_agent
                st.success(f"🎉 '{new_name}' 채용 완료! 이제 대화 채널이나 회의실에 초대하세요.")
            else:
                st.warning("이름과 직무를 모두 입력해주세요!")

# ==========================================
# 4. 메인 화면: 탭 분리 (1:1 / 원탁회의)
# ==========================================
tab1, tab2 = st.tabs(["🗣️ 1:1 전담 마크", "🔥 원탁 회의실 (난장 토론)"])

# ------------------------------------------
# [탭 1] 1:1 채팅 UI
# ------------------------------------------
with tab1:
    st.subheader("현재 대화 채널")
    selected_agent_key = st.selectbox("누구에게 지시할까요?", list(st.session_state.agent_roster.keys()), key="1on1_select")
    active_lobster = st.session_state.agent_roster[selected_agent_key]

    # 현재 선택된 에이전트의 스펙(장착된 모델) 보여주기
    st.caption(f"🤖 **장착 스펙** | 🧠 뇌: `{active_lobster.model_groq}` / 👐 손발: `{active_lobster.model_gemini}`")

    uploaded_file = st.file_uploader(f"📁 {active_lobster.name}에게 분석할 데이터 전달", type=['txt', 'csv', 'md'], key="1on1_file")
    file_data = ""
    if uploaded_file:
        file_data = uploaded_file.getvalue().decode("utf-8")
        st.success(f"데이터 전달 완료! {active_lobster.name}가 읽을 준비를 마쳤습니다.")

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
            with st.spinner(f"{active_lobster.name}가 전용 뇌({active_lobster.model_groq})를 굴리는 중... 🧠"):
                history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                try:
                    # 해당 에이전트의 '고유 모델'을 꺼내서 사용합니다!
                    action_type, text1, text2 = active_lobster.think_and_act(
                        full_prompt, history_for_agent, active_lobster.model_groq, active_lobster.model_gemini
                    )
                    if action_type == "chat":
                        st.markdown(text1)
                        report_to_discord(secrets["DISCORD"], f"💬 {active_lobster.name}의 대답", text1, 3447003)
                        final_memory = text1
                    elif action_type == "task":
                        st.markdown(f"**[계획 수립]**\n{text1}\n\n*(전용 손발인 {active_lobster.model_gemini}로 실무 작업 진행 중...)*")
                        report_to_discord(secrets["DISCORD"], f"🧠 {active_lobster.name} 기획", text1, 15105570)
                        report_to_discord(secrets["DISCORD"], f"✅ {active_lobster.name} 결과", text2[:4000], 3066993)
                        st.success("✅ 실무 작업 완료! 디스코드 확인.")
                        final_memory = f"업무 지시 완료.\n\n**[계획]**\n{text1}"
                except Exception as e:
                    st.error(f"오류: {e}")
                    final_memory = "오류 발생."

            st.session_state.messages.append({"role": "assistant", "content": final_memory})

# ------------------------------------------
# [탭 2] 🔥 에이전트 그룹 회의실
# ------------------------------------------
with tab2:
    st.subheader("토론 참석자 및 룰 세팅")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        attendees_keys = st.multiselect(
            "회의에 참석할 에이전트들을 호출하세요 (최소 2명)", 
            list(st.session_state.agent_roster.keys()),
            key="meeting_attendees"
        )
    with col2:
        meeting_turns = st.slider("토론 턴 수 (발언 횟수)", min_value=2, max_value=10, value=3)

    st.divider()
    meeting_board = st.container()

    if agenda := st.chat_input("회의 안건 던지기...", key="chat_meeting"):
        
        if len(attendees_keys) < 2:
            st.warning("토론을 하려면 참석자가 최소 2명은 있어야 합니다!")
        else:
            with meeting_board:
                st.chat_message("user").markdown(f"**[CEO 웡빈의 안건 발제]**\n{agenda}")
                
                meeting_history = [
                    {"role": "user", "content": f"우리 CEO 웡빈님이 다음 안건을 던지셨어: '{agenda}'\n너의 직무에 맞게 전문적인 의견을 내고, 앞사람이 한 말이 있다면 비판하거나 덧붙여줘."}
                ]
                
                full_meeting_log = f"**[회의 안건]** {agenda}\n\n"
                
                for i in range(meeting_turns):
                    current_key = attendees_keys[i % len(attendees_keys)]
                    current_agent = st.session_state.agent_roster[current_key]
                    
                    with st.chat_message("assistant"):
                        # 어떤 뇌를 돌리고 있는지 시각적으로 표시!
                        with st.spinner(f"🎤 {current_agent.name}가 [{current_agent.model_groq}] 뇌를 가동 중입니다..."):
                            try:
                                # 각 에이전트는 자기한테 이식된 전용 뇌만 사용해서 발언합니다!
                                action, reply, _ = current_agent.think_and_act(
                                    user_message="위 안건과 지금까지의 회의록을 바탕으로 너의 차례니 발언해봐.",
                                    chat_history=meeting_history,
                                    groq_model=current_agent.model_groq,
                                    gemini_model=current_agent.model_gemini
                                )
                                
                                st.markdown(f"**{current_agent.name} ({current_agent.role})**\n{reply}")
                                meeting_history.append({"role": "assistant", "content": f"[{current_agent.name}의 발언]: {reply}"})
                                full_meeting_log += f"**[{current_agent.name}]**\n{reply}\n\n"
                                
                            except Exception as e:
                                st.error(f"{current_agent.name} 발언 중 에러: {e}")

                st.success("✅ 토론이 종료되었습니다! 전체 회의록이 디스코드로 전송되었습니다.")
                report_to_discord(secrets["DISCORD"], f"🔥 그룹 회의 종료: {agenda[:20]}...", full_meeting_log[:4000], 15158332)
