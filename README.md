# Module 7: LangGraph

This repository contains the hands-on portion of Module 7, a training program for developing AI agents. 
Developed by the AI Hub and TLI at UMN, in partnership with Endogenex, Inspire, and Medtronic.

## Why LangGraph?

Libraries and tools for AI agents are evolving rapidly. LangGraph was selected for this course because:

1) It illustrates the underlying architectural concepts of AI agents.
2) It is widely adopted across the industry as of mid-2026.

Note: LangGraph may not be the ideal framework for every specific use case, and the landscape will continue to shift over the coming years.
Treat this as a foundation for understanding agentic workflows.

## Repository

The training is broken down by sections. Each section corresponds to a specific Git branch:

Branch / Section | Focus | Key Topics
------ | ------ | -----
`section-1-basic` | LangGraph Basics | Interactive Jupyter notebooks; building an email triage and reply agent.
`section-2-scripted` | Productionalizing Code | Moving from notebooks to *.py files; introducing Docker containers and a basic user interface (UI).
`section-3-security` | Agent Security | Implementing human-in-the-loop and security guardrails.
`section-4-memory` | Advanced Memory | Managing context, short/long-term memory, and context compression.
`section-5-tools` | Tools & Reasoning | Tool calling via Model Context Protocol (MCP) and complex reasoning loops.

For sections 2-5 there is an exercise for each branch and an associated `section-#-solution` branch.

Libraries and tools for AI agents are evolving rapidly. LangGraph was selected for this course because:

1) It illustrates the underlying architectural concepts of AI agents.
2) It is widely adopted across the industry as of mid-2026.

Note: LangGraph may not be the ideal framework for every specific use case, and the landscape will continue to shift over the coming years.
Treat this as a foundation for understanding agentic workflows.

## Repository

The training is broken down by sections. Each section corresponds to a specific Git branch:

Branch / Section | Focus | Key Topics
------ | ------ | -----
`section-1-basic` | LangGraph Basics | Interactive Jupyter notebooks; building an email triage and reply agent.
`section-2-scripted` | Productionalizing Code | Moving from notebooks to *.py files; introducing Docker containers and a basic user interface (UI).
`section-3-security` | Agent Security | Implementing human-in-the-loop and security guardrails.
`section-4-memory` | Advanced Memory | Managing context, short/long-term memory, and context compression.
`section-5-tools` | Tools & Reasoning | Tool calling via Model Context Protocol (MCP) and complex reasoning loops.


## Getting Started

### Prerequisites

- Ensure you're using Python 3.11 - 3.13.
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or [pip](https://pypi.org/project/pip/)
- LLM API Key: Groq, Azure OpenAI, or private OpenAI instance (e.g. MedtronicGPT).
- Git (to clone the repo and switch between branches).
- Docker (required for section 2+)
    - What is it? Docker is a tool that packages software into lightweight, isolated containers containing all the necessary code, runtime, and system tools.
    - Why we use it: In Section 2, Docker is used to  spin up the agent's web UI and local services without forcing you to manually configure web servers or deal with environment mismatches.

### Step 1: Clone the Repository

Download this repository and navigate into the project directory:
```bash
# Clone the repo, cd to 'python' directory
git clone git@github.com:amvs/aihub-mod-7.git
cd aihub-mod-7.git
```

### Step 2: Environment Configuration

Create your local environment file from the provided template:

```bash
# Create .env file
cp example.env .env
```

Open the .env file in your text editor and insert your API keys.
- Using Groq? Create an account at the Groq Console and follow their Quickstart Guide to generate a free-tier key.
- Using Corporate Models? If you are using enterprise-provided models (like MedtronicGPT or Azure OpenAI), follow your organization's internal documentation to retrieve your keys and update the model provider/base URL fields in the .env file.
    - Security Reminder: Groq models run in the cloud, not locally. Do not pass sensitive corporate data or proprietary code to these agents during the training.

You will also need to update the `config.yml` file to indicate which model provider you would like to use.

### Step 3: Local Python Setup

Create a virtual environment and install the required dependencies:

```bash
# Create a virtual environment
python -m venv .venv

# Activate the environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows (Command Prompt):
# .venv\Scripts\activate.bat

```

Install the project packages using `uv` (or swap `uv` for standard `pip` if preferred):


```bash
# Install uv if you don't have it
pip install uv

# Synchronize and install dependencies
uv init
uv sync
uv add -r requirements.txt
```

### Step 4: Check LLM Configuration

In order to check that your environment and LLM is configured correctly, you can import the `llm_factory` function from `env_utils.py` and run it.
It should automatically grab API keys and configuration information.
If it fails, please check your API key and endpoints.

```python
from env_utils import llm_factory
llm = llm_factory()
# if llm creation fails, an error message will be printed
```

## Non-Docker Alternatives

If you don't have admin privileges on your laptop and you cannot install Docker Desktop, don't worry.
You can still complete 100% of this course using one of these options:

Because this repository is already built around a standard Python virtual environment, you don't strictly need Docker to run the code or the UI.

- For Section 1: Jupyter Notebooks run entirely inside your local Python virtual environment. No admin rights or Docker needed.
- For Section 2 (The UI): Instead of running the Docker build commands, you can run the application script directly using Python.
    1) Update `config.yml`: change line 2 `url: "http://api:8000"` to `url: "http://localhost:8000"` (referencing `api` only works inside of Docker)
    2) Navigate in your terminal to the `email-agent-app` folder and run: `uvicorn app.main:api --reload` to start the FastAPI server. (If uvicorn is not recognized, try running `python -m uvicorn app.main:api --reload`.)
    3) Open a second terminal, navigate to the `email-agent-app` folder again and start the Streamlit frontend:  `streamlit run frontend/app.py`. Streamlit will automatically launch the UI in your web browser at http://localhost:8501, connected directly to your local backend server.