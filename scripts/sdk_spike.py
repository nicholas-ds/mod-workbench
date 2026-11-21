"""Spike: start a Claude Agent SDK session and print every message."""

import asyncio
from dataclasses import fields

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

PROMPT = "List the names of the skills you can use. Then quote the heading of the user-level rule about GLM workers."


def describe_message(message: object) -> str:
    parts = [type(message).__name__]
    for field in fields(message):  # type: ignore[arg-type]
        value = str(getattr(message, field.name))[:200]
        parts.append(f"{field.name}={value}")
    return " ".join(parts)


async def run_spike() -> None:
    options = ClaudeAgentOptions(cwd="E:/repos/mods", setting_sources=["user", "project"])
    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        await client.query(PROMPT)
        async for message in client.receive_response():
            print(describe_message(message))
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_spike())
