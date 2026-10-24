"""CivicBridge Agent main entrypoint with Agent Chat Protocol (ACP) integration."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from agent.settings import (
    AGENT_NAME,
    AGENT_SEED_PHRASE,
    AGENT_PORT,
    AGENT_MAILBOX_KEY,
    DATABASE_PATH,
    LOG_LEVEL,
)
from agent.orchestrator import CivicBridgeOrchestrator
from database.seed import seed_database
from database.repository import SchemeRepository

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("civicbridge")

# 1. Initialize Database & Seed data if necessary
repo = SchemeRepository(db_path=DATABASE_PATH)
if repo.count() == 0:
    logger.info("Initializing scheme database with seed data...")
    seed_database(db_path=DATABASE_PATH)
logger.info(f"Loaded {repo.count()} official schemes into repository.")

# 2. Instantiate Orchestrator
orchestrator = CivicBridgeOrchestrator()

# Ensure active event loop exists for modern Python (3.12+)
import asyncio
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# 3. Configure uAgent
# If AGENT_MAILBOX_KEY is set, provide mailbox endpoint; otherwise local endpoint
agent_kwargs = {
    "name": AGENT_NAME,
    "seed": AGENT_SEED_PHRASE,
    "port": AGENT_PORT,
}
if AGENT_MAILBOX_KEY:
    agent_kwargs["mailbox"] = f"{AGENT_MAILBOX_KEY}@https://agentverse.ai"
else:
    agent_kwargs["mailbox"] = False

agent = Agent(**agent_kwargs)

# 4. Define Agent Chat Protocol (ACP v0.3.0)
chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """Handle incoming citizen messages via ACP and reply through orchestrator."""
    ctx.logger.info(f"Received chat message from {sender} (id={msg.msg_id})")

    # Acknowledge receipt
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # Check for session startup / greet
    if any(isinstance(c, StartSessionContent) for c in msg.content):
        ctx.logger.info("New session started; sending welcome greeting")
        reply = await orchestrator.handle_citizen_message(sender, "hello")
        await ctx.send(sender, reply)
        return

    # Extract user text
    text_items = [c.text for c in msg.content if isinstance(c, TextContent) and c.text]
    user_query = " ".join(text_items).strip()

    if not user_query:
        ctx.logger.debug("Received empty text content; skipping")
        return

    ctx.logger.info(f"Processing query from {sender}: {user_query}")
    try:
        reply_message = await orchestrator.handle_citizen_message(sender, user_query)
        await ctx.send(sender, reply_message)
        ctx.logger.info(f"Dispatched reply message to {sender}")
    except Exception as e:
        ctx.logger.exception(f"Error handling message: {e}")
        fallback = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            content=[
                TextContent(
                    type="text",
                    text=f"An unexpected error occurred while assessing schemes: {e}. Please try again shortly.",
                )
            ],
        )
        await ctx.send(sender, fallback)


@chat_proto.on_message(ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug(f"Received acknowledgement for msg_id={msg.acknowledged_msg_id} from {sender}")


agent.include(chat_proto, publish_manifest=True)


@agent.on_event("startup")
async def startup_event(ctx: Context):
    ctx.logger.info("==================================================================")
    ctx.logger.info(f"🇮🇳 CivicBridge Benefits Navigator Agent Started")
    ctx.logger.info(f"Agent Name: {agent.name}")
    ctx.logger.info(f"Agent Address: {agent.address}")
    ctx.logger.info(f"Database: {DATABASE_PATH} ({repo.count()} schemes loaded)")
    ctx.logger.info(f"Agentverse Mailbox: {'Enabled' if AGENT_MAILBOX_KEY else 'Disabled (Local Mode)'}")
    ctx.logger.info("==================================================================")


if __name__ == "__main__":
    agent.run()
