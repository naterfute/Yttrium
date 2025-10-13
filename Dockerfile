# Start with a minimal Python base image
FROM python:3.12

# Set the working directory inside the container
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg && \
  apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . . 

RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python3", "-m", "src", "--fast", "--log-level", "INFO"]

