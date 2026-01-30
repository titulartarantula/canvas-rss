# Canvas RSS Aggregator

A daily RSS feed aggregator for Canvas LMS release notes, community discussions, and status updates.

## Quick Start

```bash
# Read the spec
specs/canvas-rss.md

# Check current state
STATE.md

# Run locally
python src/main.py

# Run tests
pytest tests/ -v
```

## Project Overview

**Purpose:** Aggregate Canvas LMS release notes, API changes, and user feedback into a single daily RSS feed for educational technologists at U of T.

**Tech Stack:**
- Python 3.11+
- Playwright (web scraping)
- PRAW (Reddit API)
- Google Gemini API (summarization)
- feedgen (RSS generation)
- SQLite (deduplication/history)
- Docker (deployment)

## Agent Instructions

Each agent has dedicated instructions:

| Agent | File | Role |
|-------|------|------|
| Coding | [agents/CODING.md](agents/CODING.md) | Write implementation code |
| Testing | [agents/TESTING.md](agents/TESTING.md) | Write and run tests |
| DevOps | [agents/DEVOPS.md](agents/DEVOPS.md) | Docker and deployment |

## Workflow

```
1. Check STATE.md for current task assignment
2. Read your agent file (agents/CODING.md, etc.)
3. Reference specs/canvas-rss.md for detailed requirements
4. Complete assigned work
5. Update STATE.md with progress
6. Hand off to next agent if needed
```

## Key Files

| File | Purpose |
|------|---------|
| `specs/canvas-rss.md` | Complete technical specification |
| `STATE.md` | Current tasks and project state |
| `config/config.yaml` | Configuration settings |
| `src/main.py` | Application entry point |

## Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

## Environment Variables

Required in `.env`:

```bash
GEMINI_API_KEY=your_gemini_api_key
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=canvas-rss-aggregator:v1.0
```

Optional:
- `TEAMS_WEBHOOK_URL` - MS Teams webhook for notifications

## Directory Structure

```
canvas-rss/
├── CLAUDE.md              # This file - project overview
├── STATE.md               # Task tracking
├── agents/
│   ├── CODING.md          # Coding agent instructions
│   ├── TESTING.md         # Testing agent instructions
│   └── DEVOPS.md          # DevOps agent instructions
├── specs/
│   └── canvas-rss.md      # Technical specification
├── src/                   # Application code
├── tests/                 # Test suite
├── config/                # Configuration files
├── data/                  # SQLite database (gitignored)
├── output/                # RSS feed output (gitignored)
└── logs/                  # Application logs (gitignored)
```
