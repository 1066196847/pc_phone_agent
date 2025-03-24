from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results") # 抛出 ValueError 异常，中断程序
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    # 作用：返回一个新的对象（ToolResult 实例），并将当前对象的字段与传入的 kwargs 参数合并。
    # 如果 kwargs 中有与当前对象字段同名的参数，则使用 kwargs 中的值覆盖当前对象的值。
    # 返回值：返回一个新的对象，类型与当前对象相同（通过 type(self) 获取）
    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # type(self) 获取当前对象的类（即 ToolResult）
        # 通过 type(self)(...) 创建一个新的 ToolResult 实例

        # self.dict() 将当前对象的字段和值转换为字典，例如，如果 self 是 ToolResult(name="tool1", value=10)，则 self.dict() 返回：
        # {"name": "tool1", "value": 10}
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""
