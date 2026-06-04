# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# Added 'tzdata' to support ZoneInfo/Timezones in Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Create a directory for the database to ensure persistence via volumes
RUN mkdir -p /app/data

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variables
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8080
ENV DB_PATH=/app/data/srbase.db
ENV PYTHONUNBUFFERED=1

# Run main.py when the container launches
CMD ["python", "main.py"]
