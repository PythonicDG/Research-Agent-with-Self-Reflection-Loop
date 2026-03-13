# 🔍 Research Agent with Self-Reflection Loop

> An agentic AI system that searches the web, critiques its own answers, loops until confident, and writes a structured report — built with LangGraph, Groq, Tavily, and FastAPI.

---

## 📌 What This Is

Most AI search tools do **one-shot retrieval** — search once, answer immediately. This agent is different.

It uses a **ReAct loop with self-reflection**: after every search, it critiques its own findings, scores its confidence, and decides whether to search again or write the final report. This mirrors how a real researcher works.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        USER QUERY                        │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   search_node   │  ◄──────────────┐
                    │                 │                  │
                    │  Calls Tavily   │                  │
                    │  max 3 results  │                  │
                    │  Appends to     │                  │
                    │  search_results │                  │
                    └────────┬────────┘                  │
                             │                           │
                             ▼                           │
                    ┌─────────────────┐                  │
                    │  reflect_node   │                  │
                    │                 │                  │
                    │  LLM critiques  │                  │
                    │  all results    │                  │
                    │  Scores 1-10    │                  │
                    │  confidence     │                  │
                    └────────┬────────┘                  │
                             │                           │
                             ▼                           │
                    ┌─────────────────┐                  │
                    │     router      │  "search" ───────┘
                    │  (conditional   │
                    │    edge)        │  "write"  ───────┐
                    │                 │                  │
                    │ conf >= 7  OR   │                  │
                    │ iter >= 3       │                  │
                    └─────────────────┘                  │
                                                         ▼
                                               ┌─────────────────┐
                                               │ write_report_   │
                                               │     node        │
                                               │                 │
                                               │ Bullet summary  │
                                               │ Key findings    │
                                               │ Sources used    │
                                               └────────┬────────┘
                                                        │
                                                        ▼
                                                  FINAL REPORT
```

---

## 🧠 How The Reflection Loop Works

```
Iteration 1:
  search("AI agents 2025")
  → 3 results found
  reflect → confidence: 5/10
  critique: "Missing recent model releases and benchmarks"
  router → "search again"

Iteration 2:
  search("AI agents 2025" + "Missing recent model releases...")
  → 3 more results (6 total)
  reflect → confidence: 8/10
  critique: "Good coverage now"
  router → "write report"

Final:
  write_report(all 6 results + both critiques)
  → structured report with bullets + sources
```

The key insight: **the refined query on loop 2 uses the critique** — so the agent searches smarter, not just more.

---

## 📂 Project Structure

```
research_agent/
├── main.py              # FastAPI backend + full LangGraph agent
├── static/
│   └── index.html       # Frontend UI (dark terminal aesthetic)
└── README.md            # This file
```

---

## ⚙️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent framework | LangGraph | Native graph-based loop control, streaming support |
| LLM | Groq (llama-3.3-70b) | Fast inference, free tier, great for ReAct |
| Search tool | Tavily | Purpose-built for AI agents, clean API |
| Backend | FastAPI | Async-native, SSE streaming, production-grade |
| Frontend | Vanilla HTML/CSS/JS | No build step, runs anywhere |

---

## 🗂️ Agent State

The entire agent memory is carried in one TypedDict across all nodes:

```python
class AgentState(TypedDict):
    query:            str        # original user question — never changes
    search_results:   List[str]  # accumulated across ALL iterations
    critiques:        List[str]  # one critique appended per loop
    confidence_score: int        # 1-10, updated by reflect_node each loop
    iteration_count:  int        # increments in search_node
    final_report:     str        # only set by write_report_node
```

---

## 🔧 Node Breakdown

### `search_node`
- **Iteration 1**: searches using the raw user query
- **Iteration 2+**: appends the last 100 chars of the most recent critique to the query
- Appends new results to `search_results` (never overwrites)
- Bumps `iteration_count`

### `reflect_node`
- Sends ALL accumulated results + ALL previous critiques to the LLM
- Prompts for structured JSON: `{"critique": "...", "confidence": 7}`
- Updates `confidence_score` and appends to `critiques`

### `router`
```python
if confidence_score >= 7 or iteration_count >= 3:
    return "write"   # done
return "search"      # loop again
```
Two exit conditions: LLM satisfied **or** safety cap hit.

### `write_report_node`
- Receives all results + all critiques
- Outputs structured report: Summary bullets → Key Findings → Sources

---

## 🚀 Setup & Running

### 1. Install dependencies

```bash
pip install fastapi uvicorn langgraph langchain langchain-groq tavily-python
```

### 2. Get API keys

| Service | Free Tier | Link |
|---------|-----------|------|
| Groq | Yes — fast LLM inference | [console.groq.com](https://console.groq.com) |
| Tavily | 1000 searches/month | [app.tavily.com](https://app.tavily.com) |

### 3. Set environment variables

```bash
export GROQ_API_KEY="your-groq-key-here"
export TAVILY_API_KEY="your-tavily-key-here"
```

### 4. Run the server

```bash
uvicorn main:app --reload
```

### 5. Open in browser

```
http://localhost:8000
```

---

## 🖥️ API Reference

### `POST /research`

Runs the full research agent loop and streams results as Server-Sent Events.

**Request body:**
```json
{ "query": "What are the latest developments in AI agents 2025?" }
```

**Streamed SSE events:**

| Event type | Payload | Triggered by |
|------------|---------|--------------|
| `status` | `{message}` | Start of run |
| `search` | `{message}` | After each search_node |
| `reflect` | `{message, critique, confidence}` | After each reflect_node |
| `report` | `{report, loops, confidence, critiques}` | After write_report_node |

---

## 🖼️ UI Features

- **Live terminal log** — streams every agent step in real time with timestamps
- **Confidence bar** — animates as reflect_node updates the score each loop
- **Final report panel** — appears with loop count + confidence badges
- **Reflection history** — collapsible accordion showing every critique made
- **Enter key support** — press Enter to run, no need to click

---

## 💡 Key Concepts Demonstrated

| Concept | Where |
|---------|-------|
| **ReAct loop** | search → reflect → route → repeat |
| **Self-reflection** | `reflect_node` critiques its own gathered research |
| **Conditional edges** | `router` function wired as LangGraph conditional edge |
| **Stateful agent** | `AgentState` carries full memory across all nodes |
| **Query refinement** | Loop 2+ uses critique to generate smarter search query |
| **Safety cap** | `iteration_count >= 3` prevents infinite loops |
| **SSE streaming** | FastAPI streams live node updates to the browser |
| **Structured LLM output** | Reflect node prompted for JSON with confidence score |

---

## 🔮 Possible Extensions

- **Multi-tool**: Add Wikipedia or SerpAPI alongside Tavily
- **Query decomposition**: Break complex questions into sub-queries before searching
- **Human-in-the-loop**: Pause at confidence 5-6 and ask user to continue
- **Vector memory**: Store past research in FAISS, check before hitting the web
- **Multi-agent**: Separate researcher, critic, and writer agents
- **Confidence chart**: Plot confidence trend across iterations with matplotlib

---

## 📄 License

MIT — free to use, modify, and build on.