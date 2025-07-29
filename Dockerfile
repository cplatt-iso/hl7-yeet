# --- START OF FILE Dockerfile ---

# Use a specific, stable, and MODERN version of Python.
# THE ONLY CHANGE IS THIS ONE LINE.
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1

# Update package lists and install dependencies needed for psycopg2-binary
# Then clean up the cache to keep the image slim.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# This includes the `app` package and our `run.py`
COPY . .

# Expose the port the app runs on
EXPOSE 5001

# THE GRAND FINALE: The command to run the application
# We use Gunicorn, a production-grade WSGI server.
# --worker-class eventlet: This is CRITICAL for Flask-SocketIO to work correctly.
# -w 1: Use a single worker process with eventlet.
# --bind 0.0.0.0:5001: Bind to all network interfaces on port 5001.
# run:app: Tells Gunicorn to look in the `run.py` file for a variable named `app`.
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--timeout", "60", "--bind", "0.0.0.0:5001", "run:app"]
# --- END OF FILE Dockerfile ---