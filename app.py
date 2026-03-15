import os
import streamlit as st
import requests
from groq import Groq
import google.generativeai as genai

# ==========================================
# 1. 페이지 세팅 및 UI 디자인
# ==========================================
st.set_page_config(page_title="랍스타 컨트롤 센터", page_icon="🦞", layout="centered")
st.title("🦞 Lobster Chat Center")
st.caption("파이썬(Streamlit)으로 진화한 진짜 실시간 랍스타 에이전트")

# ==========================================
# 2. 시크릿 키(보안) 불러오기
# ==========================================
# Streamlit Cloud의 Secrets에서 키를 안전하게 가져옵니다. (HTML에 노출 안 됨!)
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
except KeyError:
    st.error("🚨 Streamlit Secrets에 API 키가 세팅되지 않았습니다!")
    st.stop()

# 클라이언트 초기화
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 3. 디스코드 웹후크 함수
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
# 4. 메모리(채팅 기록) 초기화
# ==========================================
# 깃허브 파일(memory.json) 저장 꼼수 버림! Streamlit 자체 세션 메모리 사용
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요 웡빈님! 파이썬 뇌로 이식 완료했습니다. 뭘 도와드릴까요? 🦞"}
    ]

# 화면에 기존 대화 내용 쭉 뿌려주기
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 5. 핵심 로직: 채팅 입력 -> 사고 -> 실행
# ==========================================
# 카카오톡 같은 하단 입력창
if prompt := st.chat_input("랍스타에게 지시할 내용을 입력하세요..."):
    
    # 1. 내 메시지 화면에 즉시 출력 및 메모리 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 랍스타의 대답 준비
    with st.chat_message("assistant"):
        # "로딩 중..." 스피너 띄우기 (깃허브 액션 기다릴 필요 없이 여기서 바로 처리!)
        with st.spinner("랍스타가 뇌를 굴리는 중입니다... 🧠"):
            
            system_prompt = """
            너의 이름은 '랍스타-01'. 주인님 이름은 '웡빈'.
            1. 일상 대화면 [CHAT] 태그 부착.
            2. 문서, 데이터, 요약 등 업무 지시면 [TASK] 태그 부착 후 3단계 계획 작성.
            """
            
            # API 호출 (과거 대화 기억 포함)
            messages_for_groq = [{"role": "system", "content": system_prompt}] + [
                {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
            ]
            
            chat_completion = groq_client.chat.completions.create(
                messages=messages_for_groq,
                model="llama-3.3-70b-versatile"
            )
            groq_response = chat_completion.choices[0].message.content
            
            # 3. 행동 분기 처리
            if "[CHAT]" in groq_response:
                clean_reply = groq_response.replace("[CHAT]", "").strip()
                st.markdown(clean_reply) # 화면에 바로 답변! (딜레이 1초 미만)
                report_to_discord("💬 랍스타와 대화", clean_reply, 3447003)
                final_memory_text = clean_reply
                
            elif "[TASK]" in groq_response:
                clean_plan = groq_response.replace("[TASK]", "").strip()
                st.markdown(f"**[업무 계획 수립 완료]**\n{clean_plan}\n\n*(제미나이가 실무 작업을 시작합니다...)*")
                report_to_discord("🧠 업무 전략 수립", clean_plan, 15105570)
                
                # 제미나이 가동
                model = genai.GenerativeModel("gemini-1.5-flash")
                result = model.generate_content(f"계획:\n{clean_plan}\n\n이 계획을 바탕으로 구체적인 최종 결과물을 작성해.").text
                
                st.success("✅ 실무 작업 완료! 디스코드 보고서를 확인하세요.")
                report_to_discord("✅ 실무 결과물", result[:4000], 3066993)
                
                final_memory_text = f"업무 지시를 확인하고 디스코드로 결과를 전송했습니다.\n\n**[세운 계획]**\n{clean_plan}"
                
            else:
                st.markdown(groq_response)
                final_memory_text = groq_response

        # 랍스타의 대답을 메모리에 저장
        st.session_state.messages.append({"role": "assistant", "content": final_memory_text})
