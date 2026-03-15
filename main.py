import os
import json
import requests
from groq import Groq
import google.generativeai as genai

# ==========================================
# 1. 환경 변수 세팅 (GitHub Secrets & Inputs)
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

GROQ_MODEL = os.getenv("LOBSTER_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")
TASK = os.getenv("LOBSTER_TASK", "ops_risk")
USER_MESSAGE = os.getenv("USER_MESSAGE", "안녕?")

MEMORY_FILE = "memory.json"

# ==========================================
# 2. 클라이언트 초기화
# ==========================================
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 3. 핵심 기능 함수들
# ==========================================
def report_to_discord(title, description, color=16730698):
    """디스코드 웹후크로 깔끔한 임베드(Embed) 메시지를 전송합니다."""
    payload = {
        "username": "랍스타-자율-01",
        "avatar_url": "https://i.imgur.com/4E7989q.png", # 랍스타 프로필 이미지
        "embeds": [{"title": title, "description": description, "color": color}]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

def load_memory():
    """과거 대화 기록(기억 장치)을 불러옵니다."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_memory(history):
    """최근 10번의 티키타카만 기억장치에 저장합니다. (토큰 절약 목적)"""
    if len(history) > 10:
        history = history[-10:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def lobster_think(chat_history):
    """Groq 뇌 가동: 과거 기억을 바탕으로 의도를 파악하고 계획을 세웁니다."""
    system_prompt = f"""
    너의 이름은 '랍스타-01'이다. 너는 직장 동료처럼 친근하고 유능하게 대화하는 에이전트다.
    너를 만든 주인님의 이름은 '벤'이다.
    현재 네가 담당하고 있는 직무 파트: {TASK}
    
    [행동 지침 - 매우 중요]
    1. 사용자의 요청이 일상적인 대화, 인사, 질문이라면 아주 자연스럽게 1~2줄로 대답해라. 
       (이 경우, 반드시 답변 맨 앞에 [CHAT] 이라는 태그를 붙일 것)
       
    2. 사용자가 문서 작성, 데이터 분석, 크롤링 등 구체적인 '업무'를 지시했다면, 이 업무를 어떻게 처리할지 3단계 요약 계획을 세워라. 
       (이 경우, 반드시 답변 맨 앞에 [TASK] 라는 태그를 붙일 것)
    """
    
    # 시스템 프롬프트 + 과거 기억 + 현재 사용자 메시지 병합
    messages = [{"role": "system", "content": system_prompt}] + chat_history
    messages.append({"role": "user", "content": USER_MESSAGE})
    
    chat_completion = groq_client.chat.completions.create(
        messages=messages,
        model=GROQ_MODEL,
    )
    return chat_completion.choices[0].message.content

def lobster_execute(plan):
    """Gemini 손발 가동: Groq이 세운 계획을 바탕으로 실제 실무 결과물을 생성합니다."""
    # API 이름 형식 맞추기 (models/ 가 없으면 붙여줌)
    model_name = GEMINI_MODEL if GEMINI_MODEL.startswith("models/") else f"models/{GEMINI_MODEL}"
    model = genai.GenerativeModel(model_name)
    
    execution_prompt = f"""
    우리 에이전트 리더(Groq)의 업무 계획이야:
    {plan}
    
    이 계획을 바탕으로, 주인님이 바로 복사해서 쓸 수 있도록 
    구체적이고 완성도 높은 최종 결과물(마크다운 형식)을 작성해줘.
    """
    response = model.generate_content(execution_prompt)
    return response.text

# ==========================================
# 4. 메인 실행 루프
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 단기 기억 불러오기
        history = load_memory()
        
        # 2. 뇌 가동 (의도 파악 및 답변/계획 생성)
        groq_response = lobster_think(history)
        
        # 3. 행동 결정 및 디스코드 보고
        if "[CHAT]" in groq_response:
            # 일상 대화 모드 (제미나이 투입 안 함)
            clean_reply = groq_response.replace("[CHAT]", "").strip()
            report_to_discord("💬 랍스타의 대답", clean_reply, 3447003) # 파란색 띠
            
        elif "[TASK]" in groq_response:
            # 업무 모드 (제미나이 투입)
            clean_plan = groq_response.replace("[TASK]", "").strip()
            report_to_discord("🧠 업무 접수 및 전략 수립 (Groq)", clean_plan, 15105570) # 주황색 띠
            
            # 제미나이 실행
            result = lobster_execute(clean_plan)
            # 디스코드 메시지 길이 제한(4096자) 방어
            safe_result = result[:4000] + "..." if len(result) > 4000 else result
            report_to_discord("✅ 실무 결과물 생성 완료 (Gemini)", safe_result, 3066993) # 초록색 띠
            
        else:
            # 혹시 모델이 태그를 빼먹었을 경우 방어 로직
            report_to_discord("🤖 랍스타의 생각", groq_response, 9807270)
            
        # 4. 방금 나눈 대화를 기억 장치에 추가하고 깃허브에 영구 저장 준비
        history.append({"role": "user", "content": USER_MESSAGE})
        history.append({"role": "assistant", "content": groq_response}) # 태그가 포함된 원본을 기억해야 다음 턴에도 태그 룰을 잘 지킴
        save_memory(history)

    except Exception as e:
        report_to_discord("❌ 오류 발생", f"작업 중 에러가 났습니다:\n{str(e)}", 15158332) # 빨간색 띠
