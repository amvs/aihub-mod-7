from fastapi import FastAPI
from app.graph import build_graph 
from uuid import uuid4
import logging
from langgraph.types import Command

api = FastAPI()
graph_app = build_graph()
logger = logging.getLogger("uvicorn.error")

# --- NEW: In-Memory Tracker for the Workshop ---
# This will store thread_id -> interrupt payload
PENDING_REVIEWS_DB = {} 

@api.post("/agent/start")
def start_agent(email_content: str, sender: str):
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {"email_content": email_content, "sender_email": sender, "email_id": f"mail_{thread_id}"}
    
    # Run the graph until it finishes OR hits an interrupt
    graph_app.invoke(initial_state, config)
    
    # --- NEW: Correct way to check for LangGraph Interrupts ---
    # We inspect the current state of the thread we just ran
    state_snapshot = graph_app.get_state(config)
    
    # If the graph has pending tasks with interrupts, it means it paused!
    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
        # Extract the payload we passed into interrupt({...}) in graph.py
        interrupt_payload = state_snapshot.tasks[0].interrupts[0].value
        
        # Save it to our tracker so the frontend can find it
        PENDING_REVIEWS_DB[thread_id] = interrupt_payload
        
        return {"status": "AWAITING_REVIEW", "thread_id": thread_id}
        
    return {"status": "COMPLETED", "thread_id": thread_id}

@api.get("/agent/pending-reviews")
def get_pending_reviews():
    # Streamlit calls this to populate the dashboard!
    return PENDING_REVIEWS_DB

@api.post("/agent/approve")
def approve_agent(thread_id: str, approved: bool, edited_response: str = None):
    config = {"configurable": {"thread_id": thread_id}}
    
    # Resume the LangGraph by providing the human input back to the Command
    decision = {"approved": approved, "edited_response": edited_response}
    graph_app.invoke(Command(resume=decision), config)
    
    # --- NEW: Clean up the tracker ---
    # Now that the human handled it, remove it from the pending UI list
    if thread_id in PENDING_REVIEWS_DB:
        del PENDING_REVIEWS_DB[thread_id]
        
    return {"status": "COMPLETED"}

@api.post("/agent/check-inbox")
def check_inbox():
    logger.error("Checking inbox for new emails...")
    from app.email_service import SimulatedEmailService
    email_service = SimulatedEmailService()
    
    if not hasattr(check_inbox, "processed_ids"):
        check_inbox.processed_ids = []
    
    new_emails = email_service.fetch_new_incoming_emails(check_inbox.processed_ids)
    
    for email in new_emails:
        start_agent(email_content=email['email_content'], sender=email['sender_email'])
        check_inbox.processed_ids.append(email['email_id'])
    
    return {"new_emails_count": len(new_emails)}