from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from main import PromotionAnalysisSystem
import os
import json
import asyncio

from adls_manager import ADLSManager
from fastapi import HTTPException

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
current_csv_path = None

@app.on_event("startup")
async def startup_event():
    global system, current_csv_path
    
    # Check for file updates from ADLS
    adls = ADLSManager()
    local_path, is_new = adls.sync_latest_file()
    
    # Store globally so other endpoints can use it
    current_csv_path = local_path if local_path else "downloads/part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv"
    
    print(f"Startup: Using CSV file: {current_csv_path}")
    print(f"Startup: New file detected? {is_new}")
    
    # Initialize system (rebuild if new file detected)
    system = PromotionAnalysisSystem(current_csv_path, force_rebuild=is_new)
    system.initialize()

@app.post("/admin/sync-data")
async def manual_sync_trigger():
    """Manual trigger to fetch latest file from ADLS and rebuild index if changed"""
    global system, current_csv_path
    
    try:
        adls = ADLSManager()
        local_path, is_new = adls.sync_latest_file()
        
        if not local_path:
             raise HTTPException(status_code=404, detail="No CSV file found in ADLS or locally.")
             
        if is_new:
            current_csv_path = local_path
            print(f"Manual Sync: New file detected: {current_csv_path}. Rebuilding system...")
            
            # Re-initialize system with force_rebuild=True
            system = PromotionAnalysisSystem(current_csv_path, force_rebuild=True)
            system.initialize()
            
            return {"status": "success", "message": "New file detected and system rebuilt.", "file": current_csv_path}
        else:
            return {"status": "success", "message": "No new file detected. System remains unchanged.", "file": current_csv_path}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/data/csv")
async def get_csv_data():
    """Serve the promotion CSV data for frontend visualizations"""
    global current_csv_path
    csv_path = current_csv_path if current_csv_path else "downloads/part-00000-tid-8397012257644732603-1200992a-2c19-4df8-a301-752e4b275d40-52-1-c000.csv"
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        return Response(content=csv_content, media_type="text/csv")
    except FileNotFoundError:
        return {"error": "CSV file not found"}
    except Exception as e:
        return {"error": str(e)}