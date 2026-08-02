# Exercise

We found a bug in our agent - it doesn't route rejected emails properly!
When we interrupt for human review, if we reject the response, the agent still sends it anyway instead of escalating to a human.

A solution can be found on the `section-2-solution` branch; spend a few minutes writing your own solution before switching branches to check out the official solution.

# Solution

We fixed this by building an "off-ramp" for rejected emails.
We added a new node specifically for escalations and used LangGraph's `Command` object to dynamically route the graph based on the human's choice.

### 1. Create the Escalation Node
We added a new node to flag the ticket for manual support instead of integrating with an email service.

```python
def escalate_ticket(state: EmailAgentState):
    logger.info(f"Ticket {state.get('email_id')} escalated to human support.")
    return {"draft_response": "ESCALATED_TO_HUMAN"}
```

### 2. Update the Command Type Hint

We updated the `human_review` signature so LangGraph knows `escalate_ticket` is a valid routing destination.

```python
def human_review(state: EmailAgentState) -> Command[Literal["send_reply", "escalate_ticket"]]:
```

### 3. Route Dynamically with Command

Inside 'human_review', we evaluate the human's decision and steer the graph to the correct node using 'goto'.

```python
if human_decision.get("approved"):
        return Command(
            update={"draft_response": human_decision.get("edited_response", state['draft_response'])},
            goto="send_reply"
        )
    else:
        # Human rejected! Route to the off-ramp.
        return Command(update={}, goto="escalate_ticket")
```

### 4. Wiring New Connections

In 'build_graph', we added the new node and connected both possible endpoints to 'END'. No static edge out of 'human_review' is needed because the Command object dictates the next step dynamically.

```python
builder.add_node("escalate_ticket", escalate_ticket)
    
    # Both paths safely terminate the graph
    builder.add_edge("escalate_ticket", END)
    builder.add_edge("send_reply", END)
```