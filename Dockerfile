# BUILD ENV
FROM python:3.9.2-slim-buster

LABEL version="1.1.4"
LABEL description="Docker image of the FIRST Chesapeake Discord Bot."
LABEL maintainer="kinglinktiger@gmail.com"

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
VOLUME ["/var/log/firstchesapeakebot"]

# Command to run on container start
CMD [ "python", "-u", "./bot.py" ]
