# my-ocs-agent-docker
# Dockerfile for Teledyne Pressure Gauge

# Use the ocs image as a base
FROM simonsobs/ocs:latest

# Install required dependencies
RUN apt-get update && apt-get install -y rsync \
    wget \
    python3-pip

# Copy in and install requirements
COPY requirements.txt /app/my-ocs-agent/requirements.txt
WORKDIR /app/my-ocs-agent/
RUN pip3 install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/my-ocs-agent/

# Run agent on container startup
ENTRYPOINT ["dumb-init", "ocs-agent-cli"]

#Set default commandline arguments
CMD ["--agent", "Teledyne_Agent.py", "--entrypoint", "main"]
