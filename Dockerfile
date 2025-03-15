# Start with a minimal Python base image
FROM python:3.12-slim-bullseye

# Set the working directory inside the container
WORKDIR /workspace

# Install ffmpeg and clean up in a single step to minimize layers
RUN apt-get update && apt-get install -y --no-install-recommends \
	ffmpeg && \
	apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy application files to the container
COPY . . 

# Upgrade pip and install required Python packages in a single step
RUN pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt

# Expose the required port
EXPOSE 8000

# Command to run the application
CMD ["python3", "app.py", "--log-level=WARN"]

