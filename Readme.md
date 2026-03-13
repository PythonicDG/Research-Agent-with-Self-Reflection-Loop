# 🔍 Research Agent with Self-Reflection Loop

> Searches the web → critiques its own findings → loops until confident → writes a report. Built with LangGraph, Groq, Tavily, and FastAPI.

---

## 🏗️ Architecture

```
USER QUERY
    │
    ▼
[search_node] ◄─────────────┐
  Tavily search, 3 results   │
    │                        │ "search"
    ▼                        │
[reflect_node]           [router]
  LLM scores confidence ──►  │
  1-10, adds critique         │ "write"
                              │
                              ▼
                       [write_report_node]
                         Bullets + Sources
                              │
                              ▼
                         FINAL REPORT
```

**Router logic:** `confidence >= 7` OR `iterations >= 3` → write, else loop back.

---

## 🧠 How Reflection Works

On each loop, the agent critiques its own results and scores confidence. On retry, it appends the critique to the query — so it searches **smarter**, not just more.

```
Loop 1: search("AI agents 2025") → confidence 5/10 → loop
Loop 2: search("AI agents 2025 missing benchmarks...") → confidence 8/10 → write
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph |
| LLM | Groq (llama-3.3-70b) |
| Search | Tavily |
| Backend | FastAPI + SSE streaming |
| Frontend | Vanilla HTML/CSS/JS |

---

## 🗂️ Agent State

```python
class AgentState(TypedDict):
    query:            str        # never changes
    search_results:   List[str]  # accumulates across loops
    critiques:        List[str]  # one per loop
    confidence_score: int        # 1-10, set by reflect_node
    iteration_count:  int        # safety cap at 3
    final_report:     str        # set at the end
```

---

## 📂 Project Structure

```
research_agent/
├── main.py            # FastAPI backend + LangGraph agent
├── static/
│   └── index.html     # Frontend UI
└── README.md
```

---

## 🚀 Setup

```bash
# Install
pip install fastapi uvicorn langgraph langchain langchain-groq tavily-python

# Set keys
export GROQ_API_KEY="your-key"
export TAVILY_API_KEY="your-key"

# Run
uvicorn main:app --reload
# Open → http://localhost:8000
```

Get API keys free at [console.groq.com](https://console.groq.com) and [app.tavily.com](https://app.tavily.com).

---

## 🖥️ API

**`POST /research`** — streams SSE events as the agent runs.

```json
{ "query": "Latest developments in AI agents 2025?" }
```

| Event | Payload |
|-------|---------|
| `status` | Run started |
| `reflect` | `critique`, `confidence` score |
| `report` | Final report, loop count, confidence |

---

## 💡 Key Concepts

| Concept | Implementation |
|---------|---------------|
| ReAct loop | search → reflect → route → repeat |
| Self-reflection | LLM critiques its own gathered results |
| Conditional edges | `router` function in LangGraph |
| Query refinement | Critique appended to next search query |
| Structured output | Reflect node returns JSON with confidence score |
| SSE streaming | FastAPI streams live updates to browser |

---

## 🔮 Possible Extensions

Multi-tool search · Query decomposition · Human-in-the-loop · Vector memory · Multi-agent · Confidence trend chart

---