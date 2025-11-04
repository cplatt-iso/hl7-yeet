# HL7 Yeeter 🚀


HL7 Yeeter is a modern, full-stack web application for HL7 message simulation, analysis, and integration. It provides:

- A rich, interactive interface for parsing, editing, sending, and receiving HL7 messages over MLLP (Minimal Lower Layer Protocol)
- AI-powered HL7 message analysis and correction (Gemini integration)
- Simulation engine for generating HL7 and DICOM messages, sending to endpoints, and orchestrating complex workflows
- Real-time logging and feedback via WebSockets
- User authentication (JWT, Google OAuth)
- Fully containerized deployment with Docker Compose


## Core Features

- **Interactive HL7 Parser & Editor**: Paste or type an HL7 message and see it instantly broken down into a structured, color-coded, and editable format. Drag-and-drop fields, real-time message rebuilding, and template support.
- **MLLP Client & Server**: Send HL7 messages to any MLLP endpoint and view ACK/NACK responses. Built-in MLLP listener for receiving messages and real-time log display.
- **AI-Powered Analyzer**: Use Gemini AI to analyze, explain, and correct HL7 messages.
- **Simulation Engine**: Orchestrate multi-step workflows (generate HL7/DICOM, send via MLLP/DICOM, wait, etc.) with context extraction and logging. See `app/util/simulation_runner.py`.
- **User Authentication**: JWT and Google OAuth support.
- **Modern Tech Stack**: Python 3.9/Flask backend, React/Vite/TailwindCSS frontend, Flask-SocketIO for real-time updates.
- **Extensible Data Model**: See `app/models.py`, `app/schemas.py`, and `app/crud.py` for backend structure.


## Tech Stack

- **Backend**: Python 3.9, Flask, Flask-SocketIO, Eventlet, SQLAlchemy, Pydantic
- **Frontend**: React, Vite, TailwindCSS
- **Containerization**: Docker, Docker Compose


## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Node.js (for frontend development)
- Python 3.9+ (for backend development)
- A text editor (like VS Code)
- Git


## Getting Started

### 1. Clone the Repository

First, clone the repository to your local machine.

```bash
git clone https://github.com/cplatt-iso/hl7-yeet.git
cd hl7-yeet
```


### 2. Configure Environment Variables

The application uses a `.env` file for configuration (AI, database, JWT, etc). Example:

```env
# /home/icculus/axiom/infra/databases/yeeter/.env

# Required for the AI Analyzer feature
GOOGLE_API_KEY="your_google_gemini_api_key_here"
DATABASE_URL="sqlite:////data/yeeter_usage.db"  # or your preferred DB
JWT_SECRET_KEY="your_jwt_secret_here"
JWT_ACCESS_TOKEN_EXPIRES_HOURS=24
```

If you don't provide a `GOOGLE_API_KEY`, the application will still run, but the AI analysis feature will be disabled.


### 3. Build and Run with Docker Compose

The project is designed to be run with Docker Compose. The provided `docker-compose.yml` file in the parent directory handles the service setup.

From the `/home/icculus/axiom/infra/databases` directory, run:

```bash
docker-compose up --build -d
```

- `--build`: Build the image (needed after code changes)
- `-d`: Detached mode


### 4. Access the Application

Once the container is running, access HL7 Yeeter at:

- `http://localhost:5001` (default, no reverse proxy)
- Or configure your reverse proxy to forward to `hl7-yeeter:5001` (for custom domains)


## How to Use

### Sender & Parser

- Paste or edit HL7 messages, see them parsed and color-coded
- Edit fields inline, drag-and-drop values, rebuild messages in real time
- Send to any MLLP endpoint and view ACK/NACK
- Use the AI analyzer for message explanation and correction

### MLLP Listener

- Start a listener on any port, view incoming messages and ACKs in real time

### Simulation Engine

- Create and run simulation templates with multiple steps (generate HL7/DICOM, send, wait, etc.)
- Context extraction from HL7 messages (accession, modality, etc.)
- Real-time event logging and status updates

### Authentication

- Register/login with username/password or Google OAuth

### Command-line Simulator CLI

- Install project dependencies and ensure `requests` and `click` are available (see `requirements.txt`).
- Use the helper script `scripts/yeeter_cli.py` to automate simulator runs:

  ```bash
  # Authenticate and cache token locally (~/.yeeter/config.json by default)
  python scripts/yeeter_cli.py login --username <user> --password <pass>

  # Discover available templates
  python scripts/yeeter_cli.py templates list

  # Start a run from template ID 42 with 5 patients
  python scripts/yeeter_cli.py runs start --template-id 42 --patients 5

  # Machine-readable run metadata for automation
  python scripts/yeeter_cli.py runs start --template-id 42 --patients 5 --output json

  # Watch status changes until completion
  python scripts/yeeter_cli.py runs watch 101 --interval 2

  # Fetch aggregated metrics (table, json, or csv output)
  python scripts/yeeter_cli.py runs stats 101 --format table
  ```

- Override the API host with `YEETER_API_URL` or pass `--api-url`; for self-signed endpoints, add `--insecure`.
- CLI configuration path can be customized via `YEETER_CONFIG_PATH` (defaults to `~/.yeeter/config.json`).
- Run repeatable benchmarks with the helper script:

  ```bash
  # Launch template 42, watch progress, and archive stats under benchmarks/
  scripts/run_benchmark.sh 42 10 benchmarks
  ```


## Development

To stop the application:

```bash
docker-compose down
```

### Backend Structure

- `app/__init__.py`: Flask app factory, extension and blueprint registration
- `app/models.py`: SQLAlchemy models (User, Endpoint, GeneratorTemplate, SimulationTemplate, etc.)
- `app/schemas.py`: Pydantic schemas for API validation
- `app/crud.py`: Database access and business logic
- `app/util/simulation_runner.py`: Simulation engine (step orchestration, HL7/DICOM generation, MLLP sending, etc.)

### Frontend Structure

- `src/App.jsx`: Main React app, routing, authentication context
- `src/main.jsx`: Entry point, Google OAuth provider, AuthProvider
- `src/components/HL7Parser.jsx`: HL7 message parser/editor UI

### Critical Files

- Backend: `app/models.py`, `app/schemas.py`, `app/crud.py`, `app/util/simulation_runner.py`, `app/__init__.py`
- Frontend: `src/App.jsx`, `src/main.jsx`, `src/components/HL7Parser.jsx`

---
For more details, see the code and comments in the above files.
