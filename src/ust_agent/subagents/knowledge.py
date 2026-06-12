"""Knowledge sub-agent.

Exposes UST's prior-work retrieval as a DeepAgents sub-agent.
The orchestrator calls this agent by name; it answers with code snippets
and citations from the pgvector knowledge store.

Usage (standalone):
    from ust_agent.subagents.knowledge import build_knowledge_agent, ask
    answer = ask("Has UST built a CSV parser before?")
    print(answer)
"""
from __future__ import annotations

import logging

import deepagents
from langchain_core.tools import tool

from ust_agent.gateway import resolve_model
from ust_agent.knowledge.retrieve import retrieve, format_for_prompt

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the UST Knowledge Agent. Your job is to answer questions about
prior UST code by searching the knowledge store.

When asked whether UST has built something, ALWAYS call retrieve_knowledge
first. Include citations (file path, symbol, commit) in your answer.
Flag any deprecated snippets clearly.

If no relevant snippets are found, say so explicitly — do not fabricate code.
"""


@tool
def retrieve_knowledge(query: str, top_k: int = 5) -> str:
    """Search UST's knowledge store for prior code matching the query.

    Returns formatted code snippets with citations (repo/path:symbol@commit).
    Deprecated snippets are flagged with a ⚠ warning.
    """
    citations = retrieve(query, top_k=top_k)
    return format_for_prompt(citations)


def build_knowledge_agent(
    data_class: str = "internal",
) -> deepagents.CompiledSubAgent:
    """Build and return the Knowledge sub-agent.

    The sub-agent has a single tool: retrieve_knowledge.
    Its model is resolved through the gateway using the 'knowledge_retrieval' role.
    """
    model = resolve_model("knowledge_retrieval", data_class)

    agent = deepagents.create_deep_agent(
        model=model,
        tools=[retrieve_knowledge],
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
