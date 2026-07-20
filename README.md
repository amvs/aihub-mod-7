# Module 7: LangGraph

This repository contains the hands-on portion of Module 7, a training for developing AI agents developed by the AI Hub and TLI at UMN, in partnership with Endogenex, Inspire, and Medtronic.
The repository focuses on LangGraph, an open source framework for developing AI agents.
Libraries and tools for AI agents are changing quickly, and LangGraph was chosen for this tool because 1) it can illustrate many of the underlying concepts in developing AI agents and 2) it is widely used as of mid 2026.
LangGraph is likely not the best framework for every use case and may not be the best framework two years from now.

The repository is organized so that branches contain different sections of the training.
The sections are:
* `section-1-basic`: contains Jupyter notebooks exploring LangGraph basics in an interactive setting and establishing a framework for an agent that triages and replies to emails.
* `section-2-scripted`: moves code from Jupyter notebooks into *.py files that can be put into production; also includes docker container and basic UI for interacting with agent.
* `section-3-security`: adds security checks to the agent.
* `section-4-memory`: adds more advanced memory management and context compression.
* `section-5-tools`: adds tool calling through MCP, and reasoning loops.

For sections 2-5 there is an exercise for each branch and an associated `section-#-solution` branch.

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

Insert API key(s) directly into .env file. Also update the model provider and the base URL for the model if you are using a company-specific model.

This tutorial was developed using API keys from Groq, which as of July 2026 has a free tier with a relatively high limit on the number of requests/tokens.
To get an API key for Groq, you will need to [create an account](https://console.groq.com/login) and follow instructions on [getting started/creating an API key](https://console.groq.com/docs/quickstart).

If your employer will be providing access to a model that they subscribe to, please look for instructions from them on obtaining an API key.
This tutorial is set up to work with OpenAI models hosted on MedtronicGPT and OpenAI models hosted on Azure.

Make a virtual environment and install dependencies from `requirements.txt` file.
You can use pip instead of uv if you prefer.

To create a new venv, run:

```bash
# create venv
# can specify python version, e.g. python3.11 -m venv .venv
python -m venv .venv
# activate the env
source .venv/bin/activate
```

Now we can install the packages we need. If `uv` is not installed, you can run `pip install uv` to install it.


```bash
# set up uv and install dependencies
uv init
uv sync
uv add -r requirements.txt
```

## Starting Agent UI

After section 1, we convert the interactive email agent we built in a Jupyter notebook to one that runs in a Docker container with a Streamlit frontend and FastAPI backend.
In order to start this container, make sure Docker is installed and running on your computer, and run:

```bash
docker compose up --build
```

To shut down a container, press the `Stop` button in the Docker GUI or run `docker compose stop` to pause your containers or `docker compose down` to stop and clean them up (you will have to rebuild them the next time you start the container).