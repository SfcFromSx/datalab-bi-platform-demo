import asyncio
import json
import httpx

async def main():
    print("Testing Auto Agent...")
    async with httpx.AsyncClient() as client:
        # Create a task
        payload = {
            "query": "Generate some mock sales data, calculate the total revenue, and plot a chart of the top 5 products."
        }
        print(f"Submitting query: {payload['query']}")
        
        async with client.stream("POST", "http://127.0.0.1:8000/api/agent-tasks", json=payload, timeout=120.0) as response:
            if response.status_code != 200:
                print(f"Error starting task: {response.status_code}")
                text = await response.aread()
                print(text)
                return

            print("Stream started. Listening for events...")
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    print(f"\n[EVENT] {event_type}")
                elif line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        if "message" in data:
                            print(f"  Message: {data['message']}")
                        elif isinstance(data, list):
                            for idx, step in enumerate(data):
                                if isinstance(step, dict) and "description" in step:
                                    status = step.get("status", "unknown")
                                    print(f"  Step {idx}: {step['description']} [{status}]")
                        else:
                            content = data.get("content", str(data)) if isinstance(data, dict) else str(data)
                            print(f"  Data: {str(content)[:200]}...")
                    except json.JSONDecodeError:
                        print(f"  Raw Data: {data_str}")

        print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(main())
