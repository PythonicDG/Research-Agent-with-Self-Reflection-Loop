from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import json
from pydantic import BaseModel
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from fastapi.responses import HTMLResponse
from langchain_groq import ChatGroq
from tavily import TavilyClient
import os
import re
from dotenv import load_dotenv

load_dotenv()


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

groq_api_key = os.getenv("api_key")
tavily_api_key = os.getenv("tavily_api")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=groq_api_key
)

tavily = TavilyClient(api_key=tavily_api_key)


# ── STATE ────────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    query:              str
    planned_queries:    List[str]
    search_results:     List[str]
    critiques:          List[str]
    confidence_score:   int
    iteration_count:    int
    final_report:       str
    validation_notes:   str             
    is_valid:           bool            


def planner_node(state: AgentState) -> AgentState:
    prompt = f"""You are a research planner.

User question: {state["query"]}

Break this into 2-3 focused search queries that together will fully answer the question.
Also identify the core intent in one sentence.

Respond in this exact JSON format only, no extra text:
{{"intent": "what the user really wants to know", "sub_queries": ["query 1", "query 2", "query 3"]}}"""

    response = llm.invoke(prompt)

    match = re.search(r'\{.*\}', response.content, re.DOTALL)
    parsed = json.loads(match.group())

    return {
        **state,
        "planned_queries":  parsed.get("sub_queries", [state["query"]]),
        "search_results":   [],
        "critiques":        [],
        "confidence_score": 0,
        "iteration_count":  0,
        "final_report":     "",
        "validation_notes": "",
        "is_valid":         False,
    }


def search_node(state: AgentState) -> AgentState:
    planned   = state.get("planned_queries", [state["query"]])
    iteration = state["iteration_count"]

    base_query = planned[min(iteration, len(planned) - 1)]

    if iteration > 0 and state["critiques"]:
        short_critique = state["critiques"][-1][:100]
        search_query   = base_query + " " + short_critique
    else:
        search_query = base_query

    results     = tavily.search(search_query, max_results=3)
    new_results = [r["content"] for r in results["results"]]

    return {
        **state,
        "search_results":  state["search_results"] + new_results,
        "iteration_count": state["iteration_count"] + 1,
    }


def reflect_node(state: AgentState) -> AgentState:
    all_results = "\n\n".join(state["search_results"])

    prompt = f"""
You are a research critic.

Original question: {state["query"]}

Search results so far:
{all_results}

Previous critiques: {state["critiques"]}

Your job:
1. Critique what is missing or unclear in the search results
2. Rate confidence 1-10 that we have enough to write a complete answer

Respond in this exact JSON format only, no extra text:
{{"critique": "your critique here", "confidence": 7}}
"""
    response = llm.invoke(prompt)

    match  = re.search(r'\{.*\}', response.content, re.DOTALL)
    parsed = json.loads(match.group())

    return {
        **state,
        "critiques":        state["critiques"] + [parsed["critique"]],
        "confidence_score": parsed["confidence"],
    }


def router(state: AgentState) -> str:
    if state["confidence_score"] >= 7 or state["iteration_count"] >= 3:
        return "write"
    return "search"


def write_report_node(state: AgentState) -> AgentState:
    all_results   = "\n\n".join(state["search_results"])
    all_critiques = "\n".join(state["critiques"])

    prompt = f"""
You are a research report writer.

Original question: {state["query"]}

Research collected:
{all_results}

Research critiques made during process:
{all_critiques}

Write a final research report with this exact structure:

SUMMARY:
- bullet point 1
- bullet point 2
- bullet point 3

KEY FINDINGS:
- finding 1
- finding 2
- finding 3

SOURCES USED:
- source 1
- source 2
"""
    response = llm.invoke(prompt)
    return {**state, "final_report": response.content}


def validator_node(state: AgentState) -> AgentState:
    prompt = f"""You are a strict research quality validator.

Original question asked by the user:
{state["query"]}

Report written by the research agent:
{state["final_report"]}

Your job:
1. Check if the report fully and directly answers the original question
2. Identify any unsupported claims or missing sections
3. Check structure: SUMMARY, KEY FINDINGS, SOURCES USED must all be present

Respond in this exact JSON format only, no extra text:
{{"is_valid": true, "feedback": "brief quality note here"}}

is_valid = true means report is good to deliver.
is_valid = false means there are issues (describe them in feedback)."""

    response = llm.invoke(prompt)

    match  = re.search(r'\{.*\}', response.content, re.DOTALL)
    parsed = json.loads(match.group())

    is_valid = bool(parsed.get("is_valid", True))
    feedback = parsed.get("feedback", "")

    final_report = state["final_report"]
    if not is_valid:
        final_report += f"\n\n---\n⚠️ Validator Note: {feedback}"

    return {
        **state,
        "final_report":     final_report,
        "validation_notes": feedback,
        "is_valid":         is_valid,
    }

#graph
graph = StateGraph(AgentState)

graph.add_node("planner",   planner_node)
graph.add_node("search",    search_node)
graph.add_node("reflect",   reflect_node)
graph.add_node("write",     write_report_node)
graph.add_node("validator", validator_node)

graph.set_entry_point("planner")

graph.add_edge("planner",   "search")
graph.add_edge("search",    "reflect")
graph.add_conditional_edges("reflect", router, {"search": "search", "write": "write"})
graph.add_edge("write",     "validator")
graph.add_edge("validator", END)

agent_app = graph.compile()

#api's
class QueryRequest(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/research")
async def run_research(req: QueryRequest):
    def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': '🧠 Planning research strategy…'})}\n\n"

        initial_state = {
            "query":            req.query,
            "planned_queries":  [],
            "search_results":   [],
            "critiques":        [],
            "confidence_score": 0,
            "iteration_count":  0,
            "final_report":     "",
            "validation_notes": "",
            "is_valid":         False,
        }

        for step in agent_app.stream(initial_state):
            node_name = list(step.keys())[0]
            state     = step[node_name]

            if node_name == "planner":
                queries = state.get("planned_queries", [])
                msg     = f"🧠 Research plan ready — {len(queries)} sub-queries identified"
                yield f"data: {json.dumps({'type': 'plan', 'message': msg, 'sub_queries': queries})}\n\n"

            elif node_name == "search":
                msg = f"🔎 Search #{state['iteration_count']} complete — {len(state['search_results'])} results gathered"
                yield f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"

            elif node_name == "reflect":
                critique = state["critiques"][-1] if state["critiques"] else ""
                msg      = f"🤔 Reflecting… confidence {state['confidence_score']}/10"
                yield f"data: {json.dumps({'type': 'reflect', 'message': msg, 'critique': critique, 'confidence': state['confidence_score']})}\n\n"

            elif node_name == "write":
                yield f"data: {json.dumps({'type': 'status', 'message': '✍️ Writing final report…'})}\n\n"

            elif node_name == "validator":
                is_valid = state["is_valid"]
                feedback = state["validation_notes"]
                msg      = f"✅ Validation {'passed' if is_valid else 'flagged issues'}"
                yield f"data: {json.dumps({'type': 'report', 'report': state['final_report'], 'loops': state['iteration_count'], 'confidence': state['confidence_score'], 'critiques': state['critiques'], 'is_valid': is_valid, 'validation_feedback': feedback, 'message': msg})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")