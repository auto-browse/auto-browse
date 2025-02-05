"""Browser agent service"""
import asyncio
import base64
import json
import logging
import os
import platform
import uuid
from typing import Any, Optional, List, Callable, Dict, Type, Tuple, cast, Sequence, Union
from io import BytesIO

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from lmnr import observe
from pydantic import BaseModel, ValidationError
from PIL import Image, ImageDraw, ImageFont

from browser_agents.controller.service import Controller, ActionModel
from browser_agents.message_manager import MessageManager
from browser_agents.views import (
    ActionResult,
    AgentError,
    AgentHistory,
    AgentHistoryList,
    AgentOutput,
    AgentStepInfo,
)
from browser_capture.views import DOMState
from browser_init.browser import Browser as InitBrowser
from browser_init.context import (
    Browser as ContextBrowser,
    BrowserContext as InitBrowserContext,
    BrowserContextConfig,
)
from browser_init.views import BrowserState, BrowserStateHistory

logger = logging.getLogger(__name__)

class Agent:
    """AI Agent for browser automation"""
    def __init__(
        self,
        task: str,
        llm: BaseChatModel,
        browser: Optional[InitBrowser] = None,
        browser_context: Optional[InitBrowserContext] = None,
        controller: Optional[Controller] = None,
        use_vision: bool = True,
        max_failures: int = 3,
        retry_delay: int = 10,
        max_input_tokens: int = 128000,
        validate_output: bool = False,
        message_context: Optional[str] = None,
        generate_gif: Union[bool, str] = True,
        max_error_length: int = 400,
        max_actions_per_step: int = 10,
    ):
        self.agent_id = str(uuid.uuid4())
        self.task = task
        self.use_vision = use_vision
        self.llm = llm
        self._last_result: Optional[List[ActionResult]] = None
        self.max_error_length = max_error_length
        self.generate_gif = generate_gif

        # Controller setup
        self.controller = controller or Controller()
        self.max_actions_per_step = max_actions_per_step

        # Browser setup
        self.injected_browser = browser is not None
        self.injected_browser_context = browser_context is not None
        self.message_context = message_context

        # Initialize browser first if needed
        self.browser = browser if browser is not None else (None if browser_context else InitBrowser())

        # Initialize browser context
        if browser_context:
            self.browser_context = browser_context
        elif self.browser:
            self.browser_context = InitBrowserContext(browser=cast(ContextBrowser, self.browser))
        else:
            self.browser = InitBrowser()
            self.browser_context = InitBrowserContext(browser=cast(ContextBrowser, self.browser))

        # Action model setup
        self.ActionModel = self.controller.create_action_model()
        self.AgentOutput = AgentOutput.type_with_custom_actions(self.ActionModel)

        # Initialize message manager
        self.message_manager = MessageManager(
            llm=self.llm,
            task=task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            max_input_tokens=max_input_tokens,
            message_context=message_context,
            include_attributes=[
                'title', 'type', 'name', 'role', 'tabindex', 'aria-label',
                'placeholder', 'value', 'alt', 'aria-expanded'
            ],
            max_error_length=max_error_length,
            max_actions_per_step=max_actions_per_step,
        )

        # Task parameters
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self.consecutive_failures = 0
        self.validate_output = validate_output
        self.max_input_tokens = max_input_tokens

        # History
        self.history = AgentHistoryList(history=[])

        # Control flags
        self._paused = False
        self._stopped = False

    def _too_many_failures(self) -> bool:
        """Check if we should stop due to too many failures"""
        if self.consecutive_failures >= self.max_failures:
            logger.error(f'❌ Stopping due to {self.max_failures} consecutive failures')
            return True
        return False

    async def _handle_control_flags(self) -> bool:
        """Handle pause and stop flags"""
        if self._stopped:
            logger.info('Agent stopped')
            return False

        while self._paused:
            await asyncio.sleep(0.2)  # Small delay to prevent CPU spinning
            if self._stopped:
                return False
        return True

    async def step(self, step_info: Optional[AgentStepInfo] = None) -> None:
        """Execute one step of the task"""
        logger.info(f'\n📍 Step {len(self.history.history) + 1}')
        state = None
        model_output = None
        result: List[ActionResult] = []

        try:
            state = await self.browser_context.get_state(use_vision=self.use_vision)

            if self._stopped or self._paused:
                raise InterruptedError("Agent interrupted")

            # Add state to message history
            self.message_manager.add_state_message(
                state=state,
                last_result=[r.__dict__ for r in self._last_result] if self._last_result else None,
                step_info=step_info.__dict__ if step_info else None
            )
            input_messages = self.message_manager.get_messages()

            try:
                # Get next action from LLM
                model_output = await self._get_next_action(input_messages)
                if self._stopped or self._paused:
                    raise InterruptedError("Agent interrupted")

                # Execute actions
                result = await self.controller.multi_act(model_output.action, self.browser_context)
                self._last_result = result

                if result and result[-1].is_done:
                    logger.info(f'📄 Result: {result[-1].extracted_content}')

                self.consecutive_failures = 0

            except Exception as e:
                result = await self._handle_step_error(e)
                self._last_result = result

        finally:
            if state:
                self._make_history_item(model_output, state, result or [])

    def _make_history_item(
        self,
        model_output: Optional[AgentOutput],
        state: BrowserState,
        result: List[ActionResult],
    ) -> None:
        """Create and store history item"""
        interacted_elements = AgentHistory.get_interacted_element(
            model_output, state.selector_map
        ) if model_output else [None]

        # Convert to List[str] for BrowserStateHistory
        element_ids: List[str] = [str(x) if x is not None else "" for x in interacted_elements]

        state_history = BrowserStateHistory(
            url=state.url,
            title=state.title,
            tabs=state.tabs,
            interacted_element=element_ids,
            screenshot=state.screenshot,
        )

        history_item = AgentHistory(
            model_output=model_output,
            result=result,
            state=state_history,
        )

        self.history.history.append(history_item)

    async def _get_next_action(self, messages: List[BaseMessage]) -> AgentOutput[Any]:
        """Get next action from LLM"""
        try:
            response = await self.llm.with_structured_output(self.AgentOutput).ainvoke(messages)
            if not isinstance(response, AgentOutput):
                raise ValueError("LLM response was not an AgentOutput instance")
            return cast(AgentOutput[Any], response)
        except Exception as e:
            logger.error(f"Error getting next action: {e}")
            raise

    async def _handle_step_error(self, error: Exception) -> List[ActionResult]:
        """Handle step errors"""
        include_trace = logger.isEnabledFor(logging.DEBUG)
        error_msg = AgentError.format_error(error, include_trace=include_trace)
        prefix = f'❌ Result failed {self.consecutive_failures + 1}/{self.max_failures} times:\n '

        if isinstance(error, (ValidationError, ValueError)):
            logger.error(f'{prefix}{error_msg}')
            if 'Max token limit reached' in error_msg:
                self.message_manager.max_input_tokens = self.max_input_tokens - 500
                logger.info(f'Cutting tokens from history - new max: {self.message_manager.max_input_tokens}')
                self.message_manager.cut_messages()

            self.consecutive_failures += 1
        else:
            logger.error(f'{prefix}{error_msg}')
            self.consecutive_failures += 1
            await asyncio.sleep(self.retry_delay)

        return [ActionResult(error=error_msg, include_in_memory=True)]

    @observe(name='agent.run')
    async def run(self, max_steps: int = 100) -> AgentHistoryList:
        """Execute the task"""
        try:
            for step in range(max_steps):
                if self._too_many_failures():
                    break

                if not await self._handle_control_flags():
                    break

                await self.step()

                if self.history.is_done():
                    if self.validate_output and step < max_steps - 1:
                        if not await self._validate_output():
                            continue
                    break

            return self.history

        finally:
            # Cleanup
            if not self.injected_browser_context:
                await self.browser_context.close()

            if not self.injected_browser and self.browser:
                await self.browser.close()

            if self.generate_gif:
                output_path = 'agent_history.gif'
                if isinstance(self.generate_gif, str):
                    output_path = self.generate_gif
                self.create_history_gif(output_path=output_path)

    async def _validate_output(self) -> bool:
        """Validate the output"""
        if not self.browser_context.session:
            return True

        state = await self.browser_context.get_state(use_vision=self.use_vision)
        prompt = (
            f'Validate if the output of last action is what the user wanted and if the task is completed. '
            f'Task to validate: {self.task}.'
        )

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=str(self._last_result)),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = ""
            if isinstance(response, ChatResult):
                message = response.generations[0].message
                content = message.content if hasattr(message, 'content') else str(message)
            elif isinstance(response, (AIMessage, str)):
                content = response.content if isinstance(response, AIMessage) else response
            else:
                content = str(response)

            content_lower = str(content).lower()
            is_valid = 'valid' in content_lower and 'not' not in content_lower
            if not is_valid:
                logger.info(f'❌ Validation failed: {content}')
                self._last_result = [ActionResult(
                    error=f'Validation failed: {content}',
                    include_in_memory=True
                )]
            else:
                logger.info('✅ Validation passed')
            return is_valid
        except Exception as e:
            logger.error(f'Validation error: {e}')
            return True

    def create_history_gif(
        self,
        output_path: str = 'agent_history.gif',
        duration: int = 3000,
        show_goals: bool = True,
        show_task: bool = True,
        font_size: int = 40,
        margin: int = 40,
    ) -> None:
        """Create a GIF from the history"""
        if not self.history.history or not self.history.history[0].state.screenshot:
            logger.warning('No history to create GIF from')
            return

        try:
            # Try to load system font
            try:
                font_options = ['Helvetica', 'Arial', 'DejaVuSans']
                font = None
                for font_name in font_options:
                    try:
                        if platform.system() == 'Windows':
                            font_name = os.path.join(os.getenv('WIN_FONT_DIR', 'C:\\Windows\\Fonts'), font_name + '.ttf')
                        font = ImageFont.truetype(font_name, font_size)
                        break
                    except OSError:
                        continue
                if not font:
                    font = ImageFont.load_default()
            except OSError:
                font = ImageFont.load_default()

            images = []
            for item in self.history.history:
                if not item.state.screenshot:
                    continue

                # Convert base64 screenshot to PIL Image
                img_data = base64.b64decode(item.state.screenshot)
                image = Image.open(BytesIO(img_data))

                if show_goals and item.model_output:
                    # Add text overlay
                    draw = ImageDraw.Draw(image)
                    goal = item.model_output.current_state.next_goal
                    draw.text((margin, margin), goal, font=font, fill='black')

                images.append(image)

            if images:
                images[0].save(
                    output_path,
                    save_all=True,
                    append_images=images[1:],
                    duration=duration,
                    loop=0,
                )
                logger.info(f'Created GIF at {output_path}')
        except Exception as e:
            logger.error(f'Failed to create GIF: {e}')
