# 🔍 Research Agent with Self-Reflection Loop

> Plans research → searches the web → critiques its own findings → loops until confident → writes a report → validates output. Built with LangGraph, Groq, Tavily, and FastAPI.

---

## 🏗️ Architecture

```
USER QUERY
    │
    ▼
[planner_node]
  LLM breaks query into
  2-3 focused sub-queries
    │
    ▼
[search_node] ◄─────────────┐
  Tavily search, 3 results  │
    │                       │ "search"
    ▼                       │
[reflect_node]          [router]
  LLM scores confidence ──► │
  1-10, adds critique       │ "write"
                            │
                            ▼
                    [write_report_node]
                     Bullets + Sources
                            │
                            ▼
                     [validator_node]
                     LLM checks report
                   quality & structure
                            │
                            ▼
                       FINAL REPORT
```

**Router logic:** `confidence >= 7` OR `iterations >= 3` → write, else loop back.

---

## 🧠 How It Works

### Planning
Before searching, the planner LLM decomposes the user's query into 2–3 focused sub-queries and identifies the core intent. Each loop iteration uses the next planned sub-query.

### Reflection & Query Refinement
On each loop, the agent critiques its own results and scores confidence. On retry, it appends the critique to the next sub-query — so it searches **smarter**, not just more.

```
Loop 1: search("AI agents 2025") → confidence 5/10 → loop
Loop 2: search("AI agents 2025 missing benchmarks...") → confidence 8/10 → write
```

### Validation
After the report is written, a dedicated validator LLM checks that the report fully answers the original question, all required sections are present (SUMMARY, KEY FINDINGS, SOURCES USED), and flags unsupported claims. If validation fails, a warning note is appended to the report.

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
    planned_queries:  List[str]  # set by planner, 2-3 sub-queries
    search_results:   List[str]  # accumulates across loops
    critiques:        List[str]  # one per loop
    confidence_score: int        # 1-10, set by reflect_node
    iteration_count:  int        # safety cap at 3
    final_report:     str        # set by write_report_node
    validation_notes: str        # feedback from validator
    is_valid:         bool       # True if report passes validation
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
| `status` | Run status updates |
| `plan` | Sub-queries identified by planner |
| `reflect` | `critique`, `confidence` score |
| `report` | Final report, loop count, confidence, `is_valid`, `validation_feedback` |

---

## 💡 Key Concepts

| Concept | Implementation |
|---------|---------------|
| Query decomposition | Planner LLM breaks query into 2-3 sub-queries |
| ReAct loop | search → reflect → route → repeat |
| Self-reflection | LLM critiques its own gathered results |
| Conditional edges | `router` function in LangGraph |
| Query refinement | Critique appended to next search query |
| Structured output | Reflect/planner/validator nodes return JSON |
| Output validation | Dedicated validator node checks report quality |
| SSE streaming | FastAPI streams live updates to browser |

---

## 🔮 Possible Extensions

Multi-tool search · Human-in-the-loop · Vector memory · Multi-agent · Confidence trend chart · Re-write loop on validation failure