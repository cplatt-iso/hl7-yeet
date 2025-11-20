# HL7 Yeeter

It yeets HL7 messages. It parses them. It simulates them. It uses AI because apparently everything has to use AI now.

This is a full-stack application for dealing with the absolute joy that is the HL7 v2 standard. If you enjoy counting pipes and carets, you might like this. If you don't, this tool might make your life slightly less miserable.

## What it actually does

- **Parses HL7**: Paste your garbage message string and see it broken down into segments and fields. You can even drag them around if you feel like creating invalid messages.
- **Sends MLLP**: It's a client. It connects to an endpoint and pushes data. It waits for an ACK. Groundbreaking stuff.
- **Receives MLLP**: It listens on a port. It logs what it gets. It sends an ACK back so the sender shuts up.
- **AI Analysis**: We hooked up Google Gemini so you can ask it why your message is broken. It usually knows. Sometimes it hallucinates. Good luck.
- **Simulation Engine**: Generates fake patient data so you don't have to use real PHI and get fired. It can run multi-step workflows (Generate -> Send -> Wait -> Repeat).
- **ExamGen**: A new, overly complicated system for generating consistent exam data (`ExamSpec`) because random strings weren't good enough for you people.

## The Stack

It's 2025, so obviously it's containerized.

- **Backend**: Python 3.11 + Flask. It uses SocketIO because polling is for peasants.
- **Frontend**: React + Vite. TailwindCSS is involved because writing CSS is hard.
- **Database**: PostgreSQL.
- **Deployment**: Docker Compose. If you try to run this on bare metal, you're on your own.

## Prerequisites

- **Docker & Docker Compose**: If you don't have these, go get them.
- **Git**: To get the code.
- **A sense of humor**: Required for dealing with HL7.

## Setup

### 1. Clone it
```bash
git clone https://github.com/cplatt-iso/hl7-yeet.git
cd hl7-yeet
```

### 2. Config
Make a `.env` file. Don't commit it.
```env
GOOGLE_API_KEY="your_gemini_key" # Optional, if you want the AI to judge your messages
DATABASE_URL="postgresql://user:pass@db:5432/yeeter"
JWT_SECRET_KEY="change_this_to_something_random"
```

### 3. Run it
```bash
docker compose up --build -d
```
If it fails, check your logs before opening an issue.

### 4. Use it
Go to `http://localhost:5001`.
Login. If you haven't registered, do that first. It's not rocket science.

## CLI Tool
For those who hate GUIs or need to script things.

```bash
# Login (saves token to ~/.yeeter/config.json)
python scripts/yeeter_cli.py login --username admin --password admin

# List templates
python scripts/yeeter_cli.py templates list

# Yeet something
python scripts/yeeter_cli.py runs start --template-id 1 --patients 10

# Watch it happen
python scripts/yeeter_cli.py runs watch <run_id>
```

## Development

If you want to contribute, great. If you break it, you fix it.

- **Backend**: `app/`
- **Frontend**: `src/`
- **Tests**: `tests/` (Yes, we have some. Run them.)

## License
Do whatever you want, just don't blame me if it breaks production.
