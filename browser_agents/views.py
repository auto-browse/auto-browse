"""Browser agent views"""
import traceback
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic, cast
from dataclasses import dataclass, field

from pydantic import BaseModel

from browser_init.views import BrowserStateHistory
from browser_capture.views import SelectorMap

class AgentError:
    """Agent error utilities"""
    @staticmethod
    def format_error(error: Exception, include_trace: bool = False) -> str:
        """Format error message"""
        if include_trace:
            return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        return str(error)

class ActionResult(BaseModel):
    """Result of an agent action"""
    error: Optional[str] = None
    is_done: bool = False
    extracted_content: Optional[str] = None
    include_in_memory: bool = True

class AgentCurrentState(BaseModel):
    """Current state of the agent"""
    evaluation_previous_goal: str
    memory: str
    next_goal: str

    def __str__(self) -> str:
        return (
            f"Previous Goal: {self.evaluation_previous_goal}\n"
            f"Memory: {self.memory}\n"
            f"Next Goal: {self.next_goal}"
        )

class AgentOutputBase(BaseModel):
    """Base fields that all AgentOutput models must have."""
    current_state: AgentCurrentState

# Generic type for action models
ActionType = TypeVar("ActionType", bound=BaseModel)

class AgentOutput(AgentOutputBase, Generic[ActionType]):
    """Output from LLM with typed actions."""
    action: List[ActionType]

    @classmethod
    def type_with_custom_actions(cls, action_model: Type[BaseModel]) -> Type["AgentOutput[Any]"]:
        """
        Create a new AgentOutput subclass with the specified action type.
        This approach ensures it's recognized as a proper subclass by type checkers.
        """
        # Dynamically create a subclass of AgentOutput where “action” is typed with the given model
        # and “current_state” is still typed with AgentCurrentState.
        # This also inherits from AgentOutputBase for shared fields.

        # The new class needs to inherit from AgentOutput, so type checkers realize
        # it is valid for all places expecting an AgentOutput[Any].

        new_class_attrs = {
            "__annotations__": {
                "current_state": AgentCurrentState,
                "action": List[action_model],
            },
            # The rest of the attributes (if any) from AgentOutput remain inherited
        }

        CustomAgentOutput = type(
            "CustomAgentOutput",
            (AgentOutput,),
            new_class_attrs
        )
        return CustomAgentOutput

@dataclass
class AgentHistory:
    """Single history item for agent actions"""
    model_output: Optional[AgentOutput[Any]]
    result: List[ActionResult]
    state: BrowserStateHistory

    @staticmethod
    def get_interacted_element(
        model_output: Optional[AgentOutput[Any]],
        selector_map: SelectorMap
    ) -> List[str]:
        """Get element IDs that the agent interacted with"""
        if not model_output or not hasattr(model_output, 'action'):
            return []

        element_ids = []
        for action in model_output.action:
            # Safety check since action is generic
            if hasattr(action, 'data') and isinstance(action.data, dict):
                selector = action.data.get('selector')
                if selector and selector in selector_map:
                    element_ids.append(str(selector))
        return element_ids

@dataclass
class AgentHistoryList:
    """List of history items"""
    history: List[AgentHistory] = field(default_factory=list)

    def is_done(self) -> bool:
        """Check if the agent is done"""
        if not self.history:
            return False
        last_result = self.history[-1].result
        return bool(last_result and last_result[-1].is_done)

    def __len__(self) -> int:
        return len(self.history)

class AgentStepInfo(BaseModel):
    """Step information to record with action"""
    note: Optional[str] = None
    category: Optional[str] = None
