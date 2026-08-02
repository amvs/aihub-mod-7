# Exercise Section 2

We found a bug in our agent - it doesn't route rejected emails properly!
When we interrupt for human review, if we reject the response, the agent still sends it anyway instead of escalating to a human.

A solution can be found on the `section-2-solution` branch; spend a few minutes writing your own solution before switching branches to check out the official solution.

## Solution

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


# Exercise: Section 3

We added a `security_check` node to our graph to check whether an incoming email is attempting a cyberattack, before passing it on to the rest of our graph.
This is a good practice for any input to your agent that you do not control; the `security_check` node should have very limited access to tools, files, etc.

However, right now our `security_check` node is fragile, becasue we do a simple string match between the LLM output and "high security risk." 
What if the LLM instead calls it "high risk"? Our `security_check` will fail and will write a response to the email without flagging it!

Luckily, we can require the LLM to give us a structured output.
We already do this in the `classify_intent` node, calling `llm.with_structured_output(EmailClassification)`.

Set up a class to store the security analysis output.
It should have a `risk` attribute with levels low, medium, or high.
Then modify `security_check` to use this structured output.
Depending on the structure of your class, you may need to update the front end to work with the new class instead of the raw LLM output.

## Solution:

To make our `security_check` node robust against unpredictable LLM responses, we switched from simple string matching to enforced structured outputs using LangChain's `with_structured_output` method.

Here are the key changes we made:

### 1. Define the Expected Structure
First, we created a new `TypedDict` to strictly define the exact shape and acceptable values we want the LLM to return. We restricted the risk levels using a `Literal` type hint:

```python
class EmailSecurityAnalysis(TypedDict):
    risk_level: Literal["low", "medium", "high"]
    concerns: str
    recommended_action: str
```

### 2. Update the State Dictionary

We then updated our main `EmailAgentState` so that it expects this new structured dictionary rather than a raw string:

```python
class EmailAgentState(TypedDict):
    # ... other state keys
    security_analysis: EmailSecurityAnalysis | None
```

### 3. Implement in the Security Node

Inside the `security_check` function, we bound the new structure to our LLM before invoking it.
This guarantees the output will be a dictionary with a `risk_level` key.
Finally, we update our routing logic to check this specific key rather than searching for substrings:

```python
def security_check(state: EmailAgentState) -> Command[Literal["classify_intent", "escalate_ticket"]]:
    # ... setup llm and prompt ...
    
    # 1. Bind the structured output format
    security_analysis = llm.with_structured_output(EmailSecurityAnalysis).invoke(security_prompt)

    # 2. Safely check the exact key instead of guessing the string format
    if security_analysis['risk_level'] == 'high':
        return Command(update={"security_analysis": security_analysis}, goto="escalate_ticket")
    
    return Command(update={"security_analysis": security_analysis}, goto="classify_intent")
```