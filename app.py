import streamlit as st
import json
import os
import time
import google.generativeai as genai # 📌 요약(장기기억) 생성을 위한 제미나이 호출용
from api_setup import get_secrets, get_groq_models, get_gemini_models
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="wide")
st.title("🦞 Lobster Chat Center (아포칼립스 군단)")

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
        saved_roster["랍스타-01 (만능 비서)"] = default_agent
        save_roster(saved_roster)
    st.session_state.agent_roster = saved_roster

# ==========================================
# 3. 사이드바 (언어 설정 및 인력소)
# ==========================================
with st.sidebar:
    st.header("🌐 공용어 설정 (Language)")
    app_lang = st.radio("군단 전체 사용 언어", ["한국어", "English"], horizontal=True)
    st.divider()
    
    st.header("🦞 군단 인력소")
    groq_models = get_groq_models(secrets["GROQ"])
    gemini_models = get_gemini_models(secrets["GEMINI"])
    
    with st.expander("➕ 새 에이전트 채용 (무기 지급)"):
        new_name = st.text_input("이름 (예: 제이콥)")
        new_role = st.text_input("직무 (예: 프로젝트 매니저)")
        sel_groq = st.selectbox("🧠 사고력 뇌 (Groq)", groq_models)
        sel_gemini = st.selectbox("👐 실무용 손발 (Gemini)", gemini_models)
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
                st.success(f"🎉 '{new_name}' 채용 완료!")
                st.rerun()

# ==========================================
# 4. 메인 화면: 탭 분리
# ==========================================
tab1, tab2 = st.tabs(["🗣️ 1:1 전담 마크", "🔥 원탁 회의실 (끝장 토론)"])

# ------------------------------------------
# [탭 1] 1:1 채팅 UI
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
                st.rerun()

    tools_str = ", ".join(active_lobster.tools) if hasattr(active_lobster, 'tools') and active_lobster.tools else "맨손 (툴 없음)"
    uploaded_file = st.file_uploader(f"📁 {active_lobster.name}에게 데이터 전달", type=['txt', 'csv', 'md'], key="1on1_file")
    file_data = uploaded_file.getvalue().decode("utf-8") if uploaded_file else ""

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
            with st.spinner(f"{active_lobster.name}가 뇌를 굴리는 중... 🧠"):
                history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-10:]]
                system_injection = f"\n[현재 장착 API 툴: {tools_str}]\n[필수 명령] 너의 모든 대답은 무조건 '{app_lang}'로만 작성해라."
                
                try:
                    action_type, text1, text2 = active_lobster.think_and_act(
                        full_prompt + system_injection, history_for_agent, active_lobster.model_groq, active_lobster.model_gemini
                    )
                    st.markdown(text1)
                    if action_type == "task":
                        st.success("✅ 실무 작업 완료! 디스코드 확인.")
                    final_memory = text1
                except Exception as e:
                    st.error(f"오류: {e}")
                    final_memory = "오류 발생."
            st.session_state.messages.append({"role": "assistant", "content": final_memory})

# ------------------------------------------
# [탭 2] 🔥 원탁 회의실 (장기/단기 기억 압축 모델)
# ------------------------------------------
with tab2:
    st.subheader("토론 참석자 및 룰 세팅")
    
    attendees_keys = st.multiselect(
        "회의에 참석할 에이전트들을 호출하세요", 
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
            if st.button("🔥 아포칼립스 끝장 토론 시작!", use_container_width=True):
                if len(attendees_keys) < 2:
                    st.warning("토론 참석자가 최소 2명은 있어야 합니다!")
                elif not agenda_input:
                    st.warning("안건을 입력해주세요!")
                else:
                    # 📌 토론 초기화 및 메모리 할당
                    st.session_state.is_debating = True
                    st.session_state.meeting_agenda = agenda_input
                    st.session_state.active_attendees = attendees_keys 
                    st.session_state.turn_index = 0
                    
                    st.session_state.compressed_memory = "" # 장기 기억(요약본) 통
                    st.session_state.short_term_memory = [] # 단기 기억(최근 발언 4개) 통
                    
                    apocalypse_prompt = f"""우리 최고 사령관 웡빈님이 인류 운명이 걸린 안건을 던지셨다: '{agenda_input}'

[🔥 방어 프로토콜 - 절대 규칙 🔥]
1. [언어 강제] 모든 대화는 반드시 '{app_lang}'로만 진행한다.
2. [단기 기억 집중] API 호출 한계가 있으므로, 길게 늘어쓰지 말고 핵심만 '5문장 이내'로 짧고 날카롭게 찔러라.
3. 앞사람 말에 동의만 하지 말고 헛점을 물어뜯어라. 불가능하다는 나약한 소리는 금지다.
4. 완벽한 마스터플랜이 도출되었을 때만 마지막에 '[결론]'을 적어라.
5. 답변에 절대 '[TASK]' 라는 단어를 포함하지 마라. 무조건 대화 형식인 '[CHAT]' 태그만 사용해라."""
                    
                    # UI 표시용 전체 회의록 (이건 화면에만 띄우고 API엔 안 보냅니다)
                    st.session_state.meeting_history_ui = [{"role": "user", "content": apocalypse_prompt}]
                    st.session_state.full_meeting_log = f"**[회의 안건]** {agenda_input}\n\n"
                    st.rerun()

    with col_stop:
        if st.session_state.is_debating:
            if st.button("🛑 토론 강제 중지", type="primary", use_container_width=True):
                st.session_state.is_debating = False
                st.success("강제 중지되었습니다.")
                report_to_discord(secrets["DISCORD"], f"🛑 그룹 회의 중지", st.session_state.full_meeting_log[:4000], 15158332)
                st.rerun()

    st.divider()

    # 📌 화면에는 전체 회의록을 모두 그려줍니다. (사용자는 모든 과정을 볼 수 있음)
    if "meeting_history_ui" in st.session_state and len(st.session_state.meeting_history_ui) > 1:
        for msg in st.session_state.meeting_history_ui[1:]:
            with st.chat_message("assistant" if "발언" in msg["content"] else "user"):
                st.markdown(msg["content"].replace("[결론]", ""))

    if st.session_state.is_debating:
        attendees = st.session_state.active_attendees 
        current_key = attendees[st.session_state.turn_index % len(attendees)]
        current_agent = st.session_state.agent_roster[current_key]
        
        # 📌 20초 쿨타임
        if st.session_state.turn_index > 0:
            timer_placeholder = st.empty()
            for sec in range(20, 0, -1):
                timer_placeholder.info(f"⏳ 과열 방지 중... {current_agent.name} 발언까지 **{sec}초** 대기")
                time.sleep(1)
            timer_placeholder.empty()

        with st.chat_message("assistant"):
            
            # 📌 핵심: 단기 기억이 4개가 넘어가면, 오래된 2개를 빼서 '장기 기억(요약)'으로 압축해버립니다!
            if len(st.session_state.short_term_memory) > 4:
                old_msg1 = st.session_state.short_term_memory.pop(0)
                old_msg2 = st.session_state.short_term_memory.pop(0)
                text_to_compress = f"{old_msg1['content']}\n{old_msg2['content']}"
                
                with st.spinner("🧠 이전 대화 내용을 장기 기억으로 압축(요약) 중입니다..."):
                    try:
                        genai.configure(api_key=secrets["GEMINI"])
                        model = genai.GenerativeModel(current_agent.model_gemini)
                        sum_prompt = f"다음 대화 내용을 '{app_lang}'로 핵심만 3~4문장으로 요약해라. 이전 요약이 있다면 자연스럽게 합쳐라.\n[이전 장기 기억 요약]: {st.session_state.compressed_memory}\n[새로 추가된 대화]: {text_to_compress}"
                        st.session_state.compressed_memory = model.generate_content(sum_prompt).text
                    except Exception as e:
                        pass # 압축 실패 시 그냥 넘어감 (API 에러 방어)

            # 📌 뇌로 보내는 최종 컨텍스트 조립
            groq_context = [{"role": "user", "content": st.session_state.meeting_history_ui[0]["content"]}] # 1. 사령관 룰
            if st.session_state.compressed_memory:
                groq_context.append({"role": "user", "content": f"[과거 대화 장기기억 요약본]\n{st.session_state.compressed_memory}"}) # 2. 장기 기억
            groq_context.extend(st.session_state.short_term_memory) # 3. 단기 기억 (가장 최근 발언들)

            with st.spinner(f"🎤 {current_agent.name}가 [{current_agent.model_groq}] 뇌를 쥐어짜는 중입니다..."):
                try:
                    action, reply, _ = current_agent.think_and_act(
                        f"위 안건, 장기기억 요약본, 단기기억을 바탕으로 너의 차례니 발언해. 무조건 '{app_lang}'로 5문장 이내로 짧게 말해라. 결론이 났다면 마지막에 [결론]을 적어.",
                        groq_context, 
                        current_agent.model_groq, 
                        current_agent.model_gemini
                    )
                    
                    min_turns_required = len(attendees) * 2 
                    if "[결론]" in reply and st.session_state.turn_index < min_turns_required:
                        reply = reply.replace("[결론]", f"\n\n**(사령관 웡빈의 호통: \"장난해? 더 파고들어!! 무조건 {app_lang}로 대답해!\")**")
                    
                    st.markdown(f"**{current_agent.name} ({current_agent.role})**\n{reply}")
                    
                    new_log = {"role": "assistant", "content": f"[{current_agent.name}의 발언]: {reply}"}
                    
                    # UI 기록 및 단기 기억에 동시 저장
                    st.session_state.meeting_history_ui.append(new_log)
                    st.session_state.short_term_memory.append(new_log)
                    st.session_state.full_meeting_log += f"**[{current_agent.name}]**\n{reply}\n\n"
                    
                    if "[결론]" in reply:
                        st.session_state.is_debating = False
                        st.success("✅ 합의 도달! (디스코드 전송 완료)")
                        report_to_discord(secrets["DISCORD"], f"🔥 그룹 회의 완료: {st.session_state.meeting_agenda[:20]}...", st.session_state.full_meeting_log[:4000], 15158332)
                    else:
                        st.session_state.turn_index += 1
                    
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"{current_agent.name} 발언 중 에러: {e}")
                    st.session_state.is_debating = False
