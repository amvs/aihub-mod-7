# Module 7: LangGraph

This repository contains the hands-on portion of Module 7, a training for developing AI agents developed by the AI Hub and TLI at UMN, in partnership with Endogenex, Inspire, and Medtronic.
The repository focuses on LangGraph, a popular open source 

The repository is organized so that branches contain different sections of the training.
The sections are:
* `section-1-basic`: contains Jupyter notebooks exploring LangGraph basics in an interactive setting and establishing a framework for an agent that triages and replies to emails.
* `section-2-production`: moves code from Jupyter notebooks into `*.py` files that can be put into production; also includes docker container and basic UI for interacting with agent.
* `section-3-reasoning`: adds reasoning loops to agent.
* `section-4-mcp`: adds tool calls through MCP.
* `section-5-memory`: adds more advanced memory management and context compression.


## Getting Started

### Prerequisites

- Ensure you're using Python 3.11 - 3.13.
- [uv](https://docs.astral.sh/uv/) package manager or [pip](https://pypi.org/project/pip/)
- API key for LLM (OpenAI, Anthropic, etc.)
    - LangGraph is model-agnostic and it is straightforward to swap out a different model/provider.
    - The tutorial will use Groq, which provides free access to open-source models. These models are **not** being run locally and **no sensitive information** should be shared with these agents.


Download this repository:
```bash
# Clone the repo, cd to 'python' directory
git clone git@github.com:amvs/aihub-mod-7.git
cd aihub-mod-7.git
```

Make a copy of example.env

```bash
# Create .env file
cp example.env .env
```

Insert API key(s) directly into .env file

Make a virtual environment and install dependencies from `requirements.txt` file.
You can use pip instead of uv if you prefer.
```bash
# Create virtual environment and install dependencies
uv sync
```
