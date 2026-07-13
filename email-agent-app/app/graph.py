import uuid
from typing import Literal, TypedDict
from langchain_groq import ChatGroq
from langgraph.types import Command, interrupt
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
import yaml
import datetime
import logging

load_dotenv()

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

LLM_TEMPERATURE = config["backend"]["llm"]["temperature"]
LLM_MODEL = config["backend"]["llm"]["model"]

logger = logging.getLogger("uvicorn.error")

class EmailClassification(TypedDict):
    intent: Literal["question", "bug", "billing", "feature", "complex"]
    urgency: Literal["low", "medium", "high", "critical"]
    topic: str
    summary: str

class EmailAgentState(TypedDict):
    # Raw email data
    email_content: str # don't need annotate class or operator.add because we don't need to keep more than one email at a time
    sender_email: str
    email_id: str
    timestamp: str

    # Classification result
    classification: EmailClassification | None

    # Bug tracking
    ticket_id: str | None

    # Raw search results
    search_results: list[str] | None
    customer_history: dict | None

    # Generated content
    draft_response: str | None



def read_email(state: EmailAgentState) -> EmailAgentState:
    """Extract and parse email content"""
    # we will pass email contents directly to agent
    # if we needed to open a file we would do that here
    pass # TODO


def classify_intent(state: EmailAgentState) -> EmailAgentState:
    """Use LLM to classify email intent and urgency, then route accordingly"""
    logger.info('entering classify_intent')

    llm = ChatGroq(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

    # Create structured LLM that returns EmailClassification dict
    structured_llm = llm.with_structured_output(EmailClassification)

    classification_prompt = f"""
    Analyze this customer email and classify it:

    Email: {state['email_content']}
    From: {state['sender_email']}

    Provide classification, including intent, urgency, topic, and summary
    """

    # Get structured response directly as a dict
    classification = structured_llm.invoke(classification_prompt)

    # Store classification as a single dict in state
    return {"classification": classification}

def search_documentation(state: EmailAgentState) -> EmailAgentState:
    """Search knowledge base for relevant information"""
    logger.info('entering search_documentation')
    # Build search query from classification
    classification = state.get('classification', {})
    query = f"{classification.get('intent', '')} {classification.get('topic', '')}"

    try:
        # Implement search logic here
        search_results = [
            "--Search_result_1--",
            "--Search_result_2--",
            "--Search_result_3--"
        ]
    except SearchAPIError as e:
        # For recoverable search errors, store error and continue
        search_results = [f"Search temporarily unavailable: {str[e]}"]

    return {"search_results": search_results} # Raw search results or error

def bug_tracking(state: EmailAgentState) -> EmailAgentState:
    """Create or update bug tracking ticket"""
    logger.info('entering bug_tracking')
    # Create ticket in your bug tracking system
    ticket_id = f"BUG_{uuid.uuid4()}"

    return {"ticket_id": ticket_id}

def write_response(state: EmailAgentState) -> Command[Literal["human_review", "send_reply"]]:
    "Generate response using context and route based on quality"""
    logger.info('entering write_response')
    llm = ChatGroq(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    classification = state.get('classification', {})

    # Format context from raw state data on demand
    context_sections = []

    if state.get('search_results'):
        # Format search results for the prompt
        formatted_docs = "\n".join([f"- {doc}" for doc in state['search_results']])
        context_sections.append(f"Relevant documentation:\n{formatted_docs}")

    if state.get('customer_history'):
        # Format customer data for the prompt
        context_sections.append(f"Customer tier: {state['customer_history'].get('tier', 'standard')}")

    # Build the prompt with formatted context
    draft_prompt = f"""
    Draft a response to this customer email:
    {state['email_content']}

    Email intent: {classification.get('intent', 'unkown')}
    Urgency level: {classification.get('urgency', 'medium')}

    {chr(10).join(context_sections)}

    Guidelines:
    - Be professional and helpful
    - Address their specific concern
    - Use the provided documentation when relevant
    - Be brief
    """

    response = llm.invoke(draft_prompt)
    logger.info(f"Draft response generated in write_response")

    # Determine if human review is needed based on urgency and intent
    needs_review = (
        classification.get('urgency') in ['high', 'critical'] or
        classification.get('intent') == 'complex'
    )

    # Route to the appropriate next node
    if needs_review:
        goto = "human_review"
        print("Needs approval")
    else:
        goto = "send_reply"

    return Command(
        update = {"draft_response": response.content},
        goto = goto
    )

# 1. Update the Literal hint to include your new node
def human_review(state: EmailAgentState) -> Command[Literal["send_reply", "escalate_ticket"]]:
    """Pause for human review using interrupt and route based on decision"""
    logger.info('entering human_review')

    classification = state.get('classification', {})

    logger.info(f"Interrupting for human review: {state['email_id']}")
    
    human_decision = interrupt({
        "email_id": state['email_id'],
        "original_email": state['email_content'],
        "draft_response": state.get('draft_response', ""),
        "urgency": classification.get('urgency'),
        "intent": classification.get('intent'),
        "action": "Please review and approve/edit this response",
        "sender_email": state['sender_email'],
    })

    if human_decision.get("approved"):
        return Command(
            update = {"draft_response": human_decision.get("edited_response", state['draft_response'])},
            goto = "send_reply"
        )
    else:
        # 2. Tell it explicitly to go to the escalation node instead of END
        return Command(update = {}, goto = "escalate_ticket")

def send_reply(state: EmailAgentState) -> EmailAgentState:
    """Send the email response"""
    # Integrate with a email service
    print(f"Sending reply: {state['draft_response'][:60]}...")
    return {}

def route_after_review(state: EmailAgentState):
    """Determines where to go after the human makes a decision."""
    if state["draft_response"] == "ESCALATED_TO_HUMAN":
        return "escalate"
    return "send"

# --- Optional: A node to handle rejections ---
def escalate_ticket(state: EmailAgentState):
    """Handles what happens when an email is rejected by the reviewer."""
    # Here you might update a database, tag the ticket as 'Needs Manual Support', etc.
    logger.info(f"Ticket {state['email_id']} was escalated and will NOT be emailed by the agent.")
    print(f"Ticket {state['email_id']} was escalated and will NOT be emailed by the agent.")
    return state

def build_graph():
    logger.info("Building LangGraph state machine for Email Agent")
    builder = StateGraph(EmailAgentState)

    # Add nodes
    builder.add_node("read_email", read_email)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("search_documentation", search_documentation)
    builder.add_node("bug_tracking", bug_tracking)
    builder.add_node("write_response", write_response)
    builder.add_node("human_review", human_review)
    builder.add_node("send_reply", send_reply)
    builder.add_node("escalate_ticket", escalate_ticket)
    
    # Add standard edges
    builder.add_edge(START, "read_email")
    builder.add_edge("read_email", "classify_intent")
    builder.add_edge("classify_intent", "search_documentation")
    builder.add_edge("classify_intent", "bug_tracking")
    builder.add_edge("search_documentation", "write_response")
    builder.add_edge("bug_tracking", "write_response")
    
    # Notice we don't add an edge OUT of human_review or write_response here. 
    # The `Command(goto=...)` handles it for us!
    
    # Ensure the final nodes connect to END
    builder.add_edge("escalate_ticket", END)
    builder.add_edge("send_reply", END)

    memory = InMemorySaver()
    app = builder.compile(checkpointer = memory)
    # TODO - add thread id for email threads - stored in dataset as column thread_id
    return app

