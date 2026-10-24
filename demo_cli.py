"""Interactive Terminal Demo for CivicBridge Navigator (Simulating ACP & ASI:One Chat)."""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agent.orchestrator import CivicBridgeOrchestrator
from uagents_core.contrib.protocols.chat import TextContent, MetadataContent


async def main():
    orchestrator = CivicBridgeOrchestrator()
    user_id = "interactive_citizen"

    print("=" * 70)
    print("🇮🇳  CIVICBRIDGE NAVIGATOR — AI GOVERNMENT BENEFITS ADVISOR")
    print("Fetch.ai uAgents · Agent Chat Protocol (ACP v0.3.0) · ASI:One")
    print("=" * 70)
    print("Type your requirement or citizen profile in natural language.")
    print("Examples to try:")
    print("  1. 'I am a 35-year-old farmer in Uttar Pradesh with 1.2 hectares of land'")
    print("  2. 'I am an SC student in college with family income under 2 lakh'")
    print("  3. 'I am a street vendor running a tea stall in Delhi'")
    print("  4. 'PM-KISAN' (to drill down into documents and steps)")
    print("  5. 'exit' or 'quit' to end session.")
    print("-" * 70)

    # Initial greeting
    initial_msg = await orchestrator.handle_citizen_message(user_id, "hello")
    for content in initial_msg.content:
        if isinstance(content, TextContent):
            print(f"\n[CivicBridge Agent]:\n{content.text}\n")

    while True:
        try:
            user_input = input("\n[Citizen] > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nThank you for using CivicBridge. Jai Hind! 🇮🇳")
                break

            response = await orchestrator.handle_citizen_message(user_id, user_input)

            # Render text content
            for item in response.content:
                if isinstance(item, TextContent):
                    print(f"\n[CivicBridge Agent]:\n{item.text}\n")
                elif isinstance(item, MetadataContent):
                    if item.metadata.get("card_kind") == "custom":
                        card_payload = json.loads(item.metadata.get("card_payload", "{}"))
                        print("┌" + "─" * 68 + "┐")
                        print("│ 📇 [ASI:One Interactive Card Rendered to Chat Window]            │")
                        root = card_payload.get("root", {})
                        print(f"│ Title: {root.get('title', 'N/A')[:58]:<58} │")
                        if root.get("subtitle"):
                            print(f"│ Subtitle: {root.get('subtitle')[:55]:<55} │")
                        print("└" + "─" * 68 + "┘")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Jai Hind! 🇮🇳")
            break


if __name__ == "__main__":
    asyncio.run(main())
