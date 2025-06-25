# Start with a sane, slim Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching.
# This means we only re-install dependencies if requirements.txt changes.
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 5001

# The command to run the Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
