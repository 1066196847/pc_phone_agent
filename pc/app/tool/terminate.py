from app.tool.base import BaseTool

# 当请求得到满足或助手无法继续执行任务时，终止交互。
# 当你完成所有任务后，调用此工具结束工作。
_TERMINATE_DESCRIPTION = """Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
When you have finished all the tasks, call this tool to end the work."""


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "The finish status of the interaction.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> str:
        """Finish the current execution"""
        # 交互已完成，状态为：{status}
        return f"The interaction has been completed with status: {status}"
