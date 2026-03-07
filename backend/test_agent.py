import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Get notebooks
        headers = {
            "X-DataLab-Workspace": "demo-hq",
            "X-DataLab-User-Email": "admin@datalab.local"
        }
        resp = await client.get("http://127.0.0.1:8000/api/notebooks", headers=headers)
        notebooks = resp.json()
        if not notebooks:
            print("No notebooks found.")
            return

        notebook_id = notebooks[0]["id"]
        
        print(f"Querying agent on notebook: {notebook_id}")
        try:
            resp = await client.post(
                "http://127.0.0.1:8000/api/agents/query",
                json={"notebook_id": notebook_id, "query": "Hello AI"},
                headers=headers,
                timeout=10.0
            )
            print(f"Status: {resp.status_code}")
            print(resp.text)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
