from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from main import PromotionAnalysisSystem
import os
import json
import asyncio

app = FastAPI()

# Add CORS middleware - ADD THIS SECTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

class QueryRequest(BaseModel):
    question: str

system = None

@app.on_event("startup")
async def startup_event():
    global system
    csv_path = "downloads/part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv"
    system = PromotionAnalysisSystem(csv_path, force_rebuild=False)
    system.initialize()

@app.post("/query")
async def ask_agent(request: QueryRequest):
    result = system.query(request.question)
    return {"answer": result["output"]}

@app.post("/query/stream")
async def ask_agent_stream(request: QueryRequest):
    """Streaming endpoint for real-time responses"""
    async def generate():
        try:
            async for event in system.agent.query_stream(request.question):
                # Format as Server-Sent Events
                data = json.dumps(event)
                yield f"data: {data}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )