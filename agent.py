import os, json
from anthropic import Anthropic
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

SYSTEM_PROMPT = """You are FoodFlow, an autonomous food rescue agent.

Your mission: when food surplus is detected, orchestrate a complete rescue automatically.

Always follow this exact sequence:
1. check_inventory — confirm surplus details
2. check_foodbank_capacity — find accepting food bank
3. query_volunteers — find drivers near supplier
4. calculate_route — estimate ETA
5. verify_compliance — confirm Bill Emerson Act coverage
6. dispatch_pickup — send SMS and log pickup

Only call dispatch_pickup after all 5 prior checks pass. Be concise."""


def run_agent(trigger: dict) -> dict:
    print(f"\n{'🌿 '*20}")
    print(f"[FOODFLOW AGENT] Surplus trigger: {trigger['location_name']}")
    print(f"{'─'*60}")

    messages = [{
        "role": "user",
        "content": (
            f"Surplus alert at {trigger['location_name']} "
            f"(location_id: {trigger['location_id']}, "
            f"lat: {trigger['lat']}, lng: {trigger['lng']}). "
            f"Run the complete food rescue sequence. "
            f"Use Ithaca Food Bank (foodbank_id: ithaca_food_bank) as recipient."
        )
    }]

    result = {"status": "started", "steps": [], "dispatch": None}

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages
        )

        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"\n[CLAUDE] {block.text}")

        if response.stop_reason == "end_turn":
            result["status"] = "completed"
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\n[TOOL: {block.name}] → {json.dumps(block.input, indent=2)}")
            fn = TOOL_FUNCTIONS.get(block.name)
            output = fn(**block.input) if fn else {"error": f"Unknown tool: {block.name}"}
            print(f"[RESULT] {json.dumps(output, indent=2)}")
            result["steps"].append({"tool": block.name, "input": block.input, "output": output})
            if block.name == "dispatch_pickup":
                result["dispatch"] = output
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output)})

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    print(f"\n{'✅ '*10}")
    print(f"[FOODFLOW] Rescue complete: {result.get('dispatch', {}).get('quantity_lbs', 0)} lbs dispatched")
    return result


if __name__ == "__main__":
    from database import init_db
    init_db()
    run_agent({"location_id": "cornell_statler", "location_name": "Cornell Statler Hall", "lat": 42.4467, "lng": -76.4851})
