# FIRSTChesapeakeBot
Docker image to run the [FIRST Chesapeake](https://www.firstchesapeake.org/) [Discord](https://discord.com/) Bot.

## INTRODUCTION
This is a Docker Image of a Discord Bot for the FIRST Chesapeake Discord Server.

This bot is able to pull information from the  [FIRST](https://www.firstinspires.org/) [FTC API](https://ftc-events.firstinspires.org/), [FIRST](https://www.firstinspires.org/) [FRC API](https://frc-events.firstinspires.org/), and [The Orange Alliance API](https://theorangealliance.org/home). The bot is also capable of retrieving live information from the [FIRST Tech Challenge
](https://github.com/FIRST-Tech-Challenge/scorekeeper) scorekeeping software (EMS).

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
!frcteam <Team Number> | Retrieves information about the supplied team from the FIRST FRC API
!ftcteam <Team Number> | Retrieves information about the supplied team from the FIRST FTC API
!ftcteamtoa <Team Number> | Retrieves information about the supplied team from the The Orange Alliance API
!ftc event start/stop <Event Code> | *ADMIN COMMAND* Start/Stops the live event feed for the provided FTC Event Code
!ftc server get apikey | *ADMIN COMMAND* Request an API key from the FTC Scorekeeper Software. This will output the key to Discord and log.
!clear <amount> | *ADMIN COMMAND* Removes the specified ammount of messages in a channel, excluding pinned messages.

## CHANGES
Date | Description
---- | ----
1NOV20 | Initial Release (v1.0)