# UST Coding Agent

Model-neutral, governed coding agent built on [DeepAgents](https://github.com/anthropics/deepagents) + LangGraph.

Given a delivery feature request it:
1. **Retrieves** prior UST code patterns from a pgvector knowledge store
2. **Authors** a UST-styled Python module grounded in those patterns (HITL gate)
3. **Generates** a parametrized pytest suite for the module (HITL gate)
4. **Executes** both in the built-in sandbox and reports citations + pass/fail
5. **Traces** every model call to Langfuse

All model calls route through a LiteLLM gateway. The data-class policy prevents
sensitive code from ever reaching an external API.

---

## Using as a coding assistant

`ust-agent` is a terminal-based coding assistant — a governed, knowledge-grounded
alternative to Claude Code. Run it inside any project directory.

```bash
# Interactive REPL (like running `claude`)
ust-agent

# Single-shot task
ust-agent "Refactor the CSV parser to use our retry decorator pattern"

# Resume a previous session (persisted in Postgres — survives restarts)
ust-agent --session <thread-id>

# List all saved sessions
ust-agent --list-sessions

# Restricted data — routes to local Ollama, never Bedrock
ust-agent --data-class restricted

# Non-interactive / CI
ust-agent --auto-approve "Add type hints to all public functions in src/"
```

### What happens in a session

```
╔══════════════════════════════════════════════════════╗
║          UST Coding Agent  —  interactive            ║
║  Type your task. 'exit' or Ctrl+C to quit.          ║
╚══════════════════════════════════════════════════════╝
  session   : a3f2c8d1-4e9b-4f1a-b2c3-d4e5f6a7b8c9
  data class: internal
  directory : /Users/you/projects/my-service
  resume    : ust-agent --session a3f2c8d1-...
  history   : persisted in Postgres

▶ Add input validation to the payment processor

  ⚠  write_file
     write → src/payments/processor.py  (84 lines)
  Approve? [Y/n]

[agent writes the file, runs the tests, reports results]

▶ Now write tests for it
...
```

For every task the agent:
1. Calls `retrieve_knowledge_tool` to find relevant UST prior patterns
2. Reads your existing files with `read_file` / `glob` / `grep`
3. Writes or edits code — pausing for your approval before touching the filesystem
4. Runs `execute` to verify (tests, linters) — again with approval
5. Cites the UST pattern used at the top of any new file

### Session persistence

Sessions are stored in the same Postgres instance used for pgvector
(`langgraph-checkpoint-postgres`). The full conversation history — every message,
tool call, and agent decision — survives process restarts.

```bash
# See all your saved sessions
ust-agent --list-sessions

# Thread ID   Created              Turns
# ─────────────────────────────────────────────────────────────────────
# a3f2c8d1-…  2026-06-15 09:12:00  14
# 7b1e4f22-…  2026-06-14 16:45:00  6

# Pick up exactly where you left off
ust-agent --session a3f2c8d1-4e9b-4f1a-b2c3-d4e5f6a7b8c9
```

The checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`)
are created automatically on first run via `checkpointer.setup()`.

---

## Quick start

### One-command startup

```bash
git clone <repo-url> && cd ust_coding_agent
cp .env.example .env          # fill in AWS_PROFILE at minimum
./start.sh                    # checks prerequisites, starts everything, seeds DB
ust-agent                     # open the interactive REPL
```

`start.sh` is idempotent — safe to re-run at any time. It:
1. Checks all prerequisites (Docker, uv, Python ≥ 3.12, AWS profile, `.env`)
2. Runs `uv sync` to install Python dependencies
3. Starts Docker services (Postgres + Langfuse) and waits for health
4. Initialises the pgvector schema and ingests the seed knowledge corpus
5. Launches the Headroom proxy on `:8787` (if installed)
6. Prints the ready summary with all service URLs

```bash
./start.sh --check    # prerequisite check only, no side effects
./start.sh --status   # show what's running right now
./start.sh --stop     # stop Docker services and Headroom proxy
```

### Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| Python | ≥ 3.12 | via system or pyenv |
| [uv](https://docs.astral.sh/uv/) | yes | dependency manager + entry points |
| Docker + Compose v2 | yes | for Postgres/pgvector + Langfuse |
| AWS CLI + profile | yes | Bedrock-capable IAM profile |
| [RTK](https://github.com/rtk-ai/rtk) | optional | terminal token compression |
| [Headroom](https://github.com/chopratejas/headroom) | optional | proxy compression |

### Manual setup (if you prefer step-by-step)

```bash
# Copy and fill in secrets
cp .env.example .env

# Start Postgres (pgvector) + Langfuse
docker compose up -d

# Install Python dependencies
uv sync

# Initialise the database schema
uv run python scripts/init_db.py

# Ingest the seed UST code corpus into pgvector
uv run python -c "from ust_agent.knowledge.ingest import ingest_seed; print(ingest_seed(), 'chunks ingested')"

# Smoke test — no API call
uv run python scripts/hello_world.py

# Full end-to-end demo
uv run python scripts/demo.py
```

---

## Usage guide

### Run the accelerator demo

```bash
# Default task (phone validator module + tests)
uv run python scripts/demo.py

# Custom task
uv run python scripts/demo.py "Build a rate-limiter utility following UST patterns"
```

The demo runs two agents automatically (HITL auto-approved) and prints:

```
Step 1 — Code Authoring   frontier model, Bedrock
Step 2 — Testing          cheap → mid cascade, Bedrock
...
DELIVERY SUMMARY
  Code file   /ust_workspace/ust_<module>.py
  Test file   /ust_workspace/test_ust_<module>.py
  Total       ~4 min
```

### Call sub-agents directly from Python

```python
from ust_agent.subagents.code_authoring import run as ca_run
from ust_agent.subagents.testing import run as test_run
from ust_agent.subagents.knowledge import ask

# Ask the knowledge store a question
answer = ask("Has UST built a retry decorator before?")
print(answer)

# Generate a module (interactive HITL by default)
result = ca_run(
    "Build a UST-styled JSON schema validator",
    data_class="internal",
    auto_approve=False,   # set True to skip prompts
)
print(result["files"])   # virtual filesystem state

# Generate tests for the output
test_result = test_run(
    "Write pytest tests for /ust_workspace/ust_json_validator.py",
    data_class="internal",
    auto_approve=True,
)
```

### Use the top-level orchestrator

```python
from ust_agent.harness import run

result = run(
    "Write a CSV → Postgres ETL pipeline following UST data-engineering patterns",
    role="planner",
    data_class="internal",
    auto_approve=False,
)
# result: {messages, files, thread_id, approved}
```

### Add your own code to the knowledge store

Drop `.py` files into `seed/`. Files with `_deprecated` in the filename are
automatically flagged as deprecated (still retrieved but marked with ⚠).

```bash
cp my_ust_module.py seed/
uv run python -c "
from ust_agent.knowledge.ingest import ingest_seed
print(ingest_seed(), 'chunks ingested')
"
```

Or ingest individual chunks programmatically:

```python
from ust_agent.knowledge.ingest import chunk_python_file, load_chunks

source = Path("my_module.py").read_text()
chunks = chunk_python_file(source, path="my_module.py", repo="my-project")
load_chunks(chunks, data_class="internal")
```

### Data-class policy

Every task carries a `data_class` that controls which model groups may be used:

| Data class | Allowed groups | Use when |
|------------|---------------|----------|
| `public` | all | No sensitivity |
| `internal` | Bedrock + local | Default for UST delivery work |
| `restricted` | local only (`local_fast`, `local_standard`, `local_heavy`) | Regulated or confidential code |

```python
# Restricted: never leaves the machine — routes to Ollama
result = ca_run("Refactor this payroll module", data_class="restricted")
```

### HITL approval

When `auto_approve=False` (the default) the agent pauses before every
`write_file` or `execute` action and asks:

```
⚠  Approval required: write_file
   Args: {'file_path': '/ust_workspace/ust_validator.py', 'content': '...'}
   Approve? [y/n]
```

`y` / Enter → approve and continue  
`n` → reject with an optional reason (agent receives the rejection and replans)

### Model groups

| Group | Model | Used by |
|-------|-------|---------|
| `frontier` | Claude Sonnet 4.6 (Bedrock) | `codegen` role |
| `mid` | Claude Sonnet 4.5 (Bedrock) | `planner`, `knowledge_retrieval`, cascade fallback |
| `cheap` | Claude Haiku 4.5 (Bedrock) | `testing`, `embedding`, `summary` |
| `local_fast` | phi4-mini (Ollama) | restricted data, fast iteration |
| `local_standard` | devstral (Ollama) | restricted data, standard tasks |
| `local_heavy` | qwen3.6:35b (Ollama) | restricted data, heavy reasoning |

The `testing` role has a **routing cascade**: Haiku is tried first; any error
transparently promotes to Sonnet. To add a cascade to another role, add
`fallback_group: <group>` to that role in `config/routing-rules.yaml`.

---

## Architecture

```
scripts/
  demo.py                  ← end-to-end accelerator demo (Phase 6)
  init_db.py               ← create pgvector schema
  hello_world.py           ← Phase 0 smoke test
  phase[1-5]_verify.py     ← per-phase acceptance scripts

src/ust_agent/
  harness.py               ← top-level orchestrator (DeepAgents + HITL)
  gateway.py               ← LiteLLM gateway; resolve_model() + CascadingChatModel
  policy.py                ← data-class policy enforcement (PolicyError)
  observability.py         ← Langfuse callback wiring (idempotent)
  subagents/
    knowledge.py           ← Knowledge sub-agent (retrieval + citations)
    code_authoring.py      ← Code Authoring sub-agent (UST style + HITL)
    testing.py             ← Testing sub-agent (pytest generation + cascade)
  knowledge/
    ingest.py              ← tree-sitter chunking + embed + pgvector upsert
    retrieve.py            ← pgvector cosine search + Citation dataclass
  skills/
    code-authoring/SKILL.md  ← UST Python style guide injected into agent prompt
    testing/SKILL.md         ← UST pytest style guide injected into agent prompt

config/
  litellm.config.yaml      ← model group → Bedrock/Ollama model ID
  routing-rules.yaml       ← role → group mapping (+ optional fallback_group)
  data-classes.yaml        ← allowed groups per data class

seed/                      ← curated UST code corpus (ingested into pgvector)
docker-compose.yml         ← postgres:pgvector16 + langfuse:2
```

### Request flow

```
demo.py / your code
  │
  ├─ code_authoring.run()
  │     │
  │     ├─ gateway.resolve_model("codegen", data_class)
  │     │     └─ policy check → frontier (Bedrock Sonnet 4.6)
  │     │
  │     └─ create_deep_agent(model, tools=[retrieve_knowledge_tool, write_file, execute])
  │           │
  │           ├─ retrieve_knowledge_tool → pgvector → citations
  │           ├─ write_file ──────────────────────────────────── HITL gate
  │           └─ execute ─────────────────────────────────────── HITL gate
  │
  └─ testing.run()
        │
        ├─ gateway.resolve_model("testing", data_class)
        │     └─ CascadingChatModel(primary=Haiku, fallback=Sonnet)
        │
        └─ create_deep_agent(model, tools=[retrieve_knowledge_tool, write_file, execute])
              │
              ├─ retrieve_knowledge_tool → pgvector → test patterns
              ├─ write_file ──────────────────────────────────── HITL gate
              └─ execute (pytest) ────────────────────────────── HITL gate
```

All model calls emit traces to Langfuse at `http://localhost:3000`.

---

## Environment variables

Copy `.env.example` to `.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_PROFILE` | yes | AWS named profile with Bedrock permissions |
| `AWS_DEFAULT_REGION` | yes | Bedrock region (`us-east-1`) |
| `LANGFUSE_PUBLIC_KEY` | yes | From Langfuse → Settings → API Keys |
| `LANGFUSE_SECRET_KEY` | yes | From Langfuse → Settings → API Keys |
| `LANGFUSE_HOST` | yes | `http://localhost:3000` for local docker |
| `POSTGRES_*` | yes | Match values in `docker-compose.yml` |
| `OLLAMA_BASE_URL` | no | Only needed for local/restricted routing |
| `DEFAULT_DATA_CLASS` | no | `internal` (default) |

Langfuse keys are seeded automatically by docker-compose. Retrieve them from
`http://localhost:3000` → Settings → API Keys after first `docker compose up -d`.

---

## Observability

Every run is traced. Open `http://localhost:3000` with:

```
email:    admin@ust-agent.local
password: UstAgent2024!
```

Each trace shows the full model call chain: token counts, latency per step,
and which model group was used (useful for verifying cascade behaviour).

---

## Development

```bash
uv run pytest                          # 61 tests
uv run pytest tests/test_phase5.py -v  # routing cascade tests only

uv run python scripts/phase4_verify.py  # Code Authoring live demo
uv run python scripts/phase5_verify.py  # cascade + Testing live demo
uv run python scripts/demo.py           # full end-to-end
```

### Adding a new sub-agent

1. Create `src/ust_agent/subagents/<name>.py` following the pattern in `testing.py`
2. Add a skill guide at `src/ust_agent/skills/<name>/SKILL.md`
3. Add a role entry in `config/routing-rules.yaml`
4. Wire it into `demo.py` or call `run()` directly

### Upgrading dependencies

1. Branch: `git checkout -b bump/<package>-X.Y.Z`
2. Edit version in `pyproject.toml`, run `uv lock`
3. Run `uv run pytest && uv run python scripts/demo.py`
4. Review behaviour diff, merge, update the pinned versions table below

---

## Pinned dependency versions

| Package | Version |
|---------|---------|
| `deepagents` | **0.6.8** |
| `langgraph` | **1.2.4** |
| `langchain` | **1.3.8** |
| `litellm` | **1.88.1** |
| `langfuse` | **2.60.10** |
| `tree-sitter` | **0.25.2** |
| `tree-sitter-python` | **0.25.0** |
| `pgvector` | **0.3.x** |

Upgrade quarterly or when a needed fix lands upstream — never automatically.
