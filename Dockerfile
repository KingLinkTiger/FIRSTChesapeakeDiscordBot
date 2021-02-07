# BUILD ENV
FROM python:3.9.1-slim-buster

LABEL version="1.0.9"
LABEL description="Docker image of the FIRST Chesapeake Discord Bot."
LABEL maintainer="kinglinktiger@gmail.com"

# Set WORKDIR
WORKDIR /code

# Copy the requirements file to the WORKDIR
COPY requirements.txt .

# Install the requirements
RUN pip install -r requirements.txt

# Copy the script source files to the WORKDIR
COPY src/ .

# Configure the volume for logging
VOLUME ["/var/log/firstchesapeakebot"]

# Command to run on container start
CMD [ "python", "-u", "./bot.py" ]
