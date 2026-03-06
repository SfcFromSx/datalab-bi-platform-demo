import asyncio
from app.execution.python_executor import python_executor

async def main():
    res = await python_executor.execute("x = 1\nprint('hello world')\nx")
    print(res)

asyncio.run(main())
