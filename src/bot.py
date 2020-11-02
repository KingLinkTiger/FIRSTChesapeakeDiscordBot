#TODO: On container shutdown gracefully stop everything (Logging and websockets)

import os, os.path
from datetime import datetime, timedelta
import requests
import requests_cache
import json
import asyncio
import concurrent.futures
import websockets
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

from FTCEvent import FTCEvent

#Create cache file so we don't make unnecessary calls to the APIs 
requests_cache.install_cache('FIRSTChesapeakeBot_cache', backend='sqlite', expire_after=(timedelta(days=3)))

#Start logging
logger = logging.getLogger('FIRSTChesapeakeBot')
logger.setLevel(logging.DEBUG)

if not os.path.exists("/var/log/firstchesapeakebot"):
    os.makedirs("/var/log/firstchesapeakebot")

fh = logging.FileHandler("/var/log/firstchesapeakebot/FIRSTChesapeakeBot.log")
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
fh.setFormatter(formatter)

logger.addHandler(fh)

#Load Environment Variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TOA_KEY = os.getenv('TOA_KEY')
FTCEVENTS_KEY = os.getenv('FTCEVENTS_KEY')
FRCEVENTS_KEY = os.getenv('FRCEVENTS_KEY')
FTCEVENTSERVER = os.getenv('FTCEVENTSERVER')


BOTADMINCHANNEL = os.getenv('BOTADMINCHANNEL')
BOTADMINCHANNEL_ID = None
BOTPRODUCTIONCHANNEL = os.getenv('BOTPRODUCTIONCHANNEL')
BOTPRODUCTIONCHANNEL_ID = None

FTCEVENTSERVER_APIKey = os.getenv('FTCEVENTSERVER_APIKey')


bot = commands.Bot(command_prefix='!', case_insensitive=True)

events = {}


# ===== START COMMANDS SECTION =====

@bot.command(name='ftcteamtoa')
async def getFTCTeamDataTOA(ctx, team_number: str):
    if ctx.message.channel.name == BOTPRODUCTIONCHANNEL or ctx.message.channel.name == BOTADMINCHANNEL:
        if team_number.isnumeric() and int(team_number) >= 0 and len(team_number) <= 5:
            logger.info(ctx.message.author.display_name + " requested team number " + team_number + " from TOA.")
            
            try:
                apiheaders = {'Content-Type':'application/json', 'X-TOA-Key':TOA_KEY, 'X-Application-Origin':'DiscordTOABot' }
                response = requests.get('https://theorangealliance.org/api/team/'+team_number, headers=apiheaders, timeout=3)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                #Server is offline and needs to be handled
                logger.error("Failed to contact The Orange Alliance API!")
            else:
                #Get the status code for furthur processing if needed
                # e.g. 404 = Team number not found
                if response.status_code == 404:
                    logger.error("404 error received when trying to poll TOA for Team Number: " + team_number)
                    pass
                    #await ctx.send("ERROR: Provided team number " + team_number + " could not be found")
                else:
                    j = json.loads(response.text)[0]
                    
                    #Info to get
                    #Output Team number
                    #Team Name j['team_name_short']
                    #Location j['city']+", "+j['state_prov']+" "+j['country']
                    #Rookie Year j['rookie_year']

                    await ctx.send("""```""" + "FIRST Tech Challenge (FTC) Team Information" + "\n" + "--------------------------------------------------" + "\n" + "Team Number: " + team_number + "\n" + "Team Name: " + j['team_name_short'] + "\n" + "Team Long Name: " + j['team_name_long'] + "\n" + "Location: " + j['city'] + ", " + j['state_prov'] + " " + j['country'] + "\n" + "Rookie Year: " + str(j['rookie_year']) + """```""")
    else:
        logger.warning(ctx.message.author.display_name + " tried to invoke bot from " + ctx.message.channel.name + ".")
  
@bot.command(name='ftcteam')
async def getFTCTeamData(ctx, team_number: str):
    if ctx.message.channel.name == BOTPRODUCTIONCHANNEL or ctx.message.channel.name == BOTADMINCHANNEL:
        teamNumberInt = int(team_number)
        if team_number.isnumeric() and teamNumberInt >= 0 and len(team_number) <= 5:
            logger.info(ctx.message.author.display_name + " requested team number " + team_number + " from FIRST FTC DB.")
            teamFound = False
 
            for eventCode in events:
                event = events[eventCode]
                if teamNumberInt in event.teams:
                    teamFound = True
                    await ctx.send("""```""" + "FIRST Tech Challenge (FTC) Team Information" + "\n" + "--------------------------------------------------" + "\n" + "Team Number: " + team_number + "\n" + "Team Name: " + event.teams[teamNumberInt].name + "\n" + "Team Long Name: " + event.teams[teamNumberInt].school + "\n" + "Location: " + event.teams[teamNumberInt].city + ", " + event.teams[teamNumberInt].state + " " + event.teams[teamNumberInt].country + "\n" + "Rookie Year: " + str(event.teams[teamNumberInt].rookie) + """```""")
                    break            
            if teamFound == False:
                try:
                    apiheaders = {'Accept':'application/json', 'Authorization':'Basic ' + FTCEVENTS_KEY}
                    response = requests.get('https://ftc-api.firstinspires.org/v2.0/2020/teams?teamNumber='+team_number, headers=apiheaders, timeout=3)
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    #Server is offline and needs to be handled
                    logger.error("Failed to contact FIRST FTC API!")
                else:
                    #Get the status code for furthur processing if needed
                    # e.g. 404 = Team number not found
                    if response.status_code == 404:
                        logger.error("404 error received when trying to poll FIRST FTC DB for Team Number: " + team_number)
                        pass
                        #await ctx.send("ERROR: Provided team number " + team_number + " could not be found")
                    elif response.status_code == 400:
                        logger.error("400 error received when trying to poll FIRST FTC DB for Team Number: " + team_number)
                        pass
                        #await ctx.send("ERROR: Provided team number " + team_number + " could not be found")
                    else:
                        #print(response.text)
                        j = json.loads(response.text)["teams"][0]

                        #Info to get
                        #Team Name j['team_name_short']
                        #Location j['city']+", "+j['state_prov']+" "+j['country']
                        #Rookie Year j['rookie_year']
                        await ctx.send("""```""" + "FIRST Tech Challenge (FTC) Team Information" + "\n" + "--------------------------------------------------" + "\n" + "Team Number: " + team_number + "\n" + "Team Name: " + j['nameShort'] + "\n" + "Team Long Name: " + j['nameFull'] + "\n" + "Location: " + j['city'] + ", " + j['stateProv'] + " " + j['country'] + "\n" + "Rookie Year: " + str(j['rookieYear']) + """```""")
    else:
        logger.warning(ctx.message.author.display_name + " tried to invoke bot from " + ctx.message.channel.name + ".")

@bot.command(name='frcteam')
async def getFRCTeamData(ctx, team_number: str):
    if ctx.message.channel.name == BOTPRODUCTIONCHANNEL or ctx.message.channel.name == BOTADMINCHANNEL:
        if team_number.isnumeric() and int(team_number) >= 0 and len(team_number) <= 4:
            logger.info(ctx.message.author.display_name + " requested team number " + team_number + " from FIRST FRC DB.")
            
            try:
                apiheaders = {'Accept':'application/json', 'Authorization':'Basic '+FRCEVENTS_KEY}
                response = requests.get('https://frc-api.firstinspires.org/v2.0/2020/teams?teamNumber='+team_number, headers=apiheaders, timeout=3)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                #Server is offline and needs to be handled
                logger.error("Failed to contact FIRST FRC API!")
            else:
                #Server is online and we received a response
                #Get the status code for furthur processing if needed
                # e.g. 404 = Team number not found
                if response.status_code == 404:
                    logger.error("404 error received when trying to poll FIRST FTC DB for Team Number: " + team_number)
                    pass
                    #await ctx.send("ERROR: Provided team number " + team_number + " could not be found")
                elif response.status_code == 400:
                    logger.error("400 error received when trying to poll FIRST FTC DB for Team Number: " + team_number)
                    pass
                    #await ctx.send("ERROR: Provided team number " + team_number + " could not be found")
                else:
                    #print(response.text)
                    j = json.loads(response.text)["teams"][0]

                    #Info to get
                    #Team Name j['team_name_short']
                    #Location j['city']+", "+j['state_prov']+" "+j['country']
                    #Rookie Year j['rookie_year']
                    await ctx.send("""```""" + "FIRST Robotics Competition (FRC) Team Information" + "\n" + "--------------------------------------------------" + "\n" + "Team Number: " + team_number + "\n" + "Team Name: " + j['nameShort'] + "\n" + "Team Long Name: " + j['nameFull'] + "\n" + "Location: " + j['city'] + ", " + j['stateProv'] + " " + j['country'] + "\n" + "Rookie Year: " + str(j['rookieYear']) + """```""")
    else:
        logger.warning(ctx.message.author.display_name + " tried to invoke bot from " + ctx.message.channel.name + ".")
                
@bot.group()
async def ftc(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send('Invalid command passed...')

@ftc.command()
async def event(ctx, verb: str, noun: str):
    if ctx.message.channel.name == BOTADMINCHANNEL and "Server Administrator".lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info(ctx.message.author.display_name + " ran command " + ctx.message.content)
        
        formattedVerb = verb.lower()
        
        if formattedVerb == "add" or formattedVerb == "start":
            #If the event code is NOT already in the events DICT
            if not noun in events:
                #Check that we received a valid eventcode
                #Validate Event Code
                
                try:
                    apiheaders = {'Content-Type':'application/json'}
                    response = requests.get(FTCEVENTSERVER + "/api/v1/events/" + noun + "/", headers=apiheaders, timeout=3)
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    #Server is offline and needs to be handled
                    logger.error("Failed to contact FTC Event Server!")
                    await ctx.send("ERROR: Failed to contact FTC Event Server!")
                else:
                    #We received a reply from the server
                    if response.status_code == 200:
                        #Get basic event information from server API
                        responseData = json.loads(response.text)
                        
                        #Create FTCEvent instance
                        e = FTCEvent(responseData, bot, BOTPRODUCTIONCHANNEL_ID, BOTADMINCHANNEL_ID)
                        
                        #Store instance in dict
                        events[noun] = e

                        #Add reaction to message to let user know it was created successfully
                        await ctx.message.add_reaction('✅')

                    else:
                        logger.warning(ctx.message.author.display_name + " provided an invalid event code to the FTC Event Command!")
                        await ctx.send("ERROR: Invalid event code provided.")
            else:
                logger.info("Already monitoring event code " + noun + ".")
                await ctx.send("ERROR: System is already monitoring event " + noun)

        elif formattedVerb == "remove" or formattedVerb == "delete" or formattedVerb == "stop":
            if noun in events:
                await events[noun].stopWebSocket()
                del events[noun]
                await ctx.message.add_reaction('🛑')
            else:
                logger.error("Unable to remove event! Event code was not being monitored by system: " + noun + ".")
                await ctx.send("ERROR: System is not monitoring event " + noun)
    else:
        logger.warning(ctx.message.author.display_name + " attempted to invoke the FTC Event Command on server " + ctx.guild.name + "! Command provided: " + ctx.message.content)

@ftc.command()
async def server(ctx, verb: str, noun: str):
    if ctx.message.channel.name == BOTADMINCHANNEL and "Server Administrator".lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info(ctx.message.author.display_name + " ran command " + ctx.message.content)
        
        formattedVerb = verb.lower()
        formattedNoun = noun.lower()

        if formattedVerb == "get" and formattedNoun == "apikey":
            #If We don't already have an API key set in an environment variable
            
            logger.info("Checking for API Key")
            
            if not FTCEVENTSERVER_APIKey:
                logger.info("Requesting FTC Event Server API Key")

                try:
                    apiheaders = {'Content-Type':'application/json'}
                    response = requests.post(FTCEVENTSERVER + "/api/v1/keyrequest/", data = {"name":"FIRSTChesapeakeBot"}, timeout=3)

                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    #Server is offline and needs to be handled
                    logger.error("Failed to contact FTC Event Server!")
                    await ctx.send("ERROR: Failed to contact FTC Event Server!")
                else:
                    #We received a reply from the server
                    if response.status_code == 200:
                        logger.info("Received API Key: " + responseData["key"])
                        await ctx.send("Received API Key: " + responseData["key"])
                    elif response.status_code == 400:
                        logger.error("Must include name as a parameter when requesting API key.")
                    else:
                        logger.warning("Invalid response from server.")
                        await ctx.send("ERROR: Invalid response from server.")
            else:
                logger.warning("There is already an API key set for this application. Key: " + FTCEVENTSERVER_APIKey)
                await ctx.send("ERROR: There is already an API key set for this application. Check logs for more information.")
    else:
        logger.warning(ctx.message.author.display_name + " attempted to invoke the FTC SERVER Command on server " + ctx.guild.name + "! Command provided: " + ctx.message.content)

#The following code is from https://stackoverflow.com/questions/60643592/how-to-delete-all-messages-from-a-channel-with-discord-bot
@bot.command(pass_context = True , aliases=['purge', 'clean', 'delete', 'sweep'])
@commands.has_permissions(manage_messages=True) 
#only those with the permission to manage messages can use this command
async def clear(ctx, amount: int):
    logger.warning(ctx.message.author.display_name + " has requested the removal of " + str(amount + 1) + " messages from channel " + ctx.message.channel.name)
    #The check_func is from https://stackoverflow.com/questions/62224912/is-there-a-way-to-do-a-check-for-pinned-messages-and-only-purge-a-certain-membe
    #check_func = lambda msg: not msg.pinned
    
    #New check from https://stackoverflow.com/questions/53643906/discord-py-delete-all-messages-except-pin-messages
    await ctx.channel.purge(limit=amount + 1, check=lambda msg: not msg.pinned)


# ===== END COMMANDS SECTION =====

# ===== START BOT EVENT SECTION ===== 
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        logger.warning(ctx.message.author.display_name + " attempted to invoke an invalid command on server " + ctx.guild.name + "! Command provided: " + ctx.message.content)
        #await ctx.send('ERROR: The entered command does not exist!')
        
@bot.event
async def on_ready():
    # Check if we have a valid API key
    checkFTCEVENTSERVER_APIKey()
    
    # Get the Channel IDs for the channels we need
    findChannels()
    
@bot.event
async def on_member_join(member):
    #When a new member joins the server assign them the Needs Registration Role
    await member.add_roles("Needs Registration", "Assigning new member the Needs Registration Role")

# ===== END BOT EVENT SECTION ===== 


# ===== START FUNCTION SECTION ===== 
def checkFTCEVENTSERVER_APIKey():
    if FTCEVENTSERVER_APIKey:
        try:
            apiheaders = {'Content-Type':'application/json', 'Authorization':FTCEVENTSERVER_APIKey}
            response = requests.get(FTCEVENTSERVER + "/api/v1/keycheck/", headers=apiheaders)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            #Server is offline and needs to be handled
            logger.error("Failed to contact FTC Event Server!")
            #await ctx.send("ERROR: Failed to contact FTC Event Server!")
        else:
            #We received a reply from the server
            if response.status_code == 200:
                responseData = json.loads(response.text)
                if responseData["active"]:
                    logger.info("API Key is active")
                else:
                    #Not a active API key
                    logger.info("API Key is NOT active. Please activate it in the FTC Event Server.")
            elif response.status_code == 404:
                logger.error("Supplied API Key does not exist. Please request one, update .env file, and restart the bot.")
            else:
                logger.warning("Invalid response from server.")
    else:
        logger.error("FTC Event Server API Key is not set! Please request one, update .env file, and restart the bot.")

def findChannels():
    global BOTPRODUCTIONCHANNEL_ID
    global BOTADMINCHANNEL_ID
    
    channels = bot.get_all_channels()
    for channel in channels:       
        if channel.name.lower() == BOTPRODUCTIONCHANNEL.lower() and str(channel.type) == "text":
            BOTPRODUCTIONCHANNEL_ID = channel.id
            logger.info("Bot Production Channel found: " + str(channel.id))
        elif channel.name.lower() == BOTADMINCHANNEL.lower() and str(channel.type) == "text":
            BOTADMINCHANNEL_ID = channel.id
            logger.info("Bot Admin Channel found: " + str(channel.id))
    
    if BOTPRODUCTIONCHANNEL_ID == None:
        logger.error("Unable to locate Bot Production Channel")
        
    if BOTADMINCHANNEL_ID == None:
        logger.error("Unable to locate Bot Admin Channel")

async def stopWebSockets():
    #Stop the websocket for each event
    logger.info("Stopping all websockets")
    for eventCode in events:
        event = events[eventCode]
        await event.stopWebSocket()

async def stopDiscordBot():
    #Stop the Discord Bot
    logger.info("Logging out Discord bot")
    await bot.logout()   

async def stopBot():
    f_task1 = asyncio.create_task(stopWebSockets())
    await f_task1

    f_task2 = asyncio.create_task(stopDiscordBot())
    await f_task2

    #Tell logger to orderly shutdown all logs
    logger.warning("Shutting down logging")
    logging.shutdown()

    # FIN
# ===== END FUNCTION SECTION =====     


# Write to the log to let us know the bot is, about to be, online and ready to go
logger.info("Bot started and connecting to DISCORD")

# Script will hold on this call untill process/container is stopped
bot.run(DISCORD_TOKEN)

# All calls after the above should only run when process/container is being stopped
asyncio.run(stopBot())
