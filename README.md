# UST Coding Agent

Model-neutral, governed coding agent built on DeepAgents.
Takes a delivery task, grounds it in prior UST work, produces UST-styled code,
executes it in a sandbox, and traces every run end-to-end through Langfuse.

## Pinned dependency versions

| Package | Version |
|---------|---------|
| `deepagents` | **0.6.8** |
| `langgraph` | **1.2.4** |
| `langchain` | **1.3.8** |
| `litellm` | **1.88.1** |
| `langfuse` | **2.60.10** |

> To upgrade: bump the version in `pyproject.toml`, run `uv lock`, run `uv run pytest`
> and the Phase 6 smoke test, review behaviour changes, then merge. Do this quarterly
> or when a needed fix lands upstream — never automatically.

## Quick start

```bash
# 1. Copy and fill in secrets
cp .env.example .env

# 2. Start Postgres + pgvector + Langfuse
docker compose up -d

# 3. Install dependencies
uv sync

# 4. Phase 0 acceptance check (no API call needed)
uv run python scripts/hello_world.py

# 5. Run the Phase 6 demo (requires ANTHROPIC_API_KEY)
uv run python scripts/demo.py "Write a Python function that parses UST invoice CSV files"
```

## Architecture

```
scripts/demo.py          ← single entry point for the accelerator demo
src/ust_agent/
  harness.py             ← DeepAgents orchestrator (high-level API only)
  gateway.py             ← LiteLLM client + routing helpers
  policy.py              ← data-class policy enforcement
  observability.py       ← Langfuse wiring
  subagents/
    knowledge.py         ← Knowledge sub-agent (retrieval + citations)
    code_authoring.py    ← Code Authoring sub-agent (UST style + sandbox)
  knowledge/
    ingest.py            ← tree-sitter chunking + embedding + pgvector load
    retrieve.py          ← pgvector query + citation assembly
  skills/
    code-authoring/SKILL.md  ← UST code style spec
config/
  litellm.config.yaml    ← model group definitions
  routing-rules.yaml     ← role → model group mapping
  data-classes.yaml      ← data class policy
seed/                    ← curated UST code corpus for the demo
```

## Upgrade discipline

1. Create a branch: `git checkout -b bump/deepagents-X.Y.Z`
2. Update the version in `pyproject.toml`
3. Run `uv lock` to resolve
4. Run `uv run pytest && uv run python scripts/hello_world.py`
5. Review the behaviour diff
6. Merge and update the table above

## Development

```bash
uv run pytest           # unit tests
uv run python scripts/hello_world.py   # Phase 0 smoke test
```
