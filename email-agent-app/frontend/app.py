import streamlit as st
import requests
import time
import yaml

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

BACKEND_URL = config["backend"]["url"]

st.set_page_config(page_title="AetherOS Email Agent Control Center", layout="wide")
st.title("📥 Agent Control Center (Simulated Environment)")

def display_memory(thread_id):
    with st.expander("View Agent Memory & Context", expanded=False):
        try:
            mem_response = requests.get(f"{BACKEND_URL}/agent/memory/{thread_id}")
            if mem_response.status_code == 200:
                memory_data = mem_response.json()
                summary = memory_data.get("conversation_summary")
                messages = memory_data.get("messages", [])
                
                st.markdown("### Summary")
                if summary:
                    st.info(summary)
                else:
                    st.caption("No summary generated yet. (Threshold not reached)")
                    
                st.divider()
                st.markdown("### 💬 Raw Message Array")
                if not messages:
                    st.caption("No messages in memory for this thread.")
                else:
                    for msg in messages:
                        role = msg.get("role", "unknown")
                        avatar_role = "user" if role == "human" else "assistant" if role == "ai" else "secondary"
                        with st.chat_message(name=avatar_role):
                            st.caption(f"**Type:** {role}, **Message Type**: {msg.get('message_type', 'N/A')}")
                            st.write(msg.get("content", ""))
            else:
                st.error(f"Failed to load memory. Status: {mem_response.status_code}")
        except requests.exceptions.RequestException:
            st.error("Could not connect to the backend API to fetch memory.")

# Initialize session states for tracking things in Streamlit memory
if "processed_emails" not in st.session_state:
    st.session_state.processed_emails = []
if "active_interrupts" not in st.session_state:
    st.session_state.active_interrupts = {} # thread_id -> email data

try:
    review_resp = requests.get(f"{BACKEND_URL}/agent/pending-reviews")
    if review_resp.status_code == 200:
        st.session_state.active_interrupts = review_resp.json()
    else:
        st.session_state.active_interrupts = {}
except requests.exceptions.ConnectionError:
    st.session_state.active_interrupts = {}

# --- Sidebar Controls ---
with st.sidebar:
    st.subheader("📊 System Logs & Execution Activity")
    
    # Add a small manual refresh button for the logs
    if st.button("🔄 Refresh Logs", use_container_width=True):
        st.rerun()
        
    # Fetch logs from the backend
    try:
        logs_response = requests.get(f"{BACKEND_URL}/agent/logs")
        if logs_response.status_code == 200:
            logs = logs_response.json()
            
            if not logs:
                st.info("No completed actions yet. Process an email to see logs!")
            else:
                # Display logs in reverse order (newest at the top)
                for log in reversed(logs):
                    with st.container(border=True):
                        
                        color = log.get("color", "gray")
                        
                        # Map our custom log colors to Streamlit's native alert boxes
                        if color == "green":
                            st.success(f"**{log['action']}**")
                        elif color == "red":
                            st.error(f"**{log['action']}**")
                        elif color == "orange":
                            st.warning(f"**{log['action']}**")
                        elif color == "blue":
                            st.info(f"**{log['action']}**")
                        else:
                            st.write(f"**{log['action']}**")
                            
                        # If the security node added a reason for blocking, display it!
                        if "details" in log:
                            with st.expander("View Details"):
                                st.markdown(f"**Reason:** {log['details']}")
                        display_memory(thread_id=log['thread_id'])  # Show memory for this thread if available
                            
                        st.caption(f"Time: {log['timestamp']} | Thread ID: {log['thread_id'][:8]}...")
        else:
            st.warning("Could not fetch logs from backend.")
    except requests.exceptions.ConnectionError:
        st.error("Backend disconnected.")

# --- Main Dashboard Split Layout ---
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Update Inbox")
    if st.button("🔄 Check for New Emails", type="primary"):
        try:
            response = requests.post(f"{BACKEND_URL}/agent/check-inbox")
            if response.status_code == 200:
                data = response.json()
                st.success(f"Ingested {data.get('new_emails_count', 0)} new emails into the workflow!")
                review_resp = requests.get(f"{BACKEND_URL}/agent/pending-reviews")
                st.session_state.active_interrupts = review_resp.json()
            else:
                st.error("Failed to sync with backend.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to FastAPI backend. Is it running?")

    st.write("---")
    st.caption("This dashboard simulates a live workspace. Clicking refresh advances the virtual timeline and surfaces emails waiting for Human-in-the-Loop approval.")

with col2:
    st.subheader("Awaiting Human Review")
    if not st.session_state.active_interrupts:
        st.info("No emails require review right now. Splendid!")
    else:
        # Loop through any LangGraph states that hit an `interrupt()`
        for thread_id, payload in list(st.session_state.active_interrupts.items()):
            with st.container(border=True):
                st.markdown(f"**From:** {payload['sender_email']}")
                st.caption(f"Simulated Arrival: {payload.get('dataset_timestamp', 'Unknown')}, Urgency: {payload.get('urgency', 'Unknown')}, Intent: {payload.get('intent', 'Unknown')}")
                
                with st.expander("Show Original Customer Content"):
                    st.text(payload['original_email'])
                
                display_memory(thread_id=thread_id)
                # --------------------------------
                
                st.write("---")
                st.markdown("**Proposed Agent Reply:**")
                
                editable_draft = st.text_area(
                    "Edit draft response before sending:", 
                    value=payload['draft_response'], 
                    key=f"draft_{thread_id}", 
                    height=150
                )
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("🟢 Approve & Send", key=f"app_{thread_id}", use_container_width=True):
                        res = requests.post(f"{BACKEND_URL}/agent/approve", json={
                            "thread_id": thread_id,
                            "approved": True,
                            "edited_response": editable_draft
                        })
                        if res.status_code == 200:
                            st.toast("Email approved and sent!")
                            del st.session_state.active_interrupts[thread_id]
                            st.rerun()
                with btn_col2:
                    if st.button("🔴 Reject / Escalate", key=f"rej_{thread_id}", use_container_width=True):
                        res = requests.post(f"{BACKEND_URL}/agent/approve", json={
                            "thread_id": thread_id,
                            "approved": False,
                            "edited_response": ""
                        })
                        if res.status_code == 200:
                            st.toast("Escalated to Tier 2 support.")
                            del st.session_state.active_interrupts[thread_id]
                            st.rerun()