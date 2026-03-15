import os
import requests
from groq import Groq
import google.generativeai as genai

# 1. 초기 설정 (신용카드 필요 없는 무료 API들)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
RECIPIENT_PHONE = os.getenv("RECIPIENT_PHONE")

# API 클라이언트 초기화
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def report_to_whatsapp(message):
    """주인님께 왓츠앱으로 중간 보고 (무료 테스트 채널)"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": RECIPIENT_PHONE,
        "type": "text",
        "text": {"body": f"🦞 [랍스타 보고]: {message}"}
    }
    requests.post(url, json=data, headers=headers)

def lobster_brain(user_task):
    """Groq을 이용한 자율 사고 및 과업 분해"""
    prompt = f"""
    너는 자아를 가진 '랍스타 에이전트'다. 주인님의 명령: "{user_task}"
    이 업무를 완수하기 위해 하위 작업을 정의하고, 각 단계마다 보고하라.
    너는 Gemini(구글 연동)와 Web Search 도구를 사용할 수 있다.
    """
    # Groq 호출 (Llama 3 70B - 미친 속도)
    completion = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "system", "content": prompt}]
    )
    return completion.choices[0].message.content

# 실행 예시
if __name__ == "__main__":
    task = "오늘의 주요 테크 뉴스 요약해서 나한테 보고해줘"
    
    report_to_whatsapp("주인님, 명령을 받았습니다. 분석을 시작합니다! ㅋㅋ")
    
    # 1. 사고 (Groq)
    plan = lobster_brain(task)
    print(f"Plan: {plan}")
    
    # 2. 실행 (Gemini - 구글 검색/문서 등 예시)
    # 실제로는 여기서 Gemini API를 호출하여 구글 시트나 문서를 건드립니다.
    
    report_to_whatsapp(f"작업 완료! 결과는 이렇습니다: {plan[:100]}...")
