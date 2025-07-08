# HL7 Yeeter 🚀

HL7 Yeeter is a powerful, web-based utility designed for developers and analysts working with HL7 messaging. It provides a rich, interactive interface for parsing, editing, sending, and receiving HL7 messages over MLLP (Minimal Lower Layer Protocol). It also integrates a Gemini-powered AI to help analyze and correct malformed messages.

This tool is fully containerized with Docker, making setup and deployment incredibly simple.

## Core Features

*   **Interactive Live Parser**: Paste or type an HL7 message and see it instantly broken down into a structured, color-coded, and editable format.
*   **Drag-and-Drop Fields**: Easily move values from one field to another.
*   **Real-time Message Rebuilding**: The raw HL7 message text is automatically updated as you edit the parsed fields.
*   **MLLP Client (Sender)**: "Yeet" your crafted HL7 message to any MLLP host and port and view the ACK/NACK response.
*   **Built-in MLLP Server (Listener)**: Spin up an MLLP listener on any port with a single click. View incoming messages in real-time via WebSockets.
*   **AI-Powered Analyzer**: Leverage Google's Gemini models to analyze an HL7 message, explain its purpose, identify errors, and even suggest a corrected version.
*   **Message Templates**: Quickly load common HL7 message templates to get started.
*   **Modern Tech Stack**: Built with a Python/Flask backend and a React/Vite frontend for a fast and responsive user experience.

## Tech Stack

*   **Backend**: Python 3.9, Flask, Flask-SocketIO, Eventlet
*   **Frontend**: React, Vite, TailwindCSS
*   **Containerization**: Docker, Docker Compose

## Prerequisites

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/)
*   A text editor (like VS Code)
*   Git

## Getting Started

### 1. Clone the Repository

First, clone the repository to your local machine.

```bash
git clone https://github.com/cplatt-iso/hl7-yeet.git
cd hl7-yeet
```

### 2. Configure Environment Variables

The application uses a `.env` file for configuration, primarily for the AI features.

Create a file named `.env` in the root of the project directory (`/home/icculus/axiom/infra/databases/yeeter/.env`):

```env
# /home/icculus/axiom/infra/databases/yeeter/.env

# Required for the AI Analyzer feature
GOOGLE_API_KEY="your_google_gemini_api_key_here"
```

If you don't provide a `GOOGLE_API_KEY`, the application will still run, but the AI analysis feature will be disabled.

### 3. Build and Run with Docker Compose

The project is designed to be run with Docker Compose. The provided `docker-compose.yml` file in the parent directory handles the service setup.

From the `/home/icculus/axiom/infra/databases` directory, run:

```bash
docker-compose up --build -d
```

*   `--build`: This flag tells Docker Compose to build the `hl7-yeeter` image using its `Dockerfile`. You only need to do this the first time or after making changes to the source code or `requirements.txt`.
*   `-d`: This runs the containers in detached mode (in the background).

### 4. Access the Application

Once the container is running, you can access the HL7 Yeeter application in your web browser.

*   **If you are running this locally without a reverse proxy:**
    The application will be available at `http://localhost:5001`.

*   **If you are using a reverse proxy (like Nginx Proxy Manager):**
    You will need to configure your proxy to forward traffic to `hl7-yeeter:5001`. The application is set up to be served from the root of a domain (e.g., `http://hl7-yeeter.local`).

## How to Use

1.  **Sender & Parser Tab**:
    *   Paste an HL7 message into the text area or select a template.
    *   The message will be parsed into an interactive table.
    *   Edit fields by double-clicking their values.
    *   Enter a destination `Host` and `Port` and click **"YEET IT"** to send the message.
    *   Click the "magic wand" icon to analyze the message with AI.

2.  **MLLP Listener Tab**:
    *   Enter a `Port` you want the listener to run on.
    *   Click **"Start Listener"**. The status will update to "Listening".
    *   Send an HL7 message to your machine's IP address on that port from another application.
    *   The incoming message and the ACK sent back will appear in the "Received Messages" log.
    *   Click **"Stop Listener"** to shut it down.

## Development

To stop the application, run the following command from the directory containing your `docker-compose.yml` file:

```bash
docker-compose down
```
