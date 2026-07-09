import streamlit as st
import requests
import time

# Configuration pointing to your FastAPI backend container/process
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="AetherOS Email Agent Control Center", layout="wide")
st.title("📥 Agent Control Center (Simulated Environment)")

# Initialize session states for tracking things in Streamlit memory
if "processed_emails" not in st.session_state:
    st.session_state.processed_emails = []
if "active_interrupts" not in st.session_state:
    st.session_state.active_interrupts = {} # thread_id -> email data

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Simulation Settings")
    if st.button("🔄 Check for New Emails", type="primary"):
        # 1. Ask FastAPI to pull from email_service.py and ingest into LangGraph
        try:
            response = requests.post(f"{BACKEND_URL}/agent/check-inbox")
            if response.status_code == 200:
                data = response.json()
                st.success(f"Ingested {data.get('new_emails_count', 0)} new emails into the workflow!")
                # Refresh state of pending reviews
                review_resp = requests.get(f"{BACKEND_URL}/agent/pending-reviews")
                st.session_state.active_interrupts = review_resp.json()
            else:
                st.error("Failed to sync with backend.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to FastAPI backend. Is it running?")

    st.write("---")
    st.caption("This dashboard simulates a live workspace. Clicking refresh advances the virtual timeline and surfaces emails waiting for Human-in-the-Loop approval.")

# --- Main Dashboard Split Layout ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Awaiting Human Review")
    if not st.session_state.active_interrupts:
        st.info("No emails require review right now. Splendid!")
    else:
        # Loop through any LangGraph states that hit an `interrupt()`
        for thread_id, payload in list(st.session_state.active_interrupts.items()):
            with st.container(border=True):
                st.markdown(f"**From:** {payload['sender_email']}")
                st.markdown(f"**Subject:** {payload['subject']}")
                st.caption(f"Simulated Arrival: {payload.get('dataset_timestamp', 'Unknown')}")
                
                with st.expander("Show Original Customer Content"):
                    st.text(payload['email_content'])
                
                st.write("---")
                st.markdown("**Proposed Agent Reply:**")
                
                # Allow the human reviewer to modify the draft before approving
                editable_draft = st.text_area(
                    "Edit draft response before sending:", 
                    value=payload['draft_response'], 
                    key=f"draft_{thread_id}", 
                    height=150
                )
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("🟢 Approve & Send", key=f"app_{thread_id}", use_container_width=True):
                        # Resume the specific LangGraph thread via FastAPI
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

with col2:
    st.subheader("System Logs & Execution Activity")
    # This section can hit a backend API to show a history of completed items
    st.info("Logs will populate as you process reviews. Students can keep LangSmith open in another tab to view the live execution traces.")