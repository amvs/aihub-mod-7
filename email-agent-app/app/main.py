from fastapi import FastAPI
from app.graph import build_graph # Your compiled LangGraph app
from uuid import uuid4

api = FastAPI()
graph_app = build_graph()

@api.post("/agent/start")
def start_agent(email_content: str, sender: str):
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {"email_content": email_content, "sender_email": sender, "email_id": f"mail_{thread_id}"}
    
    result = graph_app.invoke(initial_state, config)
    
    # If it hit an interrupt, return the snapshot state so the front-end can display it
    if "__interrupt__" in result.keys():
        return {"status": "AWAITING_REVIEW", "thread_id": thread_id, "data": result}
    return {"status": "COMPLETED", "thread_id": thread_id}

@api.post("/agent/approve")
def approve_agent(thread_id: str, approved: bool, edited_response: str = None):
    config = {"configurable": {"thread_id": thread_id}}
    # Resume the LangGraph by providing the human input back to the Command
    decision = {"approved": approved, "edited_response": edited_response}
    
    result = graph_app.invoke(decision, config)
    return {"status": "COMPLETED"}

@api.get("/agent/pending-reviews")
def get_pending_reviews():
    # return dictionary of active interrupts
    return graph_app.get_active_interrupts()

@api.post("/agent/check-inbox")
def check_inbox():
    from app.email_service import SimulatedEmailService
    email_service = SimulatedEmailService()
    
    # Track processed email IDs in memory for this example
    if not hasattr(check_inbox, "processed_ids"):
        check_inbox.processed_ids = []
    
    new_emails = email_service.fetch_new_incoming_emails(check_inbox.processed_ids)
    
    for email in new_emails:
        # Start a new LangGraph thread for each new email
        start_agent(email_content=email['email_content'], sender=email['sender_email'])
        check_inbox.processed_ids.append(email['email_id'])
    
    return {"new_emails_count": len(new_emails)}