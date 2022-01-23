# FIRSTChesapeakeBot
Docker image to run the [FIRST Chesapeake](https://www.firstchesapeake.org/) [Discord](https://discord.com/) Bot.

## INTRODUCTION
This is a Docker Image of a Discord Bot for the FIRST Chesapeake Discord Server.

This bot is able to pull information from the  [FIRST](https://www.firstinspires.org/) [FTC API](https://ftc-events.firstinspires.org/), [FIRST](https://www.firstinspires.org/) [FRC API](https://frc-events.firstinspires.org/), and [The Orange Alliance API](https://theorangealliance.org/home). The bot is also capable of retrieving live information from the [FIRST Tech Challenge
](https://github.com/FIRST-Tech-Challenge/scorekeeper) scorekeeping software (EMS).

This Docker image is being pushed to [Docker Hub](https://hub.docker.com/repository/docker/kinglinktiger/firstchesapeakediscordbot)

## INSTALLATION
1. Update the .env file with your API Keys, what Discord Channel you want the bot to receive commands from, and what Discord Channel you want to send the live FTC event information to.
2. Run the bot.
3. From the Admin Channel run the ```!ftc server get apikey``` command to get an API key from the FTC Scorekeeper Software.
4. Update the .env file with the API key.
5. Run the bot.

## VOLUMES
Description | Container Path
---- | ----
Logs | /var/log/firstchesapeakebot

## EXPOSE PORTS
None

## COMMANDS
Command | Description
---- | ----
!ping | Ping/Pong command in order to validate the bot is online.
!vping | *ADMIN COMMAND* Voice Ping command in order to validate bot voice is functioning.
!frcteam/frc TeamNumber | Retrieves information about the supplied team from the FIRST FRC API
!ftcteam/ftc TeamNumber | Retrieves information about the supplied team from the FIRST FTC API
!ftcteamtoa TeamNumber | Retrieves information about the supplied team from the The Orange Alliance API
!ftc event start EventCode eventName | *ADMIN COMMAND* Starts the live event feed for the provided FTC Event Code
!ftc event stop EventCode | *ADMIN COMMAND* Stops the live event feed for the provided FTC Event Code
!ftc server get apikey | *ADMIN COMMAND* Request an API key from the FTC Scorekeeper Software. This will output the key to Discord and log.
!clear amount | *ADMIN COMMAND* Removes the specified ammount of messages in a channel, excluding pinned messages.
!dhighscore/dhs/dhigh/dh/chshigh | Returns the CHS High Score for this season.
!autohigh/ah/ahigh | Returns the Auto High Score for the active event(s)
!highscore/hs/high/h | Returns the High Score for the active event(s)

## CHANGES
Please review [CHANGELOG.md](CHANGELOG.md)