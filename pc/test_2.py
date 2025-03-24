from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import ROLE_TYPE, AgentState, Memory, Message

class BaseAgent(BaseModel):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.

    用于管理代理状态和执行的抽象基类
    为状态转换、内存管理、基于步骤的执行循环 提供基础功能。子类必须实现“step”方法。
    """

    # Core attributes
    # name: str = Field(..., description="Unique name of the agent")
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

    # # 在class中定义llm、memory两个变量时，就已经做了赋值，而且都是LLM Memory示例
    # # initialize_agent是发生在实例初始化后执行，所以两个if都不会执行到
    # @model_validator(mode="after")
    # def initialize_agent(self) -> "BaseAgent":
    #     """Initialize agent with default settings if not provided."""
    #     if self.llm is None or not isinstance(self.llm, LLM):
    #         self.llm = LLM(config_name=self.name.lower())
    #     if not isinstance(self.memory, Memory):
    #         self.memory = Memory()
    #     return self


