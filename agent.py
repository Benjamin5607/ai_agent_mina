from groq import Groq
import google.generativeai as genai
import streamlit as st
import tools

class LobsterAgent:
    def __init__(self, groq_key, gemini_key, name="랍스타-01", role="만능 비서"):
        self.name = name
        self.role = role
        self.groq_client = Groq(api_key=groq_key)
        self.gemini_key = gemini_key
        genai.configure(api_key=gemini_key)
        self.tools = []
        self.notion_db_id = None # 📌 에이전트 고유의 노션 DB 아이디 저장 공간!

    def execute_tools(self, execution_plan, actual_content, api_secrets):
        action_logs = []
        
        if "🌐 Web Crawler" in self.tools and ("웹 검색" in execution_plan or "크롤링" in execution_plan or "검색" in execution_plan):
            try:
                query_model = genai.GenerativeModel("gemini-1.5-flash")
                query = query_model.generate_content(f"다음 계획에서 웹 검색 키워드 1개만 영어로 추출해: {execution_plan}").text.strip()
                result = tools.use_web_crawler(query, api_secrets.get("TAVILY_API_KEY", ""))
                action_logs.append(result)
            except Exception as e: action_logs.append(f"🚨 웹 검색 파싱 에러: {e}")
            
        if "🎨 Pixabay API" in self.tools and ("이미지" in execution_plan or "사진" in execution_plan):
            try:
                query_model = genai.GenerativeModel("gemini-1.5-flash")
                query = query_model.generate_content(f"다음 계획에서 이미지 키워드 1개만 영어로 추출해: {execution_plan}").text.strip()
                result = tools.use_pixabay_api(query, api_secrets.get("PIXABAY_API_KEY", ""))
                action_logs.append(result)
            except Exception as e: action_logs.append(f"🚨 이미지 검색 파싱 에러: {e}")
            
        # 📌 수정됨: 이제 에이전트가 자기가 배정받은 전용 노션 DB ID를 사용합니다!
        if "📝 Notion API" in self.tools and ("노션" in execution_plan or "문서" in execution_plan or "보고서" in execution_plan):
            title = f"[{self.name}의 보고서] 자동 생성 문서"
            db_to_use = self.notion_db_id if self.notion_db_id else api_secrets.get("NOTION_DATABASE_ID", "")
            result = tools.use_notion_api(title, actual_content, api_secrets.get("NOTION_API_KEY", ""), db_to_use)
            action_logs.append(result)
            
        if "💬 Slack API" in self.tools and ("슬랙" in execution_plan or "알림" in execution_plan or "메시지" in execution_plan):
            msg = f"[{self.name}] 업무 보고\n{actual_content[:200]}..."
            result = tools.use_slack_api(msg, api_secrets.get("SLACK_BOT_TOKEN", ""))
            action_logs.append(result)
            
        return "\n\n".join(action_logs) if action_logs else "⚠️ 툴 작동 조건에 맞지 않아 API를 호출하지 않았습니다."

    def think_and_act(self, user_message, chat_history, groq_model, gemini_model):
        tools_info = ", ".join(self.tools) if self.tools else "없음"
        system_prompt = f"""
        너의 이름은 '{self.name}'. 담당 직무는 '{self.role}'이다.
        [장착 무기(Tools)]: {tools_info}
        1. 단순 대화면 [CHAT] 태그를 달아라.
        2. 실제 결과물을 만들고 툴을 써야 한다면 [TASK] 태그를 달고 계획을 적어라. 절대 없는 수치나 가짜 통계를 지어내지 마라.
        """
        
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})
        
        chat_completion = self.groq_client.chat.completions.create(
            messages=messages, model=groq_model, temperature=0.3
        )
        response = chat_completion.choices[0].message.content
        
        if "[TASK]" in response:
            plan = response.replace("[TASK]", "").strip()
            
            # 📌 웡빈 사령관의 특별 지시: 직무별 프로페셔널 SSOT 문서화 강제 룰!
            professional_formatting = ""
            if "📝 Notion API" in self.tools and ("노션" in plan or "문서" in plan or "보고서" in plan):
                professional_formatting = f"""
                [⚠️ 노션 SSOT 문서화 절대 규칙 ⚠️]
                너는 실리콘밸리 최고 수준의 프로페셔널 '{self.role}'이다. 네가 작성하는 이 문서는 팀의 진실의 원천(SSOT)이 된다.
                단순한 줄글 작성을 극도로 혐오하며, 너의 직무에 맞는 완벽한 구조화 템플릿을 무조건 적용해라.

                - 직무가 'PM'이나 '기획' 계열이라면: [Executive Summary], [Objective], [Timeline], [RACI/담당자], [Action Items] 구조로 작성해라.
                - 직무가 '데이터' 계열이라면: [분석 목적], [핵심 지표(KPIs)], [데이터 인사이트 요약], [결론 및 제언] 구조로 작성해라.
                - 직무가 '마케팅' 계열이라면: [타겟 오디언스], [핵심 메시지], [채널 전략], [예상 ROI] 구조로 작성해라.
                - 기타 직무: 가독성을 극대화하기 위해 헤더(#), 불릿 포인트(-), 체크리스트를 적극 활용해 가장 논리적으로 작성해라.
                """
            
            model = genai.GenerativeModel(gemini_model)
            execution_prompt = f"""
            사령관 지시: {user_message}
            너의 계획: {plan}
            {professional_formatting}
            
            위 지시를 수행하기 위한 텍스트 결과물을 작성해. 거듭 강조하지만 거짓말은 해고 사유다.
            """
            result_text = model.generate_content(execution_prompt).text
            tool_results = self.execute_tools(plan, result_text, st.secrets)
            return "task", plan, f"{result_text}\n\n---\n**[🛠️ 시스템 무기 실제 실행 로그]**\n{tool_results}"
        else:
            return "chat", response.replace("[CHAT]", "").strip(), None
