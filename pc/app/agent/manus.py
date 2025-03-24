import json
# 用于类型注解。Any 表示任意类型，Optional 表示一个值可以是某种类型或 None
from typing import Any, Optional
# Field，用于定义数据模型的字段及其默认值
from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
# 提示的字符串模板
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
# Terminate 可能是一个表示终止操作的工具，ToolCollection 是一个工具集合类
from app.tool import Terminate, ToolCollection
# 浏览器操作的工具
from app.tool.browser_use_tool import BrowserUseTool
# 文件保存的工具
from app.tool.file_saver import FileSaver
# 执行 Python 代码的工具
from app.tool.python_execute import PythonExecute


class Manus(ToolCallAgent):
    """
    它是一个通用的代理，能够使用多种工具（如 Python 执行、浏览器操作、文件操作等）来解决各种任务
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )
    # 你是 OpenManus，一个全能的人工智能助手，旨在解决用户提出的任何任务。你可以使用各种工具来高效地完成复杂的请求。
    # 无论是编程、信息检索、文件处理还是网页浏览，你都可以搞定。
    system_prompt: str = SYSTEM_PROMPT
    # 你可以使用 PythonExecute 与计算机交互，通过 FileSaver 保存重要内容和信息文件，使用 BrowserUseTool 打开浏览器，使用 GoogleSearch 检索信息。
    # PythonExecute：执行 Python 代码与计算机系统交互、数据处理、自动化任务等。
    # FileSaver：将文件保存在本地，如 txt、py、html 等。
    # BrowserUseTool：打开、浏览和使用网络浏览器。如果打开本地 HTML 文件，则必须提供文件的绝对路径。
    # Terminate：当任务完成或需要用户提供更多信息时结束当前交互。使用此工具表示您已完成处理用户的请求或需要澄清后再继续。
    # 根据用户需求，主动选择最合适的工具或工具组合。对于复杂的任务，你可以将问题分解并逐步使用不同的工具来解决。使用每个工具后，清楚地解释执行结果并建议下一步。
    # 在整个交互过程中始终保持乐于助人、信息丰富的语气。如果您遇到任何限制或需要更多详细信息，请在终止之前清楚地告知用户。
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000
    max_steps: int = 20

    # Add general-purpose tools to the tool collection 将通用工具添加到工具集合中
    # 定义类属性 available_tools，表示可用的工具集合。
    # 使用 Field 和 default_factory 动态初始化 ToolCollection，包含 PythonExecute、BrowserUseTool、FileSaver 和 Terminate 工具
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), BrowserUseTool(), FileSaver(), Terminate()
        )
    )

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        # 如果工具名称不是特殊工具，则直接返回
        if not self._is_special_tool(name):
            return
        else:
            # 如果是特殊工具，调用 BrowserUseTool 的 cleanup 方法进行清理
            await self.available_tools.get_tool(BrowserUseTool().name).cleanup()
            await super()._handle_special_tool(name, result, **kwargs)

    async def get_browser_state(self) -> Optional[dict]:
        """Get the current browser state for context in next steps. 获取浏览器状态以用于下一步的上下文"""
        # 从 available_tools 中获取 BrowserUseTool 工具实例
        browser_tool = self.available_tools.get_tool(BrowserUseTool().name)
        if not browser_tool:
            return None

        try:
            # Get browser state directly from the tool with no context parameter
            result = await browser_tool.get_current_state()

            if result.error:
                logger.debug(f"Browser state error: {result.error}")
                return None

            # Store screenshot if available
            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image

            # Parse the state info
            return json.loads(result.output)

        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def think(self) -> bool:
        # Add your custom pre-processing here
        browser_state = await self.get_browser_state()

        # Modify the next_step_prompt temporarily
        original_prompt = self.next_step_prompt
        if browser_state and not browser_state.get("error"):
            self.next_step_prompt += f"\nCurrent browser state:\nURL: {browser_state.get('url', 'N/A')}\nTitle: {browser_state.get('title', 'N/A')}\n"

        # Call parent implementation
        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result
