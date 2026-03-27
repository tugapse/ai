# Agent System Documentation

This document provides an overview of the agent system, how to use it in your code, and how to interact with it from the command line.

## How the Agent System Works

The agent system is designed as a pipeline of autonomous agents orchestrated by a central `MessageOrchestrator`. The behavior and structure of the pipeline are defined in a JSON configuration file.

### 1. Pipeline Configuration

The core of the system is a JSON pipeline configuration file (e.g., `pipelines/pipeline.json`). This file defines:

- **Agents:** A set of agents, each with a specific role, a system prompt (defining its personality and capabilities), and a list of tools it can use.
- **Pipeline Flow:** The entry point for the pipeline (which agent starts first) and the maximum number of iterations the orchestrator should run.
- **Transitions:** Agents can transition to other agents, creating complex workflows.

### 2. Message Orchestrator

The `MessageOrchestrator` is the brain of the agent system. It is responsible for:

- **Initialization:** Reading the pipeline configuration and setting up the agents.
- **State Management:** Maintaining the global state of the task, including the plan, tool results, and conversation history.
- **Agent Execution:** Running the main loop that activates agents in sequence.
- **Communication:** Facilitating message passing between agents.

### 3. The Agent Interaction Loop

The orchestrator executes a loop that represents the agentic workflow. In each iteration:

1.  The current agent is selected.
2.  A payload is constructed containing the current task, context, history, and any incoming messages.
3.  This payload is sent to the agent's underlying Large Language Model (LLM) via the `LLMConnector`.

### 4. LLM Connector

The `LLMConnector` is responsible for communicating with the LLM. It:

- Takes the payload from the orchestrator.
- Reads the agent's specific system prompt from a file.
- Injects dynamic constraints into the prompt, such as the list of available tools and the allowed agent transitions.
- Sends the final prompt to the LLM and returns the response.

### 5. Agent Response and Tool Use

The LLM's response is expected to be a JSON object containing:

- **`thought`:** The agent's reasoning process.
- **`response_to_user`:** A message to be displayed to the user.
- **`action`:** An object specifying the action to be taken, which can be:
    - **`tool_name`:** The name of the tool to use.
    - **`tool_parameters`:** The parameters for the tool.
    - **`agent_target`:** The next agent to transition to.

The `MessageOrchestrator` parses this response and executes the requested action.

### 6. Inter-Agent Communication

Agents can collaborate by passing messages to each other. When an agent's response includes an `agent_target`, the `MessageOrchestrator` routes the `message_to_target` to the specified agent's inbox.

### 7. Human-in-the-Loop (HITL)

To ensure safety and provide oversight, the system incorporates a Human-in-the-Loop (HITL) mechanism for sensitive operations. Before executing a command via the `execute_command` tool or writing to a file with `write_file` or `patch_file`, the system will prompt the user for confirmation.

## How to Use the Agent System in Code

You can integrate the agent system into your Python code by following these steps:

1.  **Create an LLM Instance:** Instantiate a language model from `src/ai/core/llms`.
2.  **Initialize Components:**
    - Create an `LLMConnector` with the LLM instance.
    - Create a `ToolRegistry` and register your desired tools from `src/ai/agents/agent_tools.py`.
3.  **Load Configuration:** Load your pipeline's JSON configuration file using the `load_pipeline_config` function.
4.  **Create the Orchestrator:** Instantiate the `MessageOrchestrator` with the connector, registry, and pipeline configuration.
5.  **Run the Loop:** Call the `run_loop` method of the orchestrator, providing the initial user prompt.

```python
from ai.agents.agent import MessageOrchestrator, LLMConnector, ToolRegistry, load_pipeline_config
from ai.agents.agent_tools import AVAILABLE_TOOLS
from ai.core.llms.gemini import Gemini # Or any other LLM

# 1. Create an LLM instance
llm = Gemini()

# 2. Initialize components
connector = LLMConnector(llm)
registry = ToolRegistry()
for name, tool_ref in AVAILABLE_TOOLS.items():
    registry.register_tool(name, tool_ref)

# 3. Load pipeline configuration
# Assuming 'prog' is an object with a 'config' attribute
# In a standalone script, you might need to load the main config differently
pipeline_config = load_pipeline_config(prog, "pipelines/pipeline.json")

# 4. Create the orchestrator
orchestrator = MessageOrchestrator(
    connector=connector,
    registry=registry,
    pipeline_config=pipeline_config
)

# 5. Run the loop
user_prompt = "This is your task. Go and solve it."
orchestrator.run_loop(user_prompt)
```

## How to Use the Agent System on the CLI

You can run the agent system directly from the command line using the `--agents` argument.

### Basic Usage

```bash
python -m ai --agents "Your task description here"
```

This command will use the default pipeline configuration located at `pipelines/pipeline.json`.

### Specifying a Pipeline

To use a custom pipeline configuration, provide the path to your JSON file:

```bash
python -m ai --agents /path/to/your/pipeline.json "Your task description here"
```

The agent system will then execute the task as defined in your custom pipeline.
