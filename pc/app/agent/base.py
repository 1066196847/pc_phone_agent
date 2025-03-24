from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import ROLE_TYPE, AgentState, Memory, Message

class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.

    用于管理代理状态和执行的抽象基类
    为状态转换、内存管理、基于步骤的执行循环 提供基础功能。子类必须实现“step”方法。
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    # 在class中定义llm、memory两个变量时，就已经做了赋值(default_factory)，而且都是LLM Memory实例
    # initialize_agent是发生在实例初始化后执行，在实例初始化的时候llm、memory会进行赋值，所以函数中两个if都不会执行到
    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    # 作用：安全地切换代理状态，确保在代码块执行后恢复原状态（即使发生异常）。
    # 流程：
    # 保存当前状态 previous_state。
    # 将状态切换为 new_state。
    # 执行 async with 块内的代码。state_context()是在run()中调用，调用的时候async with state_context()
    # 无论成功或失败，最终恢复为 previous_state。
    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions. 用于安全代理状态转换的上下文管理器。

        Args:
            new_state: The state to transition to during the context. 在上下文中过渡到的状态。

        Yields:
            None: Allows execution within the new state. 允许在新状态下执行。

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state # 进入上下文时切换状态
        try:
            yield # 在此处暂停，执行 async with 块内的代码
        except Exception as e:
            self.state = AgentState.ERROR  # 发生异常时切换到 ERROR 状态
            raise e
        finally:
            self.state = previous_state    # 退出上下文时恢复原状态

    def update_memory(
        self,
        role: ROLE_TYPE,  # typing.Literal['system', 'user', 'assistant', 'tool']
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            base64_image: Optional base64 encoded image.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Create message with appropriate parameters based on role
        kwargs = {"base64_image": base64_image, **(kwargs if role == "tool" else {})}
        self.memory.add_message(message_map[role](content, **kwargs))

    # 作用：异步执行代理的主循环，逐步完成任务。
    # 流程：
    # 检查代理是否处于 IDLE 状态，否则抛出错误。
    # 如果有请求，更新memory。
    # 进入 RUNNING 状态（通过 state_context）。
    # 循环执行 step() 方法，直到达到最大步骤或状态变为 FINISHED。
    # 收集每一步的结果，最终返回汇总字符串。
    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously. 异步执行代理的主循环

        Args:
            request: Optional initial user request to process. 要处理的可选初始用户请求

        Returns:
            A string summarizing the execution results. 总结执行结果的字符串

        Raises:
            RuntimeError: If the agent is not in IDLE state at start. IDLE：处理器（CPU）没有正在执行的指令，即没有任务需要处理时的状态
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        # self.memory中增加一条user_message，用户最开始的提示词
        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state 检查是否处于卡住状态
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        return "\n".join(results) if results else "No steps executed"

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    # 通过添加更改策略的提示来处理卡住状态
    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        # 观察到重复反应。考虑新的策略，避免重复已经尝试过的无效路径。
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    # 通过检测重复内容来检查代理是否卡在循环中
    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
