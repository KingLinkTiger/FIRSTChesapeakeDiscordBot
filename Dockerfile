# BUILD ENV
FROM python:3.9.13-slim-buster

LABEL version="2.3.23"
LABEL description="Docker Image of the FIRST Chesapeake Discord Bot."
LABEL maintainer="KingLinkTiger@gmail.com"

# Install ffmpeg as part of image for TTS usage
RUN apt-get update
RUN apt-get -y install ffmpeg libffi-dev libnacl-dev python3-dev

# Set WORKDIR
WORKDIR /code

# Copy the requirements file to the WORKDIR
COPY requirements.txt .

# Install the requirements
RUN python3 -m pip install -U "discord.py[voice]"
RUN pip install -r requirements.txt

# Copy the script source files to the WORKDIR
COPY src/ .

# Configure the volume for logging
VOLUME ["/var/log/firstchesapeakediscordbot"]

# Command to run on container start
CMD [ "python", "./bot.py" ]
