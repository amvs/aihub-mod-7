# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from app.graph import build_graph 
from uuid import uuid4
import logging
import asyncio
from langgraph.types import Command
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore
from app.email_service import SimulatedEmailService
from datetime import datetime
from pydantic import BaseModel
import uuid
from typing import List, Optional
from app.mcp_client import init_mcp_client, close_mcp_client
from contextlib import asynccontextmanager

# global graph placeholder
graph_app = None
logger = logging.getLogger("uvicorn.error")
email_service = SimulatedEmailService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph_app
    logger.info("Server starting up. Initializing resources...")
    
    # 1. Start the MCP connection
    await init_mcp_client()
    
    # 2. Keep the database connections alive for the entire lifespan of the API
    async with AsyncSqliteSaver.from_conn_string("email_agent_memory.db") as checkpointer, \
               AsyncSqliteStore.from_conn_string("email_agent_memory.db") as store:
               
        # 3. Ensure database schema and tables exist
        await store.setup()
        
        # 4. Compile our graph globally with active persistent memories
        graph_app = build_graph(checkpointer=checkpointer, store=store)
        logger.info("Global Graph compiled successfully with Checkpointer and Store.")
        
        yield  # FastAPI runs and processes API requests here
        
    # 5. Clean up subprocesses and MCP connections on shutdown
    logger.info("Server shutting down. Cleaning up processes...")
    await close_mcp_client()


api = FastAPI(lifespan=lifespan)

# --- In-Memory Trackers ---
PENDING_REVIEWS_DB = {}
COMPLETED_LOGS = []

# Strong references to fire-and-forget check_inbox tasks so they aren't
# garbage-collected mid-execution (see asyncio.create_task docs).
BACKGROUND_TASKS: set[asyncio.Task] = set()


@api.post("/agent/start")
async def start_agent(email: dict):
    thread_id = email.get("thread_id", str(uuid4()))
    initial_state = {
        "email_content": email["email_content"], 
        "sender_email": email["sender_email"], 
        "email_id": f"mail_{uuid.uuid4()}", 
        "timestamp": email.get("dataset_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }

    logger.info(f"Starting pipeline for Thread: {thread_id} ({email['sender_email']})")
    result, state_snapshot = await process_email_with_graph(email_data=initial_state, thread_id=thread_id)
    
    # Case 1: The graph paused for human review
    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
        interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
        PENDING_REVIEWS_DB[thread_id] = interrupt_payload
        logger.info(f"Thread {thread_id} is awaiting Human Review.")
        return {"status": "AWAITING_REVIEW", "thread_id": thread_id}
        
    # Case 2: The graph finished completely
    else:
        # Extract the final values from the state dictionary
        final_state = state_snapshot.values
        security_info = final_state.get("security_analysis") or {}
        
        if security_info.get("risk_level") == "high":
            COMPLETED_LOGS.append({
                "thread_id": thread_id, 
                "action": "Security Escalation (Blocked)", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "color": "orange",
                "details": security_info.get("concerns", "Flagged by security system.")
            })
            logger.warning(f"Thread {thread_id} BLOCKED by security.")
            return {"status": "SECURITY_ESCALATED", "thread_id": thread_id}
            
        # Case 3: It was genuinely safe and cleared automatically
        else:
            COMPLETED_LOGS.append({
                "thread_id": thread_id, 
                "action": "Auto-Processed (No Review Needed)", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "color": "blue"
            })
            logger.info(f"Thread {thread_id} completed automatically.")
            return {"status": "COMPLETED", "thread_id": thread_id}


async def process_email_with_graph(email_data: dict, thread_id: str):
    """
    Invokes the globally compiled, thread-safe graph_app.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Call the globally compiled app directly (no manual DB connections needed here!)
    result = await graph_app.ainvoke(email_data, config=config)
    state_snapshot = await graph_app.aget_state(config)
    
    return result, state_snapshot


@api.get("/agent/pending-reviews")
def get_pending_reviews():
    # Streamlit calls this to populate the dashboard!
    return PENDING_REVIEWS_DB

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    edited_response: str | None = None

@api.post("/agent/approve")
async def approve_agent(req: ApprovalRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    
    # Resume the LangGraph by providing the human input back to the Command
    decision = {"approved": req.approved, "edited_response": req.edited_response}
    
    # Resumes conversation using the globally persistent graph_app
    await graph_app.ainvoke(Command(resume=decision), config)
    
    # Clean up the pending tracker
    if req.thread_id in PENDING_REVIEWS_DB:
        del PENDING_REVIEWS_DB[req.thread_id]
        
    # --- Add to our completed logs ---
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if req.approved:
        COMPLETED_LOGS.append({
            "thread_id": req.thread_id, 
            "action": "Approved & Sent", 
            "timestamp": timestamp,
            "color": "green"
        })
    else:
        COMPLETED_LOGS.append({
            "thread_id": req.thread_id, 
            "action": "Rejected & Escalated", 
            "timestamp": timestamp,
            "color": "red"
        })
        
    return {"status": "COMPLETED"}

# --- endpoint to fetch the logs ---
@api.get("/agent/logs")
def get_logs():
    # Return the last 20 logs so the UI doesn't get overwhelmed if left running
    return COMPLETED_LOGS[-20:]

@api.post("/agent/check-inbox")
async def check_inbox():
    if not hasattr(check_inbox, "processed_ids"):
        check_inbox.processed_ids = []
    
    new_emails = email_service.fetch_new_incoming_emails(check_inbox.processed_ids)
    logger.info(f"Fetched {len(new_emails)} new emails from the dataset.")
    
    # non-blocking, concurrent background tasks
    # This responds to the frontend immediately while executing agents in parallel.
    for email in new_emails:
        task = asyncio.create_task(start_agent(email=email))
        BACKGROUND_TASKS.add(task)
        task.add_done_callback(BACKGROUND_TASKS.discard)
        check_inbox.processed_ids.append(email['email_id'])
    
    return {"new_emails_count": len(new_emails)}

class MessageModel(BaseModel):
    role: str
    content: str
    message_type: str | None = None

class MemoryResponse(BaseModel):
    conversation_summary: Optional[str] = None
    messages: List[MessageModel]


@api.get("/agent/memory/{thread_id}", response_model=MemoryResponse)
async def get_conversation_memory(thread_id: str):
    logger.info(f"Fetching memory for thread_id: {thread_id}")
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Fetch directly using the globally persistent, thread-safe graph snapshot
        state_snapshot = await graph_app.aget_state(config)
    except Exception as e:
        logger.error(f"Failed to query database memory for thread {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    logger.info(f"Successfully fetched state snapshot for thread_id: {thread_id}")
    
    # If the thread has no history yet, return an empty response
    if not state_snapshot or not state_snapshot.values:
        return MemoryResponse(conversation_summary=None, messages=[])
    
    # Extract the data
    conversation_summary = state_snapshot.values.get("conversation_summary")
    raw_messages = state_snapshot.values.get("messages", [])
    
    # Format the LangChain messages using their .type attribute
    formatted_messages = []
    for msg in raw_messages:
        role = getattr(msg, "type", "unknown")
        content = getattr(msg, "content", str(msg))
        metadata = getattr(msg, "metadata", {})
        message_type = metadata.get("type", None)
        formatted_messages.append(MessageModel(role=role, content=content, message_type=message_type))
    
    return MemoryResponse(
        conversation_summary=conversation_summary,
        messages=formatted_messages
    )
