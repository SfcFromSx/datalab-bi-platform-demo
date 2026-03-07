import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        headers = {
            "X-DataLab-Workspace": "demo-hq",
            "X-DataLab-User-Email": "admin@datalab.local"
        }
        # Get notebooks
        resp = await client.get("http://127.0.0.1:8000/api/notebooks", headers=headers)
        notebooks = resp.json()
        if not notebooks:
            print("No notebooks found.")
            return

        notebook_id = notebooks[0]["id"]
        
        # Get cells for notebook
        resp = await client.get(f"http://127.0.0.1:8000/api/notebooks/{notebook_id}", headers=headers)
        nb = resp.json()
        cells = nb["cells"]
        sql_cell = next((c for c in cells if c["cell_type"] == "sql"), None)
        if not sql_cell:
            print("No SQL cell found.")
            return

        print(f"Executing SQL cell: {sql_cell['id']}")
        resp = await client.post(
            f"http://127.0.0.1:8000/api/cells/{sql_cell['id']}/execute",
            json={"source": "-- output: sales_summary\nSELECT * FROM sales"},
            headers=headers
        )
        print(f"Status: {resp.status_code}")
        print(resp.text)

asyncio.run(main())
