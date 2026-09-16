#!/usr/bin/env bash
# start.sh — Governed Coding Agent startup script
#
# Checks all prerequisites, starts Docker services, waits for health,
# initialises the database, ingests seed knowledge, and launches the
# Headroom proxy. Leaves you ready to run `governed-coding-agent`.
#
# Usage:
#   ./start.sh              # full startup
#   ./start.sh --check      # prerequisite check only, no side effects
#   ./start.sh --stop       # stop Docker services and Headroom proxy
#   ./start.sh --status     # show status of running services
#
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET}  $*"; }
info() { echo -e "  ${CYAN}→${RESET}  $*"; }
banner() { echo -e "\n${BOLD}$*${RESET}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERRORS=0

# ── Argument parsing ──────────────────────────────────────────────────────────
MODE="start"
case "${1:-}" in
  --check)  MODE="check"  ;;
  --stop)   MODE="stop"   ;;
  --status) MODE="status" ;;
esac

# ── Stop mode ─────────────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
  banner "Stopping Governed Coding Agent services"
  cd "$SCRIPT_DIR"
  docker compose down && ok "Docker services stopped" || warn "docker compose down failed"
  pkill -f "headroom proxy" 2>/dev/null && ok "Headroom proxy stopped" || warn "Headroom was not running"
  exit 0
fi

# ── Status mode ───────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
  banner "Governed Coding Agent — service status"
  cd "$SCRIPT_DIR"
  echo ""
  docker compose ps 2>/dev/null || warn "docker compose not available"
  echo ""
  if curl -sf http://localhost:18787/health >/dev/null 2>&1; then
    VERSION=$(curl -sf http://localhost:18787/health | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "?")
    ok "Headroom proxy  http://localhost:18787  (v${VERSION})"
  else
    warn "Headroom proxy  not running"
  fi
  if curl -sf http://localhost:13000/api/public/health >/dev/null 2>&1; then
    ok "Langfuse        http://localhost:13000"
  else
    warn "Langfuse        not responding"
  fi
  PG_OK=$(docker compose exec -T postgres pg_isready -U governed_agent -d governed_agent 2>/dev/null | grep "accepting" || true)
  if [[ -n "$PG_OK" ]]; then
    ok "Postgres        localhost:15432"
  else
    warn "Postgres        not ready"
  fi
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
banner "╔══════════════════════════════════════════════╗"
echo -e "${BOLD}║     Governed Coding Agent — startup check    ║${RESET}"
banner "╚══════════════════════════════════════════════╝"
echo ""
cd "$SCRIPT_DIR"

# ── SECTION 1: Prerequisites ──────────────────────────────────────────────────
banner "1 / 5  Prerequisites"

# uv
if command -v uv &>/dev/null; then
  ok "uv  $(uv --version)"
else
  fail "uv not found — install from https://docs.astral.sh/uv/"
  (( ERRORS++ ))
fi

# Docker
if command -v docker &>/dev/null; then
  if docker info &>/dev/null; then
    ok "Docker  $(docker --version | cut -d' ' -f3 | tr -d ',')"
  else
    info "Docker daemon not running — starting Docker Desktop..."
    open -a Docker 2>/dev/null || true
    RETRIES=0
    until docker info &>/dev/null; do
      RETRIES=$(( RETRIES + 1 ))
      if [[ "$RETRIES" -ge 30 ]]; then
        fail "Docker daemon did not start after 60s — open Docker Desktop manually and re-run"
        (( ERRORS++ ))
        break
      fi
      sleep 2
    done
    if docker info &>/dev/null; then
      ok "Docker  $(docker --version | cut -d' ' -f3 | tr -d ',')  (just started)"
    fi
  fi
else
  fail "docker not found — install Docker Desktop"
  (( ERRORS++ ))
fi

# docker compose (v2 plugin)
if docker compose version &>/dev/null; then
  ok "docker compose  $(docker compose version --short 2>/dev/null || echo 'ok')"
else
  fail "docker compose plugin not found"
  (( ERRORS++ ))
fi

# Python ≥ 3.12
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 12 ]]; then
  ok "Python  ${PY_VER}"
else
  fail "Python ≥ 3.12 required (found ${PY_VER})"
  (( ERRORS++ ))
fi

# RTK (optional — warns but doesn't block)
if command -v rtk &>/dev/null; then
  ok "RTK  $(rtk --version 2>/dev/null | head -1)"
else
  warn "rtk not found — token savings disabled (install: curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh)"
fi

# Headroom (optional — warns but doesn't block)
if command -v headroom &>/dev/null; then
  ok "Headroom  $(headroom --version 2>/dev/null | head -1)"
else
  warn "headroom not found — proxy compression disabled (install: uv tool install 'headroom-ai[all]')"
fi

# AWS profile
AWS_PROF="${AWS_PROFILE:-genai-agent-user}"
if aws configure list --profile "$AWS_PROF" &>/dev/null; then
  ok "AWS profile  '${AWS_PROF}'"
else
  warn "AWS profile '${AWS_PROF}' not found — Bedrock calls will fail"
  warn "  Configure with: aws configure --profile ${AWS_PROF}"
fi

# .env file
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  ok ".env  found"
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/.env"
else
  warn ".env not found — copying from .env.example"
  if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    warn "  Copied .env.example → .env  (review and fill in secrets before use)"
    source "$SCRIPT_DIR/.env"
  else
    fail ".env.example also missing"
    (( ERRORS++ ))
  fi
fi

# Langfuse keys (warn only — seeded by docker-compose on first boot)
LF_PK="${LANGFUSE_PUBLIC_KEY:-}"
LF_SK="${LANGFUSE_SECRET_KEY:-}"
if [[ -z "$LF_PK" || -z "$LF_SK" ]]; then
  warn "LANGFUSE_PUBLIC_KEY / SECRET_KEY not set in .env"
  warn "  They will be seeded automatically by docker-compose."
  warn "  After first boot, copy from http://localhost:13000 → Settings → API Keys"
fi

# Hard stop if critical prerequisites are missing
if [[ "$ERRORS" -gt 0 ]]; then
  echo ""
  fail "${ERRORS} critical prerequisite(s) missing — fix them and re-run."
  exit 1
fi

[[ "$MODE" == "check" ]] && { echo ""; ok "All prerequisites satisfied."; exit 0; }

# ── SECTION 2: Python dependencies ───────────────────────────────────────────
banner "2 / 5  Python dependencies"
if uv sync --quiet 2>/dev/null; then
  ok "uv sync  complete"
else
  info "Running uv sync (first time may take a moment)..."
  uv sync
  ok "uv sync  complete"
fi

# Touch source files so Python's .pyc cache never silently serves stale bytecode.
touch "$SCRIPT_DIR"/src/governed_coding_agent/*.py "$SCRIPT_DIR"/src/governed_coding_agent/**/*.py 2>/dev/null || true
find "$SCRIPT_DIR/src/governed_coding_agent" -name "*.pyc" -delete 2>/dev/null || true

# Install governed-coding-agent as a global tool (editable) so it's on $PATH from any directory.
# --reinstall ensures updates are always picked up.
if uv tool install --editable "$SCRIPT_DIR" --reinstall --quiet 2>/dev/null; then
  ok "governed-coding-agent installed globally  (uv tool install -e . --reinstall)"
else
  warn "Could not install governed-coding-agent globally — run: uv tool install -e . --reinstall"
fi

# ── SECTION 3: Docker services ───────────────────────────────────────────────
banner "3 / 5  Docker services  (Postgres + Langfuse)"
docker compose up -d
info "Waiting for Postgres to be healthy..."
RETRIES=0
until docker compose exec -T postgres \
      pg_isready -U governed_agent -d governed_agent &>/dev/null; do
  RETRIES=$(( RETRIES + 1 ))
  if [[ "$RETRIES" -ge 30 ]]; then
    fail "Postgres did not become healthy after 30 retries"
    exit 1
  fi
  sleep 2
done
ok "Postgres  ready"

info "Waiting for Langfuse to be ready..."
RETRIES=0
until curl -sf http://localhost:13000/api/public/health &>/dev/null; do
  RETRIES=$(( RETRIES + 1 ))
  if [[ "$RETRIES" -ge 45 ]]; then
    warn "Langfuse not responding after 90s — continuing anyway"
    break
  fi
  sleep 2
done
if curl -sf http://localhost:13000/api/public/health &>/dev/null; then
  ok "Langfuse  ready  →  http://localhost:13000"
fi

# ── SECTION 4: Database initialisation ───────────────────────────────────────
banner "4 / 5  Database initialisation"
info "Creating pgvector schema (idempotent)..."
uv run python scripts/init_db.py
ok "Schema ready  (code_chunks + vector index)"

info "Ingesting seed knowledge corpus..."
CHUNK_COUNT=$(uv run python -c "
from governed_coding_agent.knowledge.ingest import ingest_seed
print(ingest_seed())
" 2>/dev/null)
if [[ -n "$CHUNK_COUNT" && "$CHUNK_COUNT" -gt 0 ]]; then
  ok "Seed corpus  ${CHUNK_COUNT} chunk(s) in pgvector"
else
  ok "Seed corpus  already up to date"
fi

# ── SECTION 5: Headroom proxy ─────────────────────────────────────────────────
banner "5 / 5  Headroom proxy"
HEADROOM_PORT="${HEADROOM_PORT:-18787}"

if curl -sf "http://localhost:${HEADROOM_PORT}/livez" &>/dev/null; then
  ok "Headroom already running on port ${HEADROOM_PORT}"
elif command -v headroom &>/dev/null; then
  info "Starting Headroom proxy on port ${HEADROOM_PORT}..."
  mkdir -p "$SCRIPT_DIR/.headroom/logs"
  headroom proxy \
    --port "$HEADROOM_PORT" \
    --no-ccr-inject-tool \
    --no-telemetry \
    > "$SCRIPT_DIR/.headroom/logs/proxy.log" 2>&1 &
  HEADROOM_PID=$!
  echo "$HEADROOM_PID" > "$SCRIPT_DIR/.headroom/proxy.pid"
  # Wait up to 10s for it to bind
  RETRIES=0
  until curl -sf "http://localhost:${HEADROOM_PORT}/livez" &>/dev/null; do
    RETRIES=$(( RETRIES + 1 ))
    if [[ "$RETRIES" -ge 10 ]]; then
      warn "Headroom did not start within 10s — check .headroom/logs/proxy.log"
      break
    fi
    sleep 1
  done
  if curl -sf "http://localhost:${HEADROOM_PORT}/livez" &>/dev/null; then
    ok "Headroom proxy  http://localhost:${HEADROOM_PORT}  (pid ${HEADROOM_PID})"
  fi
else
  warn "headroom not installed — skipping proxy (install: uv tool install 'headroom-ai[all]')"
fi

# ── Ready ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  Governed Coding Agent is ready.${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${BOLD}Start a session:${RESET}"
echo -e "    governed-coding-agent"
echo ""
echo -e "  ${BOLD}Run the demo:${RESET}"
echo -e "    uv run python scripts/demo.py"
echo ""
echo -e "  ${BOLD}Observability:${RESET}"
echo -e "    Langfuse  →  http://localhost:13000  (log in with LANGFUSE_INIT_USER_EMAIL / LANGFUSE_INIT_USER_PASSWORD from your .env)"
if curl -sf "http://localhost:${HEADROOM_PORT}/livez" &>/dev/null; then
  echo -e "    Headroom  →  http://localhost:${HEADROOM_PORT}/stats"
fi
echo ""
echo -e "  ${BOLD}Stop everything:${RESET}"
echo -e "    ./start.sh --stop"
echo ""
