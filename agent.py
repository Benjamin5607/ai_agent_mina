from groq import Groq
import google.generativeai as genai
import streamlit as st
import json
import tools # 📌 방금 만든 무기고 수입!

class LobsterAgent:
    def __init__(self, groq_key, gemini_key, name="랍스타-01", role="만능 비서"):
        self.name = name
        self.role = role
        self.groq_client = Groq(api_key=groq_key)
        self.gemini_key = gemini_key
        genai.configure(api_key=gemini_key)
        self.tools = []

    def execute_tools(self, execution_plan, api_secrets):
        """제미나이가 짜놓은 계획을 보고 실제 파이썬 함수(무기)를 격발시킵니다!"""
        action_logs = []
        
        # 1. 🌐 웹 검색 격발
        if "🌐 Web Crawler" in self.tools and "웹 검색" in execution_plan or "크롤링" in execution_plan:
            # 제미나이에게 검색어 추출 시키기
            query_model = genai.GenerativeModel("gemini-1.5-flash")
            query = query_model.generate_content(f"다음 계획에서 웹 검색할 '키워드' 딱 1개만 영어로 추출해: {execution_plan}").text.strip()
            result = tools.use_web_crawler(query, api_secrets.get("TAVILY_API_KEY", ""))
            action_logs.append(result)
            
        # 2. 🎨 픽사베이 이미지 격발
        if "🎨 Pixabay API" in self.tools and "이미지" in execution_plan or "사진" in execution_plan:
            query_model = genai.GenerativeModel("gemini-1.5-flash")
            query = query_model.generate_content(f"다음 계획에서 검색할 이미지 '키워드' 딱 1개만 영어로 추출해: {execution_plan}").text.strip()
            result = tools.use_pixabay_api(query, api_secrets.get("PIXABAY_API_KEY", ""))
            action_logs.append(result)
            
        # 3. 📝 노션 작성 격발
        if "📝 Notion API" in self.tools and "노션" in execution_plan or "문서화" in execution_plan:
            title = f"[{self.name}의 보고서] 자동 생성 문서"
            result = tools.use_notion_api(title, execution_plan, api_secrets.get("NOTION_API_KEY", ""), api_secrets.get("NOTION_DATABASE_ID", ""))
            action_logs.append(result)
            
        # 4. 💬 슬랙 알림 격발
        if "💬 Slack API" in self.tools and "슬랙" in execution_plan or "알림" in execution_plan:
            msg = f"[{self.name}] 요원이 업무를 완료했습니다!\n요약: {execution_plan[:100]}..."
            result = tools.use_slack_api(msg, api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 장착된 툴이 없거나 실행할 API 조건이 맞지 않아 일반 텍스트로만 답변합니다."

    def think_and_act(self, user_message, chat_history, groq_model, gemini_model):
        """에이전트의 뇌(Groq)와 손발(Gemini/Tools) 통합 가동"""
        
        tools_info = ", ".join(self.tools) if self.tools else "없음"
        system_prompt = f"""
        너의 이름은 '{self.name}'. 담당 직무는 '{self.role}'이다.
        [장착 무기(Tools)]: {tools_info}
        
        1. 단순 대화나 아이디어 논의면 [CHAT] 태그를 부착해라.
        2. 네가 가진 '장착 무기(Tools)'를 실제로 사용해서 물리적인 결과물을 내야 하는 '업무 지시'라면 반드시 [TASK] 태그를 부착하고, 어떤 툴을 어떻게 쓸 것인지 계획을 적어라.
        """
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        # 1. Groq 뇌 가동
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=groq_model, temperature=0.7
        )
        response = chat_completion.choices[0].message.content
        
        # 2. 행동 분기
        if "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            # 실무 모델(Gemini) 가동하여 최종 기획안 작성
            model = genai.GenerativeModel(gemini_model)
            execution_prompt = f"계획:\n{plan}\n\n원본 지시:\n{user_message}\n\n이 지시를 수행하기 위한 완벽한 결과물 텍스트를 작성해."
            result_text = model.generate_content(execution_prompt).text
            
            # 🚀 [핵심] 툴 실행기 격발! (app.py에서 secrets를 가져와야 하므로 st.secrets 사용)
            tool_results = self.execute_tools(plan, st.secrets)
            
            final_output = f"{result_text}\n\n---\n**[🛠️ 시스템 무기 실행 결과]**\n{tool_results}"
            return "task", plan, final_output
            
        else:
            clean_chat = response.replace("[CHAT]", "").strip()
            return "chat", clean_chat, None
