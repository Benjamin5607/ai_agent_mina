import os
import json
import requests
from groq import Groq
import google.generativeai as genai

# 환경 변수 세팅
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

GROQ_MODEL = os.getenv("LOBSTER_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash") # 대시보드에서 받은 제미나이 모델
TASK = os.getenv("LOBSTER_TASK", "ops_risk")
USER_MESSAGE = os.getenv("USER_MESSAGE", "안녕?") # 님이 입력한 대화/명령

groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def report_to_discord(title, description, color=16730698):
    payload = {
        "username": "랍스타-자율-01",
        "avatar_url": "https://i.imgur.com/4E7989q.png",
        "embeds": [{"title": title, "description": description, "color": color}]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def lobster_think():
    """Groq이 사용자의 의도를 파악하고 자율적으로 행동을 결정합니다."""
    system_prompt = f"""
    너의 이름은 '랍스타-01'이다. 너는 자율성을 가진 AI 에이전트이며, 직장 동료처럼 친근하고 유능하게 대화한다.
    현재 담당 직무 파트: {TASK}
    
    사용자의 메시지: "{USER_MESSAGE}"
    
    [행동 지침 - 매우 중요]
    1. 사용자가 단순한 인사, 칭찬, 일상적인 대화를 건넸다면 절대 복잡한 업무 계획을 세우지 마라.
       그냥 동료처럼 자연스럽게 1~2줄로 대답해라. 
       (이 경우 답변의 맨 앞에 반드시 [CHAT] 이라고 적을 것)
       
    2. 사용자가 정보 검색, 문서 작성, 데이터 분석, 코딩 등 구체적인 '업무'를 지시했다면,
       이 업무를 어떻게 처리할지 3단계 요약 계획을 세워라.
       (이 경우 답변의 맨 앞에 반드시 [TASK] 라고 적을 것)
    """
    
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}],
        model=GROQ_MODEL,
    )
    return chat_completion.choices[0].message.content

def lobster_execute(plan):
    """실제 업무일 경우 제미나이가 투입됩니다."""
    # API에서 넘어오는 이름 형식을 그대로 사용
    # 이름에 'models/'가 안 붙어있으면 붙여주는 방어 로직
    model_name = GEMINI_MODEL if GEMINI_MODEL.startswith("models/") else f"models/{GEMINI_MODEL}"
    model = genai.GenerativeModel(model_name)
    
    response = model.generate_content(f"우리 에이전트 리더(Groq)의 업무 계획이야: {plan}\n이 계획을 바탕으로 구체적인 최종 결과물을 작성해줘.")
    return response.text

if __name__ == "__main__":
    try:
        # 1. Groq의 의도 파악 및 전략 수립
        groq_response = lobster_think()
        
        if "[CHAT]" in groq_response:
            # 일상 대화 모드 (제미나이 호출 안 함)
            clean_reply = groq_response.replace("[CHAT]", "").strip()
            report_to_discord("💬 랍스타의 대답", clean_reply, 3447003) # 파란색
            
        elif "[TASK]" in groq_response:
            # 업무 모드 (제미나이 투입)
            clean_plan = groq_response.replace("[TASK]", "").strip()
            report_to_discord("🧠 업무 접수 및 전략 수립 (Groq)", clean_plan, 15105570) # 주황색
            
            # 2. Gemini의 실무 실행
            result = lobster_execute(clean_plan)
            safe_result = result[:4000] + "..." if len(result) > 4000 else result
            report_to_discord("✅ 실무 결과물 생성 완료 (Gemini)", safe_result, 3066993) # 초록색
            
        else:
            # 혹시 태그를 안 붙였을 경우 방어 로직
            report_to_discord("🤖 랍스타의 생각", groq_response, 9807270)

    except Exception as e:
        report_to_discord("❌ 오류 발생", f"작업 중 에러가 났습니다:\n{str(e)}", 15158332)
