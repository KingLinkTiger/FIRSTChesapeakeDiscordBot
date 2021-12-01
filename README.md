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
!frcteam/frc TeamNumber | Retrieves information about the supplied team from the FIRST FRC API
!ftcteam/ftc TeamNumber | Retrieves information about the supplied team from the FIRST FTC API
!ftcteamtoa TeamNumber | Retrieves information about the supplied team from the The Orange Alliance API
!ftc event start EventCode eventName | *ADMIN COMMAND* Starts the live event feed for the provided FTC Event Code
!ftc event stop EventCode | *ADMIN COMMAND* Stops the live event feed for the provided FTC Event Code
!ftc server get apikey | *ADMIN COMMAND* Request an API key from the FTC Scorekeeper Software. This will output the key to Discord and log.
!clear amount | *ADMIN COMMAND* Removes the specified ammount of messages in a channel, excluding pinned messages.

## CHANGES
Date | Description
---- | ----
1NOV20 | Initial Release (v1.0)
2NOV20 | v1.0.1 - Added: Auto Assign new users the "Needs Registration" Role, Clear/Sweep Command, Modified bot to also listen for all commands on the Admin channel as well
13NOV20 | v1.0.6 - Changed Admin Role to ENV variable
31JAN21 | v1.0.7 - Updated base image version, Updated requirements to latest, Fixed issue with websocket, ability to set multiple admin and production channels, added saving match results to mySQL server on comit.
7FEB21 | v1.0.7 - Added BOTMATCHRESULTCHANNELS ENV Variable, configured match results to only send to that channel, and configured bot to allow team commands from all but that channel.
7FEB21 | v1.0.8 - Fixed Match Results to post only to Match Results channel, also updated example.env file.
7FEB21 | v1.1.0 - Added voice announcments for match status (Start, Post, Abort).
14FEB21 | v1.1.1 - Added argument to event start for the event name. This gets passed to the voice announcments.
16FEB21 | v1.1.2 - Added ability to assign role to user when they react to a specific message.
16FEB21 | v1.1.3 - Modifed react role. If user already had role remove it. If user is member of Auto Assigned role remove their reaction and do nothing.
22FEB21 | v1.1.4 - Added aliases for frcteam and ftcteam commands.
24OCT21 | v2.0.0 - Updated bot to support 2022 FTC season.
30NOV21 | v2.1.0 - Updated bot to support Elimination Semi-Final and Finals matches. Fixed issue with TTS. Began improving get API key command.