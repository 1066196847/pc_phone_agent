import asyncio

from app.agent.manus import Manus
from app.logger import logger

# 异步函数 main
async def main():
    agent = Manus()
    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        # await 关键字表示这是一个异步操作，程序会等待 run 方法执行完成
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")


if __name__ == "__main__":
    # asyncio.run 是 Python 3.7 引入的，用于运行异步函数并管理事件循环
    asyncio.run(main())
