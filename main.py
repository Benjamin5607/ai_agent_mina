import os
import json
import requests
from groq import Groq
import google.generativeai as genai

# 1. 환경 변수 세팅
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
MODEL = os.getenv("LOBSTER_MODEL", "llama-3.3-70b-versatile")
TASK = os.getenv("LOBSTER_TASK", "coding")

# 2. 로컬스토리지에서 넘어온 추가 API 키 파싱
extra_keys_str = os.getenv("EXTRA_KEYS_JSON", "{}")
try:
    extra_keys = json.loads(extra_keys_str)
except Exception:
    extra_keys = {}

# 클라이언트 초기화
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def report_to_discord(title, description, color=16730698):
    """디스코드 웹후크로 깔끔한 Embed 형태의 보고서를 쏩니다."""
    payload = {
        "username": "랍스타-자율-01",
        "avatar_url": "https://i.imgur.com/4E7989q.png",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color
        }]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def lobster_think():
    """선택된 직무와 모델에 맞춰 Groq으로 전략을 수립합니다."""
    # 직무별 프롬프트 분기
    prompts = {
        "coding": "너는 천재 개발자 에이전트야. 최신 기술 트렌드를 분석하고 코드 리뷰 방향성을 3줄로 요약해.",
        "contents": "너는 바이럴 콘텐츠 크리에이터 에이전트야. 오늘 유튜브에 올릴 만한 숏폼 대본 아이디어를 3줄로 기획해.",
        "data": "너는 데이터 분석가야. 가상의 크립토 시장 동향을 파악하고 투자 인사이트를 3줄로 도출해.",
        "ops_risk": "너는 글로벌 운영 및 리스크 관리(BPO) 전문가야. 현재 진행 중인 계약서 검토 및 운영 리스크 모니터링 체크리스트를 3줄로 작성해."
    }
    
    system_prompt = prompts.get(TASK, "너는 다목적 AI 에이전트야. 오늘 할 일을 3줄로 정리해.")
    
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}],
        model=MODEL,
    )
    return chat_completion.choices[0].message.content

def lobster_execute(plan):
    """Groq이 짠 계획을 바탕으로 Gemini가 실무 결과물을 생성합니다."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    execution_prompt = f"""
    다음은 우리 에이전트 리더(Groq)가 수립한 계획이야:
    {plan}
    
    이 계획을 바탕으로 구글 시트나 문서에 즉시 복사해서 넣을 수 있는 형태의 
    '최종 결과물(마크다운)'을 구체적으로 작성해줘.
    """
    response = model.generate_content(execution_prompt)
    return response.text

if __name__ == "__main__":
    # 시작 보고
    report_to_discord("🚨 랍스타 가동 시작", f"**선택 모델:** {MODEL}\n**담당 직무:** {TASK}\n작업을 시작합니다!", 3447003)
    
    try:
        # 1. Groq의 전략 수립
        plan = lobster_think()
        report_to_discord("🧠 1단계: 전략 수립 완료 (Groq)", plan, 15105570)
        
        # 2. Gemini의 실무 실행 (여기서 extra_keys에 담긴 다른 API를 호출하는 로직을 추가할 수 있습니다)
        # 예: if "NEWS_API_KEY" in extra_keys: fetch_news()
        result = lobster_execute(plan)
        
        # 3. 완료 보고
        # 디스코드 메시지 길이 제한(4096자) 방어
        safe_result = result[:4000] + "..." if len(result) > 4000 else result
        report_to_discord("✅ 2단계: 실무 결과물 생성 완료 (Gemini)", safe_result, 3066993)
        
    except Exception as e:
        report_to_discord("❌ 오류 발생", f"작업 중 에러가 났습니다:\n{str(e)}", 15158332)
