from groq import Groq
import google.generativeai as genai

class LobsterAgent:
    def __init__(self, groq_key, gemini_key, name="랍스타-01", role="만능 비서"):
        """에이전트가 태어날 때 이름과 직무, API 키를 부여받습니다."""
        self.name = name
        self.role = role
        self.groq_client = Groq(api_key=groq_key)
        genai.configure(api_key=gemini_key)

    def think_and_act(self, user_message, chat_history, groq_model, gemini_model):
        """Groq으로 생각하고, 필요시 Gemini로 행동합니다."""
        
        system_prompt = f"""
        너의 이름은 '{self.name}'. 담당 직무는 '{self.role}'이다. 주인님은 '웡빈'.
        1. 일상 대화는 [CHAT] 태그 부착.
        2. 파일 분석이나 업무 지시면 [TASK] 태그 부착 후 3단계 계획 작성.
        """
        
        # 메시지 조립
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        # 1단계: 뇌(Groq) 가동
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=groq_model
        )
        response = chat_completion.choices[0].message.content
        
        # 2단계: 행동 판단
        if "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            # 제미나이 실행
            model = genai.GenerativeModel(gemini_model)
            execution_prompt = f"계획:\n{plan}\n\n원본 데이터:\n{user_message}\n\n구체적인 최종 결과물을 작성해."
            result = model.generate_content(execution_prompt).text
            return "task", plan, result
            
        elif "[CHAT]" in response:
            chat = response.replace("[CHAT]", "").strip()
            return "chat", chat, None
            
        else:
            return "chat", response, None
