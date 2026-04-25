import os, json, time
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS
from dotenv import load_dotenv
from database import create_rescue, complete_rescue
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
from anthropic import Anthropic
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
    rescue_id = trigger.get("rescue_id") or f"rescue_{int(time.time())}"

    # Persist a running rescue so the dashboard has something stable to show.
    try:
        create_rescue(rescue_id, trigger["location_id"], trigger["location_name"])
    except Exception as e:
        print(f"[WARN] Failed to create rescue record: {e}")

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

    result = {
        "status": "started",
        "rescue_id": rescue_id,
        "steps": [],
        "dispatch": None,
        "assistant_messages": [],
        "final_message": None,
    }

    max_iterations = int(os.getenv("FOODFLOW_AGENT_MAX_ITERS", "12"))
    max_seconds = int(os.getenv("FOODFLOW_AGENT_MAX_SECONDS", "45"))
    started = time.time()

    result["backend"] = "anthropic"
    if not os.getenv("ANTHROPIC_API_KEY"):
        result["status"] = "error"
        result["error"] = "Missing ANTHROPIC_API_KEY"
        try:
            complete_rescue(rescue_id, "error", json.dumps(result))
        except Exception:
            pass
        return result

    iterations = 0
    while True:
        iterations += 1
        if iterations > max_iterations or (time.time() - started) > max_seconds:
            result["status"] = "timeout"
            result["error"] = f"Agent exceeded limits (iters={max_iterations}, seconds={max_seconds})"
            break

        try:
            response = client.messages.create(
                model=os.getenv("FOODFLOW_ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                max_tokens=int(os.getenv("FOODFLOW_MAX_COMPLETION_TOKENS", "4096")),
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages
            )
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"Anthropic API error: {e}"
            break

        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"\n[CLAUDE] {block.text}")
                result["assistant_messages"].append(block.text)

        if response.stop_reason == "end_turn":
            result["status"] = "completed"
            # Best-effort: keep the last assistant text as the final user-facing summary.
            if result["assistant_messages"]:
                result["final_message"] = result["assistant_messages"][-1]
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\n[TOOL: {block.name}] → {json.dumps(block.input, indent=2)}")
            fn = TOOL_FUNCTIONS.get(block.name)
            tool_input = dict(block.input or {})
            if block.name == "dispatch_pickup" and "rescue_id" not in tool_input:
                tool_input["rescue_id"] = rescue_id

            try:
                output = fn(**tool_input) if fn else {"error": f"Unknown tool: {block.name}"}
            except Exception as e:
                output = {"error": f"Tool {block.name} failed: {e}"}
            print(f"[RESULT] {json.dumps(output, indent=2)}")
            result["steps"].append({"tool": block.name, "input": tool_input, "output": output})
            if block.name == "dispatch_pickup":
                result["dispatch"] = output
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output)})

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    print(f"\n{'✅ '*10}")
    dispatched_lbs = (result.get("dispatch") or {}).get("quantity_lbs", 0)
    print(f"[FOODFLOW] Rescue complete: {dispatched_lbs} lbs dispatched")
    try:
        complete_rescue(rescue_id, result["status"], json.dumps(result))
    except Exception as e:
        print(f"[WARN] Failed to persist rescue result: {e}")
    return result


if __name__ == "__main__":
    from database import init_db
    init_db()
    run_agent({"location_id": "cornell_statler", "location_name": "Cornell Statler Hall", "lat": 42.4467, "lng": -76.4851})
