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
    EndSessionContent,
    TextContent,
    MetadataContent,
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
    "mailbox": True,
}

agent = Agent(**agent_kwargs)

# 4. Define Agent Chat Protocol (ACP v0.3.0)
chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """Handle incoming citizen messages via ACP and reply through orchestrator."""
    ctx.logger.info(f"Received chat message from {sender} (id={msg.msg_id})")

    # 1. Acknowledge receipt as per Agent Chat Protocol v0.3.0
    try:
        await ctx.send(
            sender,
            ChatAcknowledgement(
                timestamp=datetime.now(timezone.utc),
                acknowledged_msg_id=msg.msg_id,
            ),
        )
    except Exception as ack_err:
        ctx.logger.warning(f"Failed to dispatch ChatAcknowledgement: {ack_err}")

    # 2. Check for session control signals (ACP Start/End session)
    is_start_session = any(
        isinstance(c, StartSessionContent) or getattr(c, "type", None) == "start-session"
        for c in msg.content
    )
    is_end_session = any(
        isinstance(c, EndSessionContent) or getattr(c, "type", None) == "end-session"
        for c in msg.content
    )

    # Extract conversation/session identifier if available in message content metadata or envelope
    conv_id = None
    for item in msg.content:
        if isinstance(item, MetadataContent) and hasattr(item, "metadata") and isinstance(item.metadata, dict):
            conv_id = (
                item.metadata.get("conversation_id")
                or item.metadata.get("session_id")
                or item.metadata.get("chat_id")
                or item.metadata.get("thread_id")
            )
            if conv_id:
                conv_id = str(conv_id)
                break

    if not conv_id and hasattr(ctx, "session") and ctx.session is not None:
        from unittest.mock import MagicMock
        if not isinstance(ctx.session, MagicMock):
            conv_id = str(ctx.session)

    if is_end_session:
        ctx.logger.info(f"End session received from {sender} (conv={conv_id}); clearing session state")
        orchestrator.clear_session(sender, conv_id)
        return

    # If this is a new session start, reset session state so prior conversation profile is not leaked
    if is_start_session:
        ctx.logger.info(f"New session signaled from {sender} (conv={conv_id}); initializing fresh session state")
        orchestrator.reset_session(sender, conv_id)

    # 3. Robust user text extraction
    # A ChatMessage can contain StartSessionContent AND TextContent (e.g. from Agentverse web chat).
    # We must extract all text items rather than dropping the text when a start-session signal is present.
    text_parts: list[str] = []
    for item in msg.content:
        if isinstance(item, TextContent):
            if item.text and item.text.strip():
                text_parts.append(item.text.strip())
        elif getattr(item, "type", None) == "text" and hasattr(item, "text"):
            val = str(getattr(item, "text", "")).strip()
            if val:
                text_parts.append(val)
        elif hasattr(item, "text") and isinstance(item.text, str) and item.text.strip():
            text_parts.append(item.text.strip())

    user_query = " ".join(text_parts).strip()

    # Fallback to msg.text() if available
    if not user_query and hasattr(msg, "text") and callable(msg.text):
        try:
            user_query = msg.text().strip()
        except Exception:
            pass

    # 4. If message has NO text:
    if not user_query:
        if is_start_session:
            # Empty session initiation handshake: deliver welcome greeting
            ctx.logger.info(f"Sending welcome greeting to {sender} for empty session start")
            reply = await orchestrator.handle_citizen_message(
                sender, "hello", conversation_id=conv_id, is_new_session_signal=True
            )
            await ctx.send(sender, reply)
            return
        ctx.logger.debug(f"Received empty text content from {sender}; skipping")
        return

    # 5. Process user query through orchestrator and dispatch contextually relevant response
    ctx.logger.info(f"Processing query from {sender} (conv={conv_id}): {user_query}")
    try:
        reply_message = await orchestrator.handle_citizen_message(
            sender, user_query, conversation_id=conv_id, is_new_session_signal=is_start_session
        )
        await ctx.send(sender, reply_message)
        ctx.logger.info(f"Dispatched reply message to {sender}")
    except Exception as e:
        ctx.logger.exception(f"Error handling message from {sender}: {e}")
        fallback = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            content=[
                TextContent(
                    type="text",
                    text=f"CivicBridge encountered an unexpected issue while assessing schemes: {e}. Please try again shortly.",
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
