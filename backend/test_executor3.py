import asyncio
from app.execution.python_executor import python_executor

async def main():
    res1 = await python_executor.execute("x = [1, 2, 3]\nprint(x)")
    print(res1)
    res2 = await python_executor.execute("print(x)")
    print(res2)

asyncio.run(main())
