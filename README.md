# Lobster Chat Center (Apocalypse Legion)

A multi-agent AI command center built with Streamlit. Hire specialized AI agents, assign tools, run 1:1 tasks, host multi-agent debates, and orchestrate long-term autonomous projects — all from a single web dashboard.

**Related repository:** For background job automation, extended free tools, and Human-in-the-Loop (HITL) workflows, see the companion project [ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation).

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Repository Ecosystem](#repository-ecosystem)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration (API Keys & Secrets)](#configuration-api-keys--secrets)
- [User Manual](#user-manual)
  - [Sidebar: Global Settings](#sidebar-global-settings)
  - [Tab 1: 1:1 Direct Messages](#tab-1-11-direct-messages)
  - [Tab 2: War Room (Multi-Agent Debate)](#tab-2-war-room-multi-agent-debate)
  - [Tab 3: Long-term Project HQ](#tab-3-long-term-project-hq)
- [Agent System](#agent-system)
- [Available Tools](#available-tools)
- [Discord Notifications](#discord-notifications)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Overview

**Lobster Chat Center** is an AI advisor and multi-agent orchestration platform. Each agent ("Lobster") has a name, role, Groq LLM brain, and optional tool integrations. Agents can chat, execute real tasks (Notion docs, Slack messages, web search, image search), debate with each other, and run relay-style project workflows.

| Feature | Description |
|---------|-------------|
| **Agent Recruitment** | Create agents with custom names, roles, models, and tools |
| **1:1 Direct Messages** | Assign tasks to individual agents with file upload support |
| **War Room** | Multi-agent round-robin debate with Gemini-powered final reports |
| **Project HQ** | Leader assigns tasks to workers; automated relay execution |
| **Bilingual UI** | Korean and English interface and agent response language |
| **Discord Alerts** | Meeting reports and project completions sent via webhook |

---

## Tech Stack

### Core Framework & Language

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Language** | Python 3.9+ | Application runtime |
| **Web UI** | [Streamlit](https://streamlit.io/) | Interactive dashboard, chat UI, sidebar controls |
| **Agent Brain (Primary)** | [Groq API](https://groq.com/) via `groq` SDK | Fast LLM inference (Llama 3.x, Mixtral, etc.) for agent reasoning and task execution |
| **Chief Secretary** | [Google Gemini API](https://ai.google.dev/) via `google-generativeai` | Final meeting report generation and structured summaries |
| **HTTP Client** | `requests` | REST API calls to Notion, Slack, Tavily, Pixabay, Discord |

### External APIs & Integrations

| Service | Used For | Required? |
|---------|----------|-----------|
| **Groq** | Agent thinking, planning, content generation | **Required** |
| **Google Gemini** | War Room final reports (Chief Secretary) | **Required** |
| **Discord Webhook** | Push notifications for reports | **Required** |
| **Notion API** | SSOT document creation in databases | Optional (per agent) |
| **Slack API** | Team notifications | Optional (per agent) |
| **Tavily API** | Web search / crawling | Optional (per agent) |
| **Pixabay API** | Stock image search | Optional (per agent) |

### Data & Persistence

| Component | Format | Description |
|-----------|--------|-------------|
| `agents_roster.json` | JSON | Persisted agent roster (name, role, model, tools, Notion DB) |
| Streamlit Session State | In-memory | Chat histories, debate state, project progress |
| Streamlit Secrets | TOML | API keys and credentials (local or cloud) |

### Python Dependencies

```
streamlit
groq
google-generativeai
requests
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Repository Ecosystem

This project is part of a two-repo Lobster Agent family:

| Repository | Role | Link |
|------------|------|------|
| **ai_agent_mina** (this repo) | Streamlit command center — UI, agent management, debates, in-browser project orchestration | You are here |
| **[ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)** | Background automation layer — SQLite job queue, background worker, HITL pause/resume, extended free tools | Companion repo |

### When to use which repo

| Use Case | Recommended Repo |
|----------|------------------|
| Interactive agent chat, hiring, debates | **ai_agent_mina** (this repo) |
| Run long projects in the browser with live dashboard | **ai_agent_mina** (this repo) |
| Queue projects and process them in the background | **[ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)** |
| Human-in-the-Loop: pause when agents need help, resume with feedback | **[ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)** |
| Free tools without API keys (DuckDuckGo, file I/O, Python executor, short-form video) | **[ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)** |

### Extra capabilities in ai_agent_mina_automation

The automation repo extends the same `LobsterAgent` concept with:

- **`worker.py`** — Background worker that polls SQLite for `PENDING` jobs
- **`database.py`** — Job queue (`lobster_jobs.db`) with `PENDING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED` states
- **`provide_feedback()`** — Commander injects guidance when agents raise `[NEED_HELP]` / SOS
- **Additional free tools:** DuckDuckGo search, web scraper, local file read/write, Python subprocess executor, short-form video generator (MoviePy + gTTS), SNS webhook (Make/Zapier)

Both repos share the same agent roster file format (`agents_roster.json`), so agents hired in this UI can be reused by the automation worker.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit UI (app.py)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  Tab 1: DM   │  │ Tab 2: War   │  │ Tab 3: Project HQ    │ │
│  │  1:1 Chat    │  │ Room Debate  │  │ Leader → Workers     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LobsterAgent (agent.py)                       │
│   think_and_act() → [CHAT] or [TASK] → execute_tools()          │
└─────────┬───────────────────────────────┬───────────────────────┘
          │                               │
          ▼                               ▼
┌──────────────────┐           ┌────────────────────────────────┐
│   Groq API       │           │   tools.py                     │
│   (Agent Brain)  │           │   Notion / Slack / Tavily /    │
└──────────────────┘           │   Pixabay                      │
                               └────────────────────────────────┘
          │
          ▼ (War Room conclusion only)
┌──────────────────┐           ┌────────────────────────────────┐
│  Gemini API      │           │   discord_bot.py               │
│  (Chief Secretary│──────────▶│   Webhook notifications        │
│   Final Report)  │           └────────────────────────────────┘
└──────────────────┘

          Optional background layer (separate repo):
┌─────────────────────────────────────────────────────────────────┐
│  ai_agent_mina_automation: worker.py + database.py (SQLite)      │
└─────────────────────────────────────────────────────────────────┘
```

### Agent decision flow

1. User sends a command to an agent.
2. Groq evaluates the request and tags the response as `[CHAT]` (conversation) or `[TASK]` (action required).
3. For `[TASK]`, Groq generates a plan and output content, then `execute_tools()` runs matching integrations based on keywords in the plan and assigned tools.
4. Results are returned to the UI with an execution log.

---

## Project Structure

```
ai_agent_mina/
├── app.py              # Streamlit UI — tabs, sidebar, orchestration logic
├── agent.py            # LobsterAgent class — think_and_act, tool execution
├── tools.py            # API integrations (Notion, Slack, Tavily, Pixabay)
├── api_setup.py        # Secrets loader, model discovery, Notion DB listing
├── discord_bot.py      # Discord webhook reporter
├── requirements.txt    # Python dependencies
├── agents_roster.json  # Auto-generated agent persistence (created at runtime)
└── README.md           # This file
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- API keys for Groq, Gemini, and a Discord webhook (see [Configuration](#configuration-api-keys--secrets))

### Local setup

```bash
# Clone the repository
git clone https://github.com/Benjamin5607/ai_agent_mina.git
cd ai_agent_mina

# Install dependencies
pip install -r requirements.txt

# Configure secrets (see below)
mkdir -p .streamlit
# Create .streamlit/secrets.toml with your API keys

# Launch the app
streamlit run app.py
```

The app opens at `http://localhost:8501` by default.

---

## Configuration (API Keys & Secrets)

Create `.streamlit/secrets.toml` in the project root (never commit this file):

```toml
# Required
GROQ_API_KEY = "gsk_..."
GEMINI_API_KEY = "AIza..."
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."

# Optional — enable corresponding agent tools
NOTION_API_KEY = "secret_..."
NOTION_DATABASE_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
SLACK_BOT_TOKEN = "xoxb-..."
TAVILY_API_KEY = "tvly-..."
PIXABAY_API_KEY = "..."
```

### Where to obtain keys

| Key | Provider | Notes |
|-----|----------|-------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/) | Powers all agent reasoning |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) | Powers War Room final reports |
| `DISCORD_WEBHOOK_URL` | Discord Server Settings → Integrations → Webhooks | Receives meeting and project alerts |
| `NOTION_API_KEY` | [notion.so/my-integrations](https://www.notion.so/my-integrations) | Share target databases with the integration |
| `SLACK_BOT_TOKEN` | [api.slack.com/apps](https://api.slack.com/apps) | Needs `chat:write` scope |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com/) | Web search for agents with Web Crawler tool |
| `PIXABAY_API_KEY` | [pixabay.com/api/docs](https://pixabay.com/api/docs/) | Image search for agents with Pixabay tool |

For **Streamlit Cloud** deployment, add the same keys under **App Settings → Secrets**.

---

## User Manual

### Sidebar: Global Settings

#### Language / UI Language

- Toggle between **한국어** and **English**.
- Controls both the UI labels and the language agents are instructed to respond in.

#### Chief Secretary (Gemini)

- Select the Gemini model used to generate **final War Room meeting reports** after agents reach consensus.
- This model does not power day-to-day agent chat — only structured post-debate summaries.

#### Agent Recruitment

Hire new agents from the sidebar expander:

1. **Name** — e.g., `Jacob`
2. **Role** — e.g., `Project Manager`
3. **Brain & Hands (Groq)** — Choose the Groq model for this agent
4. **Assign Tools** — Select one or more integrations (see [Available Tools](#available-tools))
5. If **Notion API** is selected, pick a target database from the dropdown (requires `NOTION_API_KEY`)
6. Click **Hire & Save** — the agent is added to `agents_roster.json`

Default agent `랍스타-01 (만능 비서)` is created automatically on first launch.

---

### Tab 1: 1:1 Direct Messages

Use this tab to work directly with a single agent.

#### Left panel — Agent list

- Select an agent from the radio list.
- View the agent's assigned Groq model and tools.
- **Fire Agent** — Remove an agent from the roster (only shown when more than one agent exists).

#### Right panel — Chat

1. **Upload a file** (optional) — Supports `.txt`, `.csv`, `.md`. File content is appended to your command.
2. **Type a command** in the chat input and press Enter.
3. The agent responds with either:
   - A conversational reply (`[CHAT]`)
   - A task execution with generated content and tool logs (`[TASK]`)

#### Tips

- Agents remember the last 10 messages in the session.
- Mention documents, reports, or searches explicitly if you want tool execution (e.g., "Write a report to Notion").
- Tool execution depends on both the assigned tool **and** keywords in the agent's plan.

---

### Tab 2: War Room (Multi-Agent Debate)

A structured multi-agent debate that ends with a Gemini-generated action report.

#### Setup

1. **Select attendees** — Choose 2 or more agents from the multiselect.
2. **Enter an agenda** — The topic or question for the debate.
3. Click **Start Apocalypse Debate!**

#### Debate rules (enforced automatically)

- Agents speak in the selected UI language only.
- Maximum 5 sentences per turn.
- Agents criticize and propose extreme ideas.
- Agents append `[결론]` (conclusion) only when they agree.
- Early conclusions are rejected — the Commander pushes agents to dig deeper until enough rounds pass.

#### Flow

1. Agents take turns speaking (20-second cooldown between turns to avoid rate limits).
2. Older messages are compressed into a summary when short-term memory exceeds 4 entries.
3. When `[결론]` appears in a valid concluding turn:
   - Debate stops.
   - **Chief Secretary (Gemini)** generates a structured markdown report with:
     - Meeting Summary
     - Key Takeaways
     - Action Items (matched to each agent's role)
     - Expected Results
     - Individual AI Prompts (copy-paste ready for Tab 1)
   - Report is displayed in the UI and sent to Discord.

#### Controls

- **Stop Debate** — Force-end an active debate at any time.

---

### Tab 3: Long-term Project HQ

An autonomous three-phase project workflow run entirely in the browser.

#### Setup

1. **Select Project Leader (PM)** — The agent who plans and reviews.
2. **Select Workers** — One or more agents who execute tasks.
3. **Enter Grand Project Goal** — The Commander's high-level objective.
4. Click **Start Autonomous Project!**

#### Execution phases

| Phase | What happens |
|-------|--------------|
| **Planning** | Leader breaks the goal into per-worker tasks (`[Worker Name] \| [Task instruction]`) |
| **Executing** | Each worker runs tasks sequentially with a 20-second cooldown between tasks |
| **Review** | Leader compiles all results into a final report; sent to Discord |

#### Live Operations Dashboard

- Shows the task list, current worker progress, and execution results in real time.
- **Stop Project** — Halt the workflow at any time.

#### For background / queued execution

If you need projects to run outside the browser, survive page refreshes, or support Human-in-the-Loop pausing, use the companion repo:

**[ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)**

Run `worker.py` alongside the Streamlit app to process jobs from `lobster_jobs.db`.

---

## Agent System

### LobsterAgent class (`agent.py`)

| Method | Description |
|--------|-------------|
| `__init__(groq_key, name, role)` | Create an agent with Groq client |
| `think_and_act(user_message, chat_history)` | Returns `(action_type, text1, text2)` — `"chat"` or `"task"` |
| `execute_tools(execution_plan, content, api_secrets)` | Runs tool APIs based on plan keywords |

### Response tags

| Tag | Meaning |
|-----|---------|
| `[CHAT]` | Conversational response — no tool execution |
| `[TASK]` | Action plan — triggers content generation and tool calls |

### Roster persistence

Agents are saved to `agents_roster.json`:

```json
{
  "Jacob (Project Manager)": {
    "name": "Jacob",
    "role": "Project Manager",
    "model_groq": "llama-3.3-70b-versatile",
    "tools": ["📝 Notion API", "🌐 Web Crawler"],
    "notion_db_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }
}
```

---

## Available Tools

Tools are assigned per agent in the sidebar. Execution is keyword-triggered inside `execute_tools()`.

| Tool | Trigger Keywords (KO) | API Key | Action |
|------|----------------------|---------|--------|
| **📝 Notion API** | 노션, 문서, 보고서 | `NOTION_API_KEY`, DB ID | Creates structured SSOT pages in Notion |
| **💬 Slack API** | 슬랙, 알림, 메시지 | `SLACK_BOT_TOKEN` | Posts message to `#general` |
| **🌐 Web Crawler** | 웹 검색, 크롤링, 검색 | `TAVILY_API_KEY` | Tavily web search (top 3 results) |
| **🎨 Pixabay API** | 이미지, 사진 | `PIXABAY_API_KEY` | Returns stock image URLs |
| **🐙 GitHub API** | — | — | Listed in UI; not yet implemented in `tools.py` |
| **📊 Google Sheets API** | — | — | Listed in UI; not yet implemented in `tools.py` |

> For GitHub, file system, Python execution, free web search, and video generation tools, see **[ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)**.

### Notion document formatting

When creating Notion documents, agents apply role-based SSOT templates:

- **PM / Planning:** Executive Summary, Objective, Timeline, RACI, Action Items
- **Data:** Analysis purpose, KPIs, insights, recommendations
- **Marketing:** Target audience, messaging, channel strategy, ROI

---

## Discord Notifications

`discord_bot.py` sends embed messages to your configured webhook:

| Event | Title | When |
|-------|-------|------|
| War Room conclusion | `📜 최종 회의 보고서` | After Gemini generates the final debate report |
| Project completion | `🚀 프로젝트 완료 보고` | After Tab 3 review phase completes |

Messages are truncated to 4,000 characters for Discord embed limits.

---

## Deployment

### Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and connect the repository.
3. Set **Main file path** to `app.py`.
4. Add all secrets under **Advanced settings → Secrets**.
5. Deploy.

### Local / VPS

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

For production, place a reverse proxy (nginx, Caddy) with HTTPS in front of the Streamlit server.

### Pairing with the automation worker

```bash
# Terminal 1 — UI
streamlit run app.py

# Terminal 2 — Background worker (from ai_agent_mina_automation repo)
python worker.py
```

Both processes read the same `agents_roster.json` and Streamlit secrets.

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| App stops on launch with secrets error | Missing required keys | Add `GROQ_API_KEY`, `GEMINI_API_KEY`, `DISCORD_WEBHOOK_URL` to secrets |
| `429` / rate limit errors | Too many Groq requests | Wait for the 20-second cooldown; reduce concurrent agents |
| Tools not executing | Keywords or tool not assigned | Assign the tool to the agent; use trigger keywords in your command |
| Notion DB dropdown empty | Integration not shared | Share databases with your Notion integration |
| Discord messages not arriving | Invalid webhook URL | Regenerate webhook in Discord server settings |
| Agent speaks wrong language | Language toggle | Set UI language in sidebar before starting chat/debate |

---

## License

No license file is currently specified. Contact the repository owner for usage terms.

---

## Links

- **This repository:** [github.com/Benjamin5607/ai_agent_mina](https://github.com/Benjamin5607/ai_agent_mina)
- **Automation companion:** [github.com/Benjamin5607/ai_agent_mina_automation](https://github.com/Benjamin5607/ai_agent_mina_automation)
- **Groq Console:** [console.groq.com](https://console.groq.com/)
- **Google AI Studio:** [aistudio.google.com](https://aistudio.google.com/)
- **Streamlit Docs:** [docs.streamlit.io](https://docs.streamlit.io/)
