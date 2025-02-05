"""Controller service for browser agents"""
from typing import Any, Type, Dict, Union, Protocol, runtime_checkable, List, Optional, cast

from pydantic import BaseModel, ConfigDict, create_model, Field

from browser_agents.views import ActionResult

@runtime_checkable
class ActionData(Protocol):
    """Protocol for action data"""
    async def execute(self, context: Any) -> ActionResult:
        """Execute the action"""
        ...

    @staticmethod
    def get_description() -> str:
        """Get action description for prompts"""
        ...

class ActionBase(BaseModel):
    """Base class for all action data models"""
    model_config = ConfigDict(extra='forbid')
    index: int = -1

    @staticmethod
    def get_description() -> str:
        """Get description for prompts"""
        return "No description provided"

class ActionModel(BaseModel):
    """Base model for all actions"""
    model_config = ConfigDict(extra='forbid')
    action_type: str = Field(alias='type')
    data: Dict[str, Any]

    def get_index(self) -> int:
        """Get index from action data"""
        return self.data.get('index', -1) if self.data else -1

    def set_index(self, new_index: int) -> None:
        """Set index in action data"""
        if self.data:
            self.data['index'] = new_index

class Registry:
    """Registry of actions"""
    def __init__(self):
        self.actions: Dict[str, Type[ActionBase]] = {}

    def register(self, name: str, action_class: Type[ActionBase]) -> None:
        """Register a new action"""
        if not hasattr(action_class, 'execute'):
            raise ValueError(f"Action class {action_class.__name__} must implement execute method")
        self.actions[name] = action_class

    def get(self, name: str) -> Optional[Type[ActionBase]]:
        """Get an action by name"""
        return self.actions.get(name)

    def get_prompt_description(self) -> str:
        """Get descriptions of all registered actions"""
        descriptions = []
        for name, action_class in self.actions.items():
            description = action_class.get_description()
            descriptions.append(f"Action: {name}\n{description}\n")
        return "\n".join(descriptions)

class Controller:
    """Controller for browser agent actions"""
    def __init__(self):
        self.registry = Registry()

    def register_action(self, name: str, action_class: Type[ActionBase]) -> None:
        """Register a new action type"""
        self.registry.register(name, action_class)

    def create_action_model(self) -> Type[ActionModel]:
        """Create a Pydantic model for actions"""
        return ActionModel

    async def multi_act(self, actions: list[ActionModel], context: Any) -> list[ActionResult]:
        """Execute a list of actions"""
        results = []
        for action in actions:
            if not action:
                results.append(ActionResult(error="None action provided"))
                continue

            action_class = self.registry.get(action.action_type)
            if not action_class:
                results.append(ActionResult(error=f"Unknown action type: {action.action_type}"))
                continue

            try:
                # Create instance of the action class with the data
                action_instance = action_class(**action.data)
                if isinstance(action_instance, ActionData):
                    result = await action_instance.execute(context)
                    results.append(result)
                else:
                    results.append(ActionResult(
                        error=f"Action {action_class.__name__} does not implement ActionData protocol"
                    ))
            except Exception as e:
                results.append(ActionResult(error=str(e)))

        return results
