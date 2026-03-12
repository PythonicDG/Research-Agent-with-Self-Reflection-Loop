from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from langchain_groq import ChatGroq
from tavily import TavilyClient
import os
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
