import asyncio
from app.execution.python_executor import python_executor

async def main():
    res = await python_executor.execute("import pandas as pd\ndf = pd.DataFrame({'a': [1,2,3]})\n")
    print(res)

asyncio.run(main())
