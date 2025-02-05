"""Message manager for browser agents"""
import json
import re
from typing import List, Optional, Type, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel


from browser_init.views import BrowserState, TabInfo
from browser_capture.views import DOMState, DOMElementNode

class MessageManager:
    """Manages chat messages for an agent"""
    def __init__(
        self,
        llm: BaseChatModel,
        task: str,
        action_descriptions: str,
        max_input_tokens: int = 128000,
        include_attributes: list[str] = [],
        max_error_length: int = 400,
        max_actions_per_step: int = 10,
        message_context: Optional[str] = None,
    ):
        self.llm = llm
        self.task = task
        self.action_descriptions = action_descriptions
        self.max_input_tokens = max_input_tokens
        self.message_context = message_context
        self.include_attributes = include_attributes
        self.max_error_length = max_error_length
        self.max_actions_per_step = max_actions_per_step

        # Initialize message history
        self.messages: List[BaseMessage] = []
        self._initialize_messages()

    def _initialize_messages(self) -> None:
        """Initialize message history with system prompt"""
        system_prompt = self._create_system_prompt()
        self.messages = [SystemMessage(content=system_prompt)]

    def _create_system_prompt(self) -> str:
        """Create the system prompt"""
        return f"""You are a highly capable browser automation agent. Your task is: {self.task}

You can use these actions to accomplish the task:

{self.action_descriptions}

You should:
1. Analyze the current browser state
2. Evaluate your previous actions (if any)
3. Decide on your next goal
4. Take appropriate actions to achieve that goal

Each response must be a valid JSON object with the following structure:
{{
    "current_state": {{
        "evaluation_previous_goal": "Describe your evaluation of previous goal/actions",
        "memory": "Key information you want to remember",
        "next_goal": "Your next concrete goal"
    }},
    "action": [
        {{
            "type": "action_name",
            "data": {{
                "param1": "value1",
                "param2": "value2"
            }}
        }}
    ]
}}"""

    def add_state_message(
        self,
        state: BrowserState,
        last_result: Optional[List[dict]] = None,
        step_info: Optional[dict] = None,
    ) -> None:
        """Add browser state message"""
        if step_info:
            state_msg = f"\nStep Info: {json.dumps(step_info, indent=2)}\n"
        else:
            state_msg = ""

        if last_result:
            state_msg += f"\nPrevious Result: {json.dumps(last_result, indent=2)}\n"

        state_msg += f"\nCurrent URL: {state.url}\n"
        state_msg += f"Current Title: {state.title}\n"

        if state.element_tree:
            state_msg += "\nInteractive Elements:\n"
            state_msg += state.element_tree.clickable_elements_to_string(self.include_attributes)

        self.messages.append(HumanMessage(content=state_msg))

    def add_model_output(self, output: BaseModel) -> None:
        """Add model output to message history"""
        self.messages.append(
            SystemMessage(content=json.dumps(output.model_dump(), indent=2))
        )

    def _remove_last_state_message(self) -> None:
        """Remove the last state message"""
        if len(self.messages) > 1:
            self.messages.pop()

    def get_messages(self) -> List[BaseMessage]:
        """Get all messages"""
        return self.messages

    def merge_successive_human_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Merge successive human messages"""
        merged = []
        current_human_content = []

        for message in messages:
            if isinstance(message, HumanMessage):
                current_human_content.append(message.content)
            else:
                if current_human_content:
                    merged.append(HumanMessage(content="\n".join(current_human_content)))
                    current_human_content = []
                merged.append(message)

        if current_human_content:
            merged.append(HumanMessage(content="\n".join(current_human_content)))

        return merged

    def extract_json_from_model_output(self, output: str) -> dict:
        """Extract JSON from model output"""
        # Find JSON-like structure in the string
        matches = re.findall(r'\{(?:[^{}]|(?R))*\}', output)
        if not matches:
            raise ValueError("No JSON object found in output")

        try:
            return json.loads(matches[0])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def cut_messages(self) -> None:
        """Cut message history to fit token limit"""
        while len(self.messages) > 2:  # Keep system prompt and last message
            total_tokens = sum(len(str(m.content)) for m in self.messages)
            if total_tokens <= self.max_input_tokens:
                break
            self.messages.pop(1)  # Remove second message (keeping system prompt)
