# browser-agents

AI agent implementation for browser automation.

## Overview

This package provides the AI agent implementation for browser automation. It handles:

- LLM-powered browser automation
- Action planning and execution
- State management and memory
- Multi-step task completion
- Error handling and recovery
- History tracking and GIF generation

## Installation

```bash
pip install browser-agents
```

## Usage

```python
from langchain_core.language_models import ChatOpenAI
from browser_agents.service import Agent
from browser_agents.views import AgentStepInfo

# Initialize LLM
llm = ChatOpenAI(model="gpt-4-vision-preview")

# Create agent
agent = Agent(
    task="Navigate to example.com and click the 'About' link",
    llm=llm,
    use_vision=True,
    max_failures=3,
    validate_output=True
)

# Run the agent
async def run_agent():
    # Optional step info for detailed logging
    step_info = AgentStepInfo(
        note="Starting navigation task",
        category="navigation"
    )

    # Execute the task
    history = await agent.run(max_steps=10)

    # Check results
    if history.is_done():
        print("✅ Task completed successfully")
        for item in history.history:
            if item.result:
                print(f"Action result: {item.result[-1].extracted_content}")
    else:
        print("❌ Task failed to complete")

# Run the agent
await run_agent()
```

## Features

- LLM-powered decision making
- Structured action planning
- State tracking and memory management
- Error recovery mechanisms
- Progress visualization (GIF generation)
- Integration with browser-init and browser-capture
- Customizable system prompts
- Support for multiple LLM providers

## Dependencies

- langchain-core>=0.0.242
- pydantic>=2.0.0
- typing-extensions>=4.0.0
- loguru>=0.7.0
- lmnr>=0.0.5
- Pillow>=10.0.0
- browser-init>=0.1.0
- browser-capture>=0.1.0

## Development

```bash
# Install development dependencies
pdm install -G test,lint

# Run tests
pytest

# Run linters
ruff check .
black .
mypy .
```

## Architecture

The agent system is composed of several key components:

1. **Agent Service**: Core logic for task execution and state management
2. **Controller**: Handles action registration and execution
3. **Message Manager**: Manages conversation history and context
4. **Views**: Data models for agent state and actions

## Customization

The agent can be customized in several ways:

- Custom action registration
- System prompt modification
- Output validation rules
- Memory management settings
- Vision mode configuration
- Browser settings inheritance

## License

MIT License
