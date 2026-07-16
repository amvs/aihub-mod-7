# Exercise Section 2

We found a bug in our agent - it doesn't route rejected emails properly!
When we interrupt for human review, if we 

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


# Exercise: Section 4

Our agent has excellent memory within a conversation, thanks to the SQLite checkpointer.
However, it has no memory across conversations.
If Isiah emails us in a new conversation next week, the agent will start from a blank slate and won't remember the conversation we had this week!

LangGraph has two types of memory, which serve different purposes:
* Thread memory (checkpointer): tracking the messages within a conversation.
* Global memory (store): tracks facts, preferences, and history about entities involved in conversation (like users, organizations, or documents) over time.

Our goal in this exercise is to add a `customer_profiles` table to our existing SQLite database.
You will then teach the agent to look up the sender's history at the beginning of an email, use that history to draft a better response, and update the customer's profile at the end of the interaction.
We only need a little bit of new syntax to create the store:
```python
checkpointer = SqliteSaver(conn) # already have this line
store = SqliteStore(conn)
store.setup() # ensures database tables for the store exist

graph = builder.compile(checkpointer=checkpointer, store=store) # modified version of our current builder.compile line
```

To retrieve from or update the store, we need to call `store.get` or `store.put` respectively.
If we are working inside of a node, make sure that `store` is an argument for the function defining the node.
If we want to track multiple types of entities (e.g. tracking customers and bugs), both are kept in the same global store, but are separated by namespaces:
```python
customer_id = "customer_123"
bug_id = "bug_456"

# retrieve customer info:
customer_namespace = ("customers",)
customer_history = store.get(customer_namespace, customer_id)

all_customer_history = store.search(("customers",), ) # retrieve all customer history, e.g. want to search for partial matches

if customer_history:
    print(f"Customer Name: customer_history.name")

# conversation between customer and agent
# want to update customer record at the end
store.put(customer_namespace,
        "history",
        {customer_history_dict})
```

Add this syntax to our `build_graph` function, and add the following elements to make sure our agent remembers customers across multiple conversations:

1) Create the global store, using the syntax above. Make sure you:
    a) Create a new class to hold structured info about the customer (e.g. how many tickets/emails have they sent in the past?).
    b) Update `EmailAgentState` to include a new key to hold the customer's history.
2) Wire the graph to read and write the customer's history:
    a) Update `read_email` to query the customer's profile using `sender_email`. If a profile exists, load it into the state. You'll need to add a `store` argument to `read_email`.
    b) Update `write_response` to include the customer's history in the context to the LLM while drafting a response.
    c) Update the history. Add a new node before the graph finishes that summarizes the current conversation and updates the profile in the global store.
3) Validate the new customer history is working properly by logging it in Docker.

## Solution

To allow our agent to remember customers across entirely separate threads and conversations, we integrated LangGraph's global **`Store`**. This allows the agent to persist persistent user data (like loyalty tiers, previous interaction counts, and preferences) even when the conversational checkpointer memory starts from scratch.

Here are the key changes we made to implement cross-conversation memory:

### 1. Define the Customer Profile Structure & State
We created a new `TypedDict` to enforce a clean database schema for our customer records, and added a tracking key directly to our `EmailAgentState`[cite: 6]:

```python
class CustomerHistory(TypedDict):
    customer_email: str
    account_tier: Literal["standard", "premium", "vip"]
    num_interactions: int
    last_interaction_date: str | None
    preferred_contact_method: str
    relationship_summary: str

class EmailAgentState(TypedDict):
    # ... other keys
    customer_history: CustomerHistory | None
```

### 2. Retrieve Profiles on Startup (`read_email`)

We updated `read_email` to request the global store. At the start of every email run, the agent queries the namespace ("customer_history",) using the sender's email as the unique key. If no history exists, it safely initializes a blank profile.

```python
def read_email(state: EmailAgentState, store: BaseStore) -> EmailAgentState:
    sender = state['sender_email']
    
    # Query the global store
    profile_item = store.get(namespace=("customer_history",), key=sender)
    
    if profile_item:
        customer_history = profile_item.value
    else:
        # Initialize a fresh profile for a new customer
        customer_history = {
            "customer_email": sender,
            "account_tier": "standard",
            "num_interactions": 0,
            "last_interaction_date": None,
            "preferred_contact_method": "email",
            "relationship_summary": "New customer."
        }
        
    return {"customer_history": customer_history}
```

### 3. Update Profiles at the End of the Run

We created a dedicated `update_customer_history` node. This node takes the current interaction (the inbound email, response, and classification), increments the ticket counter, updates the date, and saves the updated record back to the global SQLite database.

```python
def update_customer_history(state: EmailAgentState, store: BaseStore) -> EmailAgentState:
    sender = state['sender_email']
    customer_history = state.get('customer_history', {})
    
    # Safely increment interaction count
    current_num_tickets = customer_history.get('num_interactions', 0)
    customer_history['num_interactions'] = current_num_tickets + 1
    customer_history['last_interaction_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Save profile back to the global store namespace
    store.put(namespace=("customer_history",), key=sender, value=customer_history)
    return {"customer_history": customer_history}
```

### 4. Wire the Global Store into the Graph

We initialized the `SqliteStore` alongside our checkpointer, passed it directly into our compiled graph, and registered our new node to run right before the graph ends.

```python
def build_graph(checkpointer: SqliteSaver = None, store: SqliteStore = None) -> StateGraph[EmailAgentState]:
    builder = StateGraph(EmailAgentState)

    # Register the nodes
    builder.add_node("read_email", read_email)
    builder.add_node("update_customer_history", update_customer_history)
    # ... other nodes ...

    # Connect final actions to profile saving, then terminate
    builder.add_edge("escalate_ticket", "update_customer_history")
    builder.add_edge("send_reply", "update_customer_history")
    builder.add_edge("update_customer_history", END)

    # Compile the graph binding both the short-term checkpointer and long-term store
    return builder.compile(checkpointer=checkpointer, store=store)
```

# Exercise: Section 5

Right now, the agent only has access to `fetch`.
This means the agent has to be hardcoded with a dictionary of URLs to visit; if a customer asks about a topic not in the dictionary, the agent is stuck.

Therefore, we will add a new tool: MCP's Wikipedia search server.
We can set this up using `npx` or `uvx` using `@modelcontextprotocol/server-wikipedia`.
This will give the agent one additional tool: `search_wikipedia`.
In addition, wire your agent so that it performs a two-step research process:
1) Look up a user's problem using the search tool.
2) Extract the most promising URL from the search results.
3) Pass that URL to the `fetch` tool to read the page and answer the user.


