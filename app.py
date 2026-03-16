import streamlit as st
import json
import os
import time
import google.generativeai as genai
# 📌 변경됨: get_notion_databases 임포트 추가!
from api_setup import get_secrets, get_groq_models, get_gemini_models, get_notion_databases
from discord_bot import report_to_discord
from agent import LobsterAgent

st.set_page_config(page_title="Lobster Chat Center", page_icon="🦞", layout="wide")

secrets = get_secrets()
groq_models = get_groq_models(secrets["GROQ"])
gemini_models = get_gemini_models(secrets["GEMINI"])
default_groq = groq_models[0] if groq_models else "llama3-8b-8192"
default_gemini = gemini_models[0] if gemini_models else "gemini-pro"

AVAILABLE_TOOLS = [
    "📝 Notion API", "🐙 GitHub API", "💬 Slack API", 
    "📊 Google Sheets API", "🌐 Web Crawler", "🎨 Pixabay API"
]

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
                agent.model_groq = info.get("model_groq", default_groq)
                agent.model_gemini = info.get("model_gemini", default_gemini)
                agent.tools = info.get("tools", [])
                agent.notion_db_id = info.get("notion_db_id", None) # 📌 파일에서 불러올 때 DB ID도 복구!
                roster[key] = agent
            return roster
        except: pass
    return {}

def save_roster(roster):
    data = {}
    for key, agent in roster.items():
        data[key] = {
            "name": agent.name, "role": agent.role,
            "model_groq": getattr(agent, "model_groq", default_groq),
            "model_gemini": getattr(agent, "model_gemini", default_gemini),
            "tools": getattr(agent, "tools", []),
            "notion_db_id": getattr(agent, "notion_db_id", None) # 📌 파일에 DB ID 저장!
        }
    with open(ROSTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "agent_roster" not in st.session_state:
    saved_roster = load_roster()
    if not saved_roster:
        default_agent = LobsterAgent(secrets["GROQ"], secrets["GEMINI"], "랍스타-01", "만능 비서")
        default_agent.model_groq = default_groq
        default_agent.model_gemini = default_gemini
        saved_roster["랍스타-01 (만능 비서)"] = default_agent
        save_roster(saved_roster)
    st.session_state.agent_roster = saved_roster

with st.sidebar:
    st.header("🌐 Language / 공용어 설정")
    app_lang = st.radio("UI & Agent Language", ["한국어", "English"], horizontal=True, label_visibility="collapsed")

def t(ko, en): return ko if app_lang == "한국어" else en

st.title(t("🦞 랍스타 컨트롤 센터 (아포칼립스 군단)", "🦞 Lobster Chat Center (Apocalypse Legion)"))

# ==========================================
# 3. 사이드바 (요원 채용 및 노션 DB 선택 UI)
# ==========================================
with st.sidebar:
    st.divider()
    st.header(t("📝 서기 설정", "📝 Secretary Settings"))
    secretary_model = st.selectbox(t("최종 보고서 작성 모델 (Gemini)", "Final Report Model (Gemini)"), gemini_models)
    
    st.divider()
    st.header(t("🦞 군단 인력소", "🦞 Agent Recruitment"))
    
    with st.expander(t("➕ 새 에이전트 채용 (무기 지급)", "➕ Hire New Agent (Assign Tools)")):
        new_name = st.text_input(t("이름", "Name (e.g., Jacob)"))
        new_role = st.text_input(t("직무", "Role (e.g., Project Manager)"))
        sel_groq = st.selectbox(t("🧠 사고력 뇌 (Groq)", "🧠 Brain (Groq)"), groq_models)
        sel_gemini = st.selectbox(t("👐 실무용 손발 (Gemini)", "👐 Hands (Gemini)"), gemini_models)
        selected_tools = st.multiselect(t("🛠️ 툴 장착", "🛠️ Assign Tools"), AVAILABLE_TOOLS)
        
        # 📌 핵심: 노션 API를 선택하면 DB 선택창이 스르륵 뜹니다!
        selected_notion_db_id = None
        if "📝 Notion API" in selected_tools:
            notion_dbs = get_notion_databases(st.secrets.get("NOTION_API_KEY", ""))
            if notion_dbs:
                selected_db_name = st.selectbox(t("📂 담당할 노션 DB 선택", "📂 Select Notion DB"), list(notion_dbs.keys()))
                selected_notion_db_id = notion_dbs[selected_db_name] # 선택한 제목 뒤에 숨겨진 ID 값을 가져옴
            else:
                st.warning(t("⚠️ 봇이 초대된 노션 DB가 없습니다. 먼저 노션 페이지 연결 메뉴에서 봇을 초대하세요.", "⚠️ No Notion DB found. Invite the bot in Notion first."))
        
        if st.button(t("채용 및 명부 등록 🚀", "Hire & Save 🚀")):
            if new_name and new_role:
                new_agent = LobsterAgent(secrets["GROQ"], secrets["GEMINI"], new_name, new_role)
                new_agent.model_groq = sel_groq
                new_agent.model_gemini = sel_gemini
                new_agent.tools = selected_tools
                new_agent.notion_db_id = selected_notion_db_id # 📌 에이전트에게 DB 아이디 이식!
                
                st.session_state.agent_roster[f"{new_name} ({new_role})"] = new_agent
                save_roster(st.session_state.agent_roster)
                st.success(t(f"🎉 '{new_name}' 채용 완료!", f"🎉 '{new_name}' Hired!"))
                time.sleep(1)
                st.rerun()

# ==========================================
# 4. 메인 화면: 탭 분리 (기존과 동일하므로 전체 복붙)
# ==========================================
tab1_name = t("💬 1:1 개인 업무 지시 (DM)", "💬 1:1 Direct Messages (DM)")
tab2_name = t("🔥 원탁 회의실 (끝장 토론)", "🔥 War Room (Endless Debate)")
tab1, tab2 = st.tabs([tab1_name, tab2_name])

with tab1:
    contact_col, chat_col = st.columns([1, 3])
    with contact_col:
        st.subheader(t("👥 내 요원 목록", "👥 My Agents"))
        selected_agent_key = st.radio(t("업무를 지시할 요원 선택", "Select agent to assign task"), list(st.session_state.agent_roster.keys()), label_visibility="collapsed")
        active_lobster = st.session_state.agent_roster[selected_agent_key]
        
        st.divider()
        st.caption(t(f"🧠 장착 뇌:\n`{active_lobster.model_groq}`", f"🧠 Brain:\n`{active_lobster.model_groq}`"))
        tools_str = ", ".join(active_lobster.tools) if hasattr(active_lobster, 'tools') and active_lobster.tools else t("맨손 (툴 없음)", "No Tools")
        st.caption(t(f"🛠️ 장착 툴:\n{tools_str}", f"🛠️ Tools:\n{tools_str}"))
        
        if len(st.session_state.agent_roster) > 1:
            if st.button(t("🗑️ 요원 해고", "🗑️ Fire Agent"), use_container_width=True):
                del st.session_state.agent_roster[selected_agent_key]
                save_roster(st.session_state.agent_roster)
                st.rerun()

    with chat_col:
        st.subheader(f"💬 {active_lobster.name} {t('요원과의 1:1 DM', 'Direct Message')}")
        chat_memory_key = f"dm_history_{selected_agent_key}"
        if chat_memory_key not in st.session_state:
            st.session_state[chat_memory_key] = [{"role": "assistant", "content": t(f"충성! 사령관님. {active_lobster.role} 담당 {active_lobster.name} 대기 중입니다. 지시를 내려주십시오! 🫡", f"Yes, Commander! {active_lobster.name} ({active_lobster.role}) awaiting orders! 🫡")}]

        uploaded_file = st.file_uploader(t(f"📁 분석할 데이터 전달", f"📁 Upload File for {active_lobster.name}"), type=['txt', 'csv', 'md'], key=f"file_{selected_agent_key}")
        file_data = uploaded_file.getvalue().decode("utf-8") if uploaded_file else ""

        for msg in st.session_state[chat_memory_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input(t(f"[{active_lobster.name}]에게 지시하기...", f"Command [{active_lobster.name}]..."), key=f"input_{selected_agent_key}"):
            full_prompt = prompt if not file_data else f"{prompt}\n\n[Data:\n{file_data}\n]"
            st.session_state[chat_memory_key].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner(t("뇌와 무기를 굴리는 중... 🧠🛠️", "Thinking & Executing... 🧠🛠️")):
                    history_for_agent = [{"role": m["role"], "content": m["content"]} for m in st.session_state[chat_memory_key][-10:]]
                    system_injection = f"\n[Tools: {tools_str}]\n[Rule] All your responses must be strictly in '{app_lang}'."
                    try:
                        action_type, text1, text2 = active_lobster.think_and_act(full_prompt + system_injection, history_for_agent, active_lobster.model_groq, active_lobster.model_gemini)
                        st.markdown(text1)
                        if action_type == "task": st.success(t("✅ 실무 작업 완료 (API 연동)!", "✅ Task Executed (API Used)!"))
                        final_memory = text1
                    except Exception as e:
                        final_memory = f"Error: {e}"
                st.session_state[chat_memory_key].append({"role": "assistant", "content": final_memory})

with tab2:
    st.subheader(t("토론 참석자 세팅", "Select Attendees"))
    attendees_keys = st.multiselect(t("회의에 참석할 에이전트들을 호출하세요", "Call agents to the meeting"), list(st.session_state.agent_roster.keys()), key="meeting_attendees_widget", label_visibility="collapsed")
    st.divider()

    if "is_debating" not in st.session_state: st.session_state.is_debating = False

    col_start, col_stop = st.columns([3, 1])
    with col_start:
        if not st.session_state.is_debating:
            agenda_input = st.text_input(t("회의 안건 던지기...", "Agenda..."), key="agenda_input")
            if st.button(t("🔥 아포칼립스 끝장 토론 시작!", "🔥 Start Apocalypse Debate!"), use_container_width=True):
                if len(attendees_keys) < 2: st.warning(t("참석자가 최소 2명은 있어야 합니다!", "Need at least 2 attendees!"))
                elif not agenda_input: st.warning(t("안건을 입력해주세요!", "Please enter an agenda!"))
                else:
                    st.session_state.is_debating = True
                    st.session_state.meeting_agenda = agenda_input
                    st.session_state.active_attendees = attendees_keys 
                    st.session_state.turn_index = 0
                    st.session_state.compressed_memory = "" 
                    st.session_state.short_term_memory = [] 
                    
                    apoc_kr = f"웡빈 사령관의 안건: '{agenda_input}'\n[규칙]\n1. 무조건 '{app_lang}'로만 말해라.\n2. 5문장 이내로 핵심만 찔러라.\n3. 앞사람 의견을 비판하고 극단적 아이디어를 내라.\n4. 완벽한 계획이 섰을 때만 마지막에 [결론]을 적어라.\n5. [TASK] 태그 사용 금지."
                    apoc_en = f"Commander Wongbin's Agenda: '{agenda_input}'\n[Rules]\n1. Speak ONLY in '{app_lang}'.\n2. Keep it under 5 sentences. Get straight to the point.\n3. Criticize the previous speaker and provide extreme ideas.\n4. Append [결론] at the very end ONLY when a perfect master plan is reached.\n5. NEVER use the [TASK] tag."
                    
                    st.session_state.meeting_history_ui = [{"role": "user", "content": t(apoc_kr, apoc_en)}]
                    st.session_state.full_meeting_log = f"**[Agenda]** {agenda_input}\n\n"
                    st.rerun()

    with col_stop:
        if st.session_state.is_debating:
            if st.button(t("🛑 강제 중지", "🛑 Stop Debate"), type="primary", use_container_width=True):
                st.session_state.is_debating = False
                st.rerun()

    st.divider()

    if "meeting_history_ui" in st.session_state and len(st.session_state.meeting_history_ui) > 1:
        for msg in st.session_state.meeting_history_ui[1:]:
            with st.chat_message("assistant" if "발언" in msg["content"] or "Speaker" in msg["content"] else "user"):
                st.markdown(msg["content"].replace("[결론]", ""))

    if st.session_state.is_debating:
        attendees = st.session_state.active_attendees 
        current_key = attendees[st.session_state.turn_index % len(attendees)]
        current_agent = st.session_state.agent_roster[current_key]
        
        if st.session_state.turn_index > 0:
            timer_ph = st.empty()
            for sec in range(20, 0, -1):
                timer_ph.info(t(f"⏳ 과열 방지 중... {current_agent.name} 발언까지 **{sec}초** 대기", f"⏳ Cooling down... {current_agent.name} speaks in **{sec}s**"))
                time.sleep(1)
            timer_ph.empty()

        with st.chat_message("assistant"):
            if len(st.session_state.short_term_memory) > 4:
                old1 = st.session_state.short_term_memory.pop(0)
                old2 = st.session_state.short_term_memory.pop(0)
                with st.spinner(t("🧠 과거 기억 압축 중...", "🧠 Compressing memories...")):
                    try:
                        genai.configure(api_key=secrets["GEMINI"])
                        model = genai.GenerativeModel(current_agent.model_gemini)
                        st.session_state.compressed_memory = model.generate_content(
                            f"Summarize this in '{app_lang}' into 3 sentences. Previous: {st.session_state.compressed_memory}. New: {old1['content']} \n {old2['content']}"
                        ).text
                    except: pass

            groq_context = [{"role": "user", "content": st.session_state.meeting_history_ui[0]["content"]}]
            if st.session_state.compressed_memory:
                groq_context.append({"role": "user", "content": f"[Memory]\n{st.session_state.compressed_memory}"})
            groq_context.extend(st.session_state.short_term_memory)

            with st.spinner(t(f"🎤 {current_agent.name} 발언 준비 중...", f"🎤 {current_agent.name} is thinking...")):
                try:
                    action, reply, _ = current_agent.think_and_act(
                        t(f"너의 차례다. '{app_lang}'로 5문장 이내로 말해. 결론이 났다면 [결론]을 적어.", f"Your turn. Speak in '{app_lang}' under 5 sentences. If concluded, append [결론]."),
                        groq_context, current_agent.model_groq, current_agent.model_gemini
                    )
                    
                    if "[결론]" in reply and st.session_state.turn_index < len(attendees) * 2:
                        reply = reply.replace("[결론]", t(f"\n\n**(사령관: \"장난해? 더 파고들어!\")**", f"\n\n**(Commander: \"Not enough! Dig deeper!\")**"))
                    
                    st.markdown(f"**{current_agent.name} ({current_agent.role})**\n{reply}")
                    
                    log_entry = {"role": "assistant", "content": f"[{current_agent.name}]: {reply}"}
                    st.session_state.meeting_history_ui.append(log_entry)
                    st.session_state.short_term_memory.append(log_entry)
                    st.session_state.full_meeting_log += f"**[{current_agent.name}]**\n{reply}\n\n"
                    
                    if "[결론]" in reply:
                        st.session_state.is_debating = False
                        st.success(t("✅ 합의 도달! 최종 보고서를 작성합니다...", "✅ Agreement Reached! Generating Final Report..."))
                        
                        with st.spinner(t("서기(Gemini)가 액션 아이템을 정리 중입니다... 📝", "Gemini is finalizing Action Items... 📝")):
                            try:
                                genai.configure(api_key=secrets["GEMINI"])
                                summary_model = genai.GenerativeModel(secretary_model)
                                
                                report_prompt = f"""
                                다음은 방금 완료된 회의의 전체 기록이다. 모든 내용을 반드시 '{app_lang}'로 작성해라.
                                [안건]: {st.session_state.meeting_agenda}
                                [전체 회의록]: {st.session_state.full_meeting_log}
                                
                                다음 양식에 맞춰 완벽한 마크다운 형식의 최종 회의 결과 보고서를 작성해:
                                1. 📌 미팅 요약 (Meeting Summary)
                                2. 💡 중요 내용 (Key Takeaways)
                                3. 📅 액션 아이템 (Action Items)
                                4. 🎯 기대 효과 (Expected Results)
                                5. 🤖 각 에이전트별 개인 업무 AI 프롬프트 (Individual AI Prompts)
                                """
                                final_report = summary_model.generate_content(report_prompt).text
                                st.session_state.final_report = final_report
                                report_to_discord(secrets["DISCORD"], "📜 최종 회의 보고서", final_report[:4000], 15158332)
                            except Exception as e:
                                st.session_state.final_report = f"요약 생성 중 에러 발생: {e}"
                        st.rerun()
                    else:
                        st.session_state.turn_index += 1
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.is_debating = False

    if not st.session_state.is_debating and "final_report" in st.session_state:
        st.divider()
        st.subheader(t("📜 제미나이 서기의 최종 회의 보고서", "📜 Final Meeting Report by Gemini"))
        with st.container(border=True):
            st.markdown(st.session_state.final_report)
