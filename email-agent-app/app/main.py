from fastapi import FastAPI
from fastapi import APIRouter, HTTPException
from app.graph import build_graph 
from uuid import uuid4
import logging
from langgraph.types import Command
from app.email_service import SimulatedEmailService
from datetime import datetime
from pydantic import BaseModel
import uuid
from typing import List, Optional

api = FastAPI()
graph_app = build_graph()
logger = logging.getLogger("uvicorn.error")
email_service = SimulatedEmailService()


# --- NEW: In-Memory Tracker for the Workshop ---
# This will store thread_id -> interrupt payload
PENDING_REVIEWS_DB = {} 
COMPLETED_LOGS = [] 


@api.post("/agent/start")
def start_agent(email: dict):
    thread_id = email.get("thread_id", str(uuid4()))
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "email_content": email["email_content"], 
        "sender_email": email["sender_email"], 
        "email_id": f"mail_{uuid.uuid4()}", 
        "timestamp": email.get("dataset_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }
    
    graph_app.invoke(initial_state, config)
    state_snapshot = graph_app.get_state(config)
    
    # Case 1: The graph paused for human review
    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
        interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
        PENDING_REVIEWS_DB[thread_id] = interrupt_payload
        return {"status": "AWAITING_REVIEW", "thread_id": thread_id}
        
    # Case 2: The graph finished completely
    else:
        # Extract the final values from the state dictionary
        final_state = state_snapshot.values
        security_info = final_state.get("security_analysis") or {}
        
        # Check if the security node flagged this as high risk
        if security_info.get("risk_level") == "high":
            COMPLETED_LOGS.append({
                "thread_id": thread_id, 
                "action": "Security Escalation (Blocked)", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "color": "orange",
                "details": security_info.get("concerns", "Flagged by security system.")
            })
            return {"status": "SECURITY_ESCALATED", "thread_id": thread_id}
            
        # Case 3: It was genuinely safe and cleared automatically
        else:
            COMPLETED_LOGS.append({
                "thread_id": thread_id, 
                "action": "Auto-Processed (No Review Needed)", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "color": "blue"
            })
            return {"status": "COMPLETED", "thread_id": thread_id}

@api.get("/agent/pending-reviews")
def get_pending_reviews():
    # Streamlit calls this to populate the dashboard!
    return PENDING_REVIEWS_DB

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    edited_response: str | None = None

@api.post("/agent/approve")
def approve_agent(req: ApprovalRequest): # <-- Accept the Pydantic model
    config = {"configurable": {"thread_id": req.thread_id}}
    
    # Resume the LangGraph by providing the human input back to the Command
    decision = {"approved": req.approved, "edited_response": req.edited_response}
    
    from langgraph.types import Command
    graph_app.invoke(Command(resume=decision), config)
    
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

# --- NEW: Endpoint to fetch the logs ---
@api.get("/agent/logs")
def get_logs():
    # Return the last 20 logs so the UI doesn't get overwhelmed if left running
    return COMPLETED_LOGS[-20:]

@api.post("/agent/check-inbox")
def check_inbox():
    if not hasattr(check_inbox, "processed_ids"):
        check_inbox.processed_ids = []
    
    new_emails = email_service.fetch_new_incoming_emails(check_inbox.processed_ids)
    logging.info(f"Fetched {len(new_emails)} new emails from the dataset.")
    for email in new_emails:
        start_agent(email=email)
        check_inbox.processed_ids.append(email['email_id'])
    
    return {"new_emails_count": len(new_emails)}

class MessageModel(BaseModel):
    role: str
    content: str
    message_type: str | None = None

class MemoryResponse(BaseModel):
    conversation_summary: Optional[str] = None
    messages: List[MessageModel]

# --- API Endpoint ---
@api.get("/agent/memory/{thread_id}", response_model=MemoryResponse)
def get_conversation_memory(thread_id: str):
    logger.info(f"Fetching memory for thread_id: {thread_id}")
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        state_snapshot = graph_app.get_state(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
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