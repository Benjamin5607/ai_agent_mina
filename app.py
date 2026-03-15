import streamlit as st
import json
import os
import time  # 📌 20초 쿨타임을 위한 시간 모듈 추가!
from api_setup import get_secrets, get_groq_models, get_gemini_models
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center (무한 끝장 토론 모드)")

# ==========================================
# 1. 환경 세팅 및 비밀열쇠 로드
# ==========================================
secrets = get_secrets()

def get_model_desc(model_name):
    m = model_name.lower()
    if "70b" in m: return "🧠 [압도적 지능] 복잡한 논리 추론 및 프로젝트 리드"
    if "8b" in m: return "⚡ [보조 두뇌] 가볍고 빠름, 단순 리서치"
    if "mixtral" in m: return "🎨 [창의력 대장] 유연한 사고와 브레인스토밍"
    if "gemma" in m: return "📝 [서기/정리] 구글 경량 모델, 텍스트 정리"
    if "pro" in m: return "💎 [고급 실무] 방대한 문서 분석 및 고품질 작업"
    if "flash" in m: return "⚡ [가속 실무] 초고속 실무 처리"
    return "💡 일반 범용 모델"

AVAILABLE_TOOLS = [
    "📝 Notion API (문서 작성 및 관리)",
    "🐙 GitHub API (코드 푸시 및 PR 리뷰)",
    "💬 Slack API (팀 메신저 알림)",
    "📊 Google Sheets API (데이터 기록 및 분석)",
    "🌐 Web Crawler (웹 검색 및 정보 스크래핑)",
    "🎨 Pixabay API (이미지 소스 검색)"
]

# ==========================================
# 2. 직원 명부(DB) 영구 저장/불러오기
# ==========================================
ROSTER_FILE = "agents_roster.json"

def load_roster():
    if os.path.exists(ROSTER_FILE):
        try:
            with open(ROSTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            roster = {}
            for key, info in data.items():
                agent = LobsterAgent(
                    groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], 
                    name=info["name"], role=info["role"]
                )
                agent.model_groq = info.get("model_groq", "llama-3.3-70b-versatile")
                agent.model_gemini = info.get("model_gemini", "models/gemini-1.5-flash")
                agent.tools = info.get("tools", [])
                roster[key] = agent
            return roster
        except Exception as e:
            st.error(f"직원 명부 로드 실패: {e}")
    return {}

def save_roster(roster):
    data = {}
    for key, agent in roster.items():
        data[key] = {
            "name": agent.name,
            "role": agent.role,
            "model_groq": getattr(agent, "model_groq", "llama-3.3-70b-versatile"),
            "model_gemini": getattr(agent, "model_gemini", "models/gemini-1.5-flash"),
            "tools": getattr(agent, "tools", [])
        }
    with open(ROSTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "agent_roster" not in st.session_state:
    saved_roster = load_roster()
    if not saved_roster:
        default_agent = LobsterAgent(
            groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], name="랍스타-01", role="만능 비서"
        )
        default_agent.model_groq = "llama-3.3-70b-versatile"
        default_agent.model_gemini = "models/gemini-1.5-flash"
        default_agent.tools = ["🌐 Web Crawler (웹 검색 및 정보 스크래핑)"]
        saved_roster["랍스타-01 (만능 비서)"] = default_agent
        save_roster(saved_roster)
    st.session_state.agent_roster = saved_roster

# ==========================================
# 3. 사이드바 (채용소 및 무기고)
# ==========================================
with st.sidebar:
    st.header("🦞 군단 인력소")
    groq_models = get_groq_models(secrets["GROQ"])
    gemini_models = get_gemini_models(secrets["GEMINI"])
    
    with st.expander("➕ 새 에이전트 채용 (무기 지급)"):
        new_name = st.text_input("이름 (예: 제이콥)")
        new_role = st.text_input("직무 (예: 프로젝트 매니저)")
        st.divider()
        sel_groq = st.selectbox("🧠 사고력 뇌 (Groq)", groq_models)
        st.info(get_model_desc(sel_groq))
        sel_gemini = st.selectbox("👐 실무용 손발 (Gemini)", gemini_models)
        st.info(get_model_desc(sel_gemini))
        st.divider()
        selected_tools = st.multiselect("툴 장착", AVAILABLE_TOOLS)
        
        if st.button("채용 및 명부 등록 🚀"):
            if new_name and new_role:
                new_agent = LobsterAgent(
                    groq_key=secrets["GROQ"], gemini_key=secrets["GEMINI"], name=new_name, role=new_role
                )
                new_agent.model_groq = sel_groq
                new_agent.model_gemini = sel_gemini
                new_agent.tools = selected_tools
                
                dict_key = f"{new_name} ({new_role})"
                st.session_state.agent_roster[dict_key] = new_agent
                save_roster(st.session_state.agent_roster)
                st.success(f"🎉 '{new_name}' 채용 및 저장 완료!")
                st.rerun()
            else:
                st.warning("이름과 직무를 모두 입력해주세요!")

# ==========================================
# 4. 메인 화면: 탭 분리
# ==========================================
tab1, tab2 = st.tabs(["🗣️ 1:1 전담 마크", "🔥 원탁 회의실 (끝장 토론)"])

# ------------------------------------------
# [탭 1] 1:1 채팅 UI (기존과 동일)
# ------------------------------------------
with tab1:
    st.subheader("현재 대화 채널")
    colA, colB = st.columns([4, 1])
    with colA:
        selected_agent_key = st.selectbox("누구에게 지시할까요?", list(st.session_state.agent_roster.keys()), key="1on1_select", label_visibility="collapsed")
        active_lobster = st.session_state.agent_roster[selected_agent_key]
    with colB:
        if len(st.session_state.agent_roster) > 1:
            if st.button("🗑️ 해고하기", use_container_width=True):
                del st.session_state.agent_roster[selected_agent_key]
                save_roster(st.session_state.agent_roster)
                st.success("해고 처리되었습니다.")
                st.rerun()
        else:
            st.button("🗑️ 해고 불가", disabled=True, use_container_width=True)

    st.caption(f"🤖 **스펙** | 🧠 뇌: `{active_lobster.model_groq}` / 👐 손발: `{active_lobster.model_gemini}`")
    tools_str = ", ".join(active_lobster.tools) if hasattr(active_lobster, 'tools') and active_lobster.tools else "맨손 (툴 없음)"
    st.caption(f"🛠️ **장착 무기** | {tools_str}")

    uploaded_file = st.file_uploader(f"📁 {active_lobster.name}에게 데이터 전달", type=['txt', 'csv', 'md'], key="1on1_file")
    file_data = ""
    if uploaded_file:
        file_data = uploaded_file.getvalue().decode("utf-8")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "명령을 내려주세요! 🦞"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"[{active_lobster.name}]에게 지시하기...", key="chat_1on1"):
        full_prompt = prompt if not file_data else f"{prompt}\n\n[첨부 데이터:\n{file_data}\n]"
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"{active_lobster.name}가 뇌({active_lobster.model_groq})와 무기를 굴리는 중... 🧠"):
                history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                system_injection = f"\n[현재 장착 중인 API 툴: {tools_str}]\n너는 이 툴들을 사용하여 업무를 자동화할 수 있는 권한이 있다. 계획을 세울 때 네가 가진 툴을 적극적으로 활용해서 세워라."
                
                try:
                    action_type, text1, text2 = active_lobster.think_and_act(
                        full_prompt + system_injection, history_for_agent, active_lobster.model_groq, active_lobster.model_gemini
                    )
                    if action_type == "chat":
                        st.markdown(text1)
                        report_to_discord(secrets["DISCORD"], f"💬 {active_lobster.name}의 대답", text1, 3447003)
                        final_memory = text1
                    elif action_type == "task":
                        st.markdown(f"**[계획 수립 및 툴 활용]**\n{text1}")
                        report_to_discord(secrets["DISCORD"], f"🧠 {active_lobster.name} 기획", text1, 15105570)
                        report_to_discord(secrets["DISCORD"], f"✅ {active_lobster.name} 결과", text2[:4000], 3066993)
                        st.success("✅ 실무 작업 완료! 디스코드 확인.")
                        final_memory = f"업무 지시 완료.\n\n**[계획]**\n{text1}"
                except Exception as e:
                    st.error(f"오류: {e}")
                    final_memory = "오류 발생."
            st.session_state.messages.append({"role": "assistant", "content": final_memory})

# ------------------------------------------
# [탭 2] 🔥 원탁 회의실 (20초 쿨타임 & 무한 루프)
# ------------------------------------------
with tab2:
    st.subheader("토론 참석자 및 룰 세팅")
    
    # 여기서 위젯 키는 "meeting_attendees_widget"으로 씁니다!
    attendees_keys = st.multiselect(
        "회의에 참석할 에이전트들을 호출하세요 (최소 2명 이상)", 
        list(st.session_state.agent_roster.keys()),
        key="meeting_attendees_widget" 
    )
    
    st.divider()

    if "is_debating" not in st.session_state:
        st.session_state.is_debating = False

    col_start, col_stop = st.columns([3, 1])
    
    with col_start:
        if not st.session_state.is_debating:
            agenda_input = st.text_input("회의 안건 던지기...", key="agenda_input")
            if st.button("🔥 무제한 끝장 토론 시작!", use_container_width=True):
                if len(attendees_keys) < 2:
                    st.warning("토론을 하려면 참석자가 최소 2명은 있어야 합니다!")
                elif not agenda_input:
                    st.warning("회의 안건을 입력해주세요!")
                else:
                    st.session_state.is_debating = True
                    st.session_state.meeting_agenda = agenda_input
                    # 📌 에러 원인 해결! 위젯 키랑 안 겹치게 "active_attendees"라는 새 변수통에 담습니다.
                    st.session_state.active_attendees = attendees_keys 
                    st.session_state.turn_index = 0
                    
                    st.session_state.meeting_history = [
                        {"role": "user", "content": f"우리 CEO 웡빈님이 다음 안건을 던지셨어: '{agenda_input}'\n너의 직무에 맞게 전문적인 의견을 내고 비판해. 만약 충분히 논의되었고 팀 전체의 최종 결론이 도출되었다면 답변 가장 마지막에 반드시 '[결론]' 이라는 단어를 적어줘. 그러면 회의가 종료될 거야."}
                    ]
                    st.session_state.full_meeting_log = f"**[회의 안건]** {agenda_input}\n\n"
                    st.rerun()

    with col_stop:
        if st.session_state.is_debating:
            if st.button("🛑 토론 강제 중지", type="primary", use_container_width=True):
                st.session_state.is_debating = False
                st.success("CEO 권한으로 토론이 강제 중지되었습니다.")
                report_to_discord(secrets["DISCORD"], f"🛑 그룹 회의 강제 중지", st.session_state.full_meeting_log[:4000], 15158332)
                st.rerun()

    st.divider()

    if "meeting_history" in st.session_state and len(st.session_state.meeting_history) > 1:
        for msg in st.session_state.meeting_history[1:]:
            with st.chat_message("assistant" if "발언" in msg["content"] else "user"):
                st.markdown(msg["content"].replace("[결론]", ""))

    if st.session_state.is_debating:
        # 📌 저장해둔 새로운 변수(active_attendees)를 불러옵니다!
        attendees = st.session_state.active_attendees 
        current_key = attendees[st.session_state.turn_index % len(attendees)]
        current_agent = st.session_state.agent_roster[current_key]
        
        if st.session_state.turn_index > 0:
            timer_placeholder = st.empty()
            for sec in range(20, 0, -1):
                timer_placeholder.info(f"⏳ Groq API 차단 방어 중... {current_agent.name} 발언까지 **{sec}초** 대기")
                time.sleep(1)
            timer_placeholder.empty()

        with st.chat_message("assistant"):
            with st.spinner(f"🎤 {current_agent.name}가 [{current_agent.model_groq}] 뇌를 가동 중입니다..."):
                try:
                    action, reply, _ = current_agent.think_and_act(
                        "위 안건과 지금까지의 회의록을 바탕으로 너의 차례니 발언해봐. 결론이 났다면 마지막에 [결론]을 적어.",
                        st.session_state.meeting_history, 
                        current_agent.model_groq, 
                        current_agent.model_gemini
                    )
                    
                    st.markdown(f"**{current_agent.name} ({current_agent.role})**\n{reply}")
                    
                    st.session_state.meeting_history.append({"role": "assistant", "content": f"[{current_agent.name}의 발언]: {reply}"})
                    st.session_state.full_meeting_log += f"**[{current_agent.name}]**\n{reply}\n\n"
                    
                    if "[결론]" in reply:
                        st.session_state.is_debating = False
                        st.success("✅ 에이전트들이 합의에 도달하여 토론이 자동 종료되었습니다! (디스코드 전송 완료)")
                        report_to_discord(secrets["DISCORD"], f"🔥 그룹 회의 완료: {st.session_state.meeting_agenda[:20]}...", st.session_state.full_meeting_log[:4000], 15158332)
                    else:
                        st.session_state.turn_index += 1
                    
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"{current_agent.name} 발언 중 에러: {e}")
                    st.session_state.is_debating = False
                    st.button("다시 시도")
