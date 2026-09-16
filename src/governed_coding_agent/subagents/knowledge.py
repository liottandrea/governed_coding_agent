"""Knowledge sub-agent.

Exposes prior-work retrieval as a DeepAgents sub-agent.
The orchestrator calls this agent by name; it answers with code snippets
and citations from the pgvector knowledge store.

Usage (standalone):
    from governed_coding_agent.subagents.knowledge import build_knowledge_agent, ask
    answer = ask("Has this project built a CSV parser before?")
    print(answer)
"""
from __future__ import annotations

import logging

import deepagents

from governed_coding_agent.gateway import resolve_model
from governed_coding_agent.knowledge.retrieve import retrieve_knowledge_tool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Governed Coding Agent's Knowledge sub-agent. Your job is to answer questions about
prior code by searching the knowledge store.

When asked whether this project has built something, ALWAYS call retrieve_knowledge_tool
first. Include citations (file path, symbol, commit) in your answer.
Flag any deprecated snippets clearly.

If no relevant snippets are found, say so explicitly — do not fabricate code.
"""


def build_knowledge_agent(
    data_class: str = "internal",
) -> deepagents.CompiledSubAgent:
    """Build and return the Knowledge sub-agent.

    The sub-agent has a single tool: retrieve_knowledge_tool.
    Its model is resolved through the gateway using the 'knowledge_retrieval' role.
    """
    model = resolve_model("knowledge_retrieval", data_class)

    agent = deepagents.create_deep_agent(
        model=model,
        tools=[retrieve_knowledge_tool],
        system_prompt=_SYSTEM_PROMPT,
        name="knowledge",
    )
    return agent


def ask(question: str, data_class: str = "internal") -> str:
    """Convenience function: build the agent, ask a question, return the answer."""
    from langchain_core.messages import HumanMessage

    agent = build_knowledge_agent(data_class=data_class)
    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    messages = result.get("messages", [])
    return messages[-1].content if messages else ""
