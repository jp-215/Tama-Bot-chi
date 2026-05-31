# TamaBotchi

TamaBotchi is a desktop pet that lives on your Mac and handles your iMessages.

Inspired by the Tamagotchi, it is a little companion that sits on your screen — idle when things are quiet, excited when messages come in, and always working behind the scenes to keep your conversations going. When someone texts you, TamaBotchi reads the message, thinks about it using Claude AI, and sends a reply that sounds like you.

It is not just an auto-responder. It is a trusted companion that knows your voice, respects your relationships, and acts on your behalf only when you want it to.

---

## What It Does

- Watches your Mac's iMessage inbox in real time via `chat.db`
- Reads incoming messages and generates context-aware replies using Claude
- Sends replies automatically through the Messages app via AppleScript
- Shows up on your desktop as an animated bunny that reacts to your message activity — bouncing when new messages arrive, sleeping when things are quiet
- Remembers your preferences: tone, formality, which contacts to auto-reply to, and which ones to always ask you about first

---

## How It Works

```
Incoming iMessage
      │
      ▼
 chat.db (~/Library/Messages)
      │
      ▼
  watcher.py  ──────────────────────────────►  Agent API (port 5000)
  polls every 3s                                    │
                                                    │  calls Claude
                                                    ▼
                                               Claude generates reply
                                                    │
                                                    ▼
  watcher.py  ◄──────────────────────────────  returns reply text
      │
      ▼
iMessage Bridge (port 5001)
      │
      ▼
AppleScript → Messages.app → sends reply
```

**Four services run together:**

| Service | Port | Role |
|---------|------|------|
| Agent API | 5000 | Receives messages, calls Claude, returns the reply |
| iMessage Bridge | 5001 | Sends iMessages back via AppleScript |
| MCP Server | 5002 | Stores your preferences and conversation history |
| Watcher | — | Polls `chat.db`, orchestrates the full loop |

The desktop pet (`desktop-pet/`) runs as an Electron app sitting above your other windows. It polls for unread message counts and changes mood states accordingly — a visual pulse for your inbox.

---

## Prerequisites

- macOS (iMessage requires it)
- Python 3.12+
- Node.js 18+ (for the desktop pet)
- An Anthropic API key ([get one here](https://console.anthropic.com/))
- Full Disk Access granted to Terminal (required to read `chat.db`)
- iMessage configured and signed in on your Mac

### Grant Full Disk Access to Terminal

1. Open **System Settings > Privacy & Security > Full Disk Access**
2. Click **+** and add your terminal app (Terminal.app or iTerm2)
3. Restart your terminal

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Jay-tech456/Tama-Bot-chi.git
cd Tama-Bot-chi
```

### 2. Create virtual environments

Each Python service has its own venv. Run these from the repo root:

```bash
# Agent API
cd agent && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && deactivate && cd ..

# iMessage Bridge + Watcher
cd imessage-server && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install requests && deactivate && cd ..

# MCP Server
cd mcp-server && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && deactivate && cd ..
```

### 3. Configure environment

Create `agent/.env`:

```bash
cp agent/.env.example agent/.env
```

Fill in your key:

```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-haiku-4-5-20251001
IMESSAGE_SERVER_URL=http://localhost:5001
MCP_SERVER_URL=http://localhost:5002
AGENT_NAME=TamaBotchi
```

---

## Running TamaBotchi

Open four terminal tabs and run one command per tab, from the repo root.

### Terminal 1 — MCP Server

```bash
cd mcp-server && source .venv/bin/activate && uvicorn main:app --reload --port 5002
```

### Terminal 2 — iMessage Bridge

```bash
cd imessage-server && source .venv/bin/activate && uvicorn server:app --reload --port 5001
```

### Terminal 3 — Agent API

```bash
cd agent && source .venv/bin/activate && uvicorn main:app --reload --port 5000
```

### Terminal 4 — Watcher (starts auto-reply)

```bash
cd imessage-server && source .venv/bin/activate && python watcher.py
```

Once the watcher is running you should see:

```
============================================================
  TamaBotchi iMessage Auto-Reply Watcher
============================================================

[INFO] Agent API (http://127.0.0.1:5000): UP
[INFO] iMessage Server (http://127.0.0.1:5001): UP
[INFO] Starting from message ROWID XXXXX - will only respond to NEW messages
[INFO] Polling every 3 seconds...
[INFO] Waiting for incoming iMessages...
```

Send yourself an iMessage from another device. Within a few seconds:

```
[INFO] New message from +1xxxxxxxxxx: hey
[INFO] Generating AI response...
[INFO] Sending reply: Hey! ...
[INFO] Reply sent successfully to +1xxxxxxxxxx
```

### Desktop Pet (optional)

```bash
cd desktop-pet && npm install && npm run dev
```

The bunny appears in a floating window on your desktop. It bounces when new messages arrive and goes to sleep when your inbox is quiet.

---

## Configuration

All config lives in `agent/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | required | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` | Claude model used for replies |
| `AGENT_NAME` | `TamaBotchi` | Name used in the agent's system prompt |
| `IMESSAGE_SERVER_URL` | `http://localhost:5001` | iMessage bridge URL |
| `MCP_SERVER_URL` | `http://localhost:5002` | MCP server URL |
| `POLL_INTERVAL` | `3` | Seconds between `chat.db` polls |
| `HIGH_MATCH_THRESHOLD` | `0.75` | Compatibility score above which TamaBotchi replies automatically |

---

## Project Structure

```
Tama-Bot-chi/
├── agent/                    # Claude AI agent (port 5000)
│   ├── core/
│   │   ├── agent.py          # TamaBotchiAgent class + Claude integration
│   │   ├── matching.py       # Interest-based compatibility scoring
│   │   └── permissions.py    # Auto vs ask-first permission logic
│   ├── tools/
│   │   ├── imessage_tool.py  # iMessage bridge HTTP client
│   │   ├── gmail_tool.py     # Gmail + Calendar integration
│   │   └── mcp_client.py     # MCP server HTTP client
│   ├── config.py             # Loads settings from .env
│   ├── exceptions.py         # Custom exception hierarchy (TamaError base)
│   ├── tama_types.py         # TypedDict type definitions
│   └── main.py               # FastAPI server entrypoint
│
├── desktop-pet/              # Electron desktop pet (the bunny)
│   └── src/components/
│       ├── BunnyPet.tsx      # Animated pet with mood states
│       ├── ChatView.tsx      # View recent conversations
│       ├── CalendarView.tsx  # Upcoming scheduled meetings
│       └── SummaryPanel.tsx  # Activity summary
│
├── imessage-server/          # iMessage bridge + watcher (port 5001)
│   ├── server.py             # FastAPI, sends messages via AppleScript
│   └── watcher.py            # Polls chat.db, routes through agent
│
├── mcp-server/               # User data store (port 5002)
│   ├── main.py               # FastAPI — profiles, preferences, history
│   └── database.py           # SQLite via tama.db
│
└── mcp-gmail-main/           # Gmail MCP server integration
```

---

## API Reference

The Agent API (port 5000) exposes:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check across all services |
| `POST` | `/users/{user_id}/messages/incoming` | Handle incoming message, returns AI reply |
| `POST` | `/users/{user_id}/messages/send` | Send a message on behalf of a user |
| `POST` | `/users/{user_id}/detected` | Trigger outreach when a person is detected nearby |
| `GET` | `/users/{user_id}/profile` | Get user profile |
| `PATCH` | `/users/{user_id}/profile` | Update user profile |
| `GET` | `/users/{user_id}/preferences` | Get reply preferences |
| `PATCH` | `/users/{user_id}/preferences` | Update reply preferences |

---

## Troubleshooting

**"Cannot read Messages database"**
Terminal does not have Full Disk Access. Follow the grant instructions above.

**"Agent API is not running. Start it first."**
The watcher waits for all three servers before starting. Launch Terminals 1–3 first.

**Watcher detects messages but sends no reply**
Check the agent terminal for error logs. Most common cause: `ANTHROPIC_API_KEY` not set in `agent/.env`.

**"iMessage server returned 500: syntax error"**
Pull the latest version — this was a bug in AppleScript escaping that has been fixed.

**Reply goes to the wrong contact**
The watcher uses phone numbers directly from `chat.db`. Make sure numbers are in E.164 format (`+1xxxxxxxxxx`).

---

## License

MIT
