import os, os.path
import datetime 
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
from io import StringIO
import csv

from FTCEvent import FTCEvent
from DiscordChannel import DiscordChannel

#For TTS
from gtts import gTTS
from io import BytesIO

#For fixing voice
from FFmpegPCMAudioGTTS import FFmpegPCMAudioGTTS

#Required for vPing
import random

#required for logging to stdout
import sys

#required for mySQL Queries
import mysql.connector
from mysql.connector import Error


#25AUG22 - Get logging level from variable
LOGLEVEL =  os.environ.get('LOGLEVEL', 'INFO').upper()

#Create cache file so we don't make unnecessary calls to the APIs 
requests_cache.install_cache('FIRSTChesapeakeBot_cache', backend='sqlite', expire_after=(datetime.timedelta(days=3)))

#Start logging
logger = logging.getLogger('FIRSTChesapeakeBot')
logger.setLevel(level=LOGLEVEL) #25AUG22 - Updated to use LOGLEVEL variable

#23JAN22 - Output to stdout
sh = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
sh.setFormatter(formatter)
logger.addHandler(sh)

#25AUG22 - Add LOGFOLDER Variable
LOGFOLDER = os.path.join(os.environ.get('LOGFOLDER', '/var/log'), '') # https://stackoverflow.com/questions/2736144/python-add-trailing-slash-to-directory-string-os-independently

#25AUG22 - Added LOGNAME Variable
LOGNAME = os.environ.get('LOGNAME', 'FIRSTChesapeakeDiscordBot.log')

if not os.path.exists(LOGFOLDER):
    os.makedirs(LOGFOLDER)

fh = logging.FileHandler(LOGFOLDER+LOGNAME)
fh.setLevel(level=LOGLEVEL) #25AUG22 - Updated to use LOGLEVEL variable

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

BOTADMINCHANNELS = os.getenv('BOTADMINCHANNELS').replace("'", "").replace('"', '')

BOTPRODUCTIONCHANNELS = os.getenv('BOTPRODUCTIONCHANNELS').replace("'", "").replace('"', '')

BOTMATCHRESULTCHANNELS = os.getenv('BOTMATCHRESULTCHANNELS').replace("'", "").replace('"', '')

FTCEVENTSERVER_APIKey = os.getenv('FTCEVENTSERVER_APIKey')

ROLE_NEWUSER = os.getenv('ROLE_NEWUSER').replace("'", "").replace('"', '')

ROLE_ADMINISTRATOR = os.getenv('ROLE_ADMINISTRATOR').replace("'", "").replace('"', '')

#TTS ENV Variables
BOTTTSENABLED = os.getenv('BOTTTSENABLED')
BOTTTSCHANNEL = os.getenv('BOTTTSCHANNEL').replace("'", "").replace('"', '')

#Reaction Monitor ENV Variables
ID_Message_ReactionMonitor = int(os.getenv('ID_Message_ReactionMonitor'))
ROLE_ReactionMonitor = os.getenv('ROLE_ReactionMonitor').replace("'", "").replace('"', '')
ID_Channel_ReactionMonitor = int(os.getenv('ID_Channel_ReactionMonitor'))

#Required for mySQL Queries
mySQL_USER = os.getenv('mySQL_USER')
mySQL_PASSWORD = os.getenv('mySQL_PASSWORD')
mySQL_HOST = os.getenv('mySQL_HOST')
mySQL_DATABASE = os.getenv('mySQL_DATABASE')
mySQL_TABLE = os.getenv('mySQL_TABLE')
mySQL_RANKINGTABLE = os.getenv('mySQL_RANKINGTABLE')

# Commentator ROLE Management
#from discord.ext import tasks #TODO Autoremove the role
ROLE_ACTIVECOMMENTATOR = int(os.getenv('ROLE_ACTIVECOMMENTATOR'))
ROLE_COMMENTATOR = int(os.getenv('ROLE_COMMENTATOR'))
ID_Channel_Voice_CommentatorLive = int(os.getenv('ID_Channel_Voice_CommentatorLive'))

# Get master variables to disable portions of the bot if desired
bool_FTCEVENTSSERVER = os.getenv('bool_FTCEVENTSSERVER').lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']


intents = discord.Intents(
    message_content=True, #25AUG22 - Required with Discord.py v2
    messages=True,
    guilds=True,
    reactions=True,
    members = True,
    voice_states=True, # Add this!
)
intents.members = True
bot = commands.Bot(command_prefix='!', case_insensitive=True, intents=intents)


events = []


# ===== START COMMANDS SECTION =====

#30JAN22 - Added End of Day Command
@bot.command(name="endofday", aliases=['eod'])
async def endOfDay(ctx):
    #TODO
    # Clear all messages in bot-spam
    # Clear all messages in Event-results
    # Clear all messages in Registration
    # Clear all messages in Scorekeeping-coms
    # Clear all messages in backstage

    #Remove ActiveCommentator role from all users
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        for guild in bot.guilds:
            logger.debug("[on_voice_state_update] Guild Name: " + guild.name)
            obj_ROLE_ACTIVECOMMENTATOR = guild.get_role(ROLE_ACTIVECOMMENTATOR)

        for member in bot.get_all_members():
            if ROLE_ACTIVECOMMENTATOR in [y.id for y in member.roles]:
                await member.remove_roles(obj_ROLE_ACTIVECOMMENTATOR)

#23JAN22
@bot.command(name="dhighscore", aliases=['dhs', 'dhigh', 'dh', 'chshigh'])
async def chshigh(ctx):
    if bool_FTCEVENTSSERVER:
        logger.info("[chshigh] " + ctx.message.author.display_name + " tried to run command " + ctx.message.content)

        if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 0 or x.channelType == 1]:
            logger.info("[chshigh] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
            try:
                mySQLConnection = mysql.connector.connect(user=mySQL_USER, password=mySQL_PASSWORD, host=mySQL_HOST, database=mySQL_DATABASE)
                mySQLCursor = mySQLConnection.cursor(dictionary=True)
                logger.info("[chshigh] " + "Connected to SQL Database")
            except mysql.connector.Error as err:
                logger.error("[chshigh] " + "ERROR when trying to connect to SQL Database.")
                logger.error("[chshigh] " + err.msg)

            #get the high score for each event
            SQLStatement = "SELECT eventCode,matchBrief_matchName,startTime,redScore,blueScore,red_auto,blue_auto,matchBrief_red_team1,matchBrief_red_team2,matchBrief_blue_team1,matchBrief_blue_team2 FROM `{table_name}` WHERE (`eventCode` <> 'bottest1' AND `eventCode` <> 'bottest2') AND (redScore = (SELECT GREATEST(MAX(redScore), MAX(blueScore)) AS highScore  FROM `{table_name}` WHERE (`eventCode` <> 'bottest1' AND `eventCode` <> 'bottest2')) OR blueScore = (SELECT GREATEST(MAX(redScore), MAX(blueScore)) AS highScore  FROM `{table_name}` WHERE (`eventCode` <> 'bottest1' AND `eventCode` <> 'bottest2')));".format(table_name=mySQL_TABLE)

            try:
                mySQLCursor.execute(SQLStatement)
                result = mySQLCursor.fetchall()
            except mysql.connector.Error as err:
                logger.error("[chshigh] " + "ERROR when trying to SELECT from SQL Database.")
                logger.error("[chshigh] " + "Something went wrong: {}".format(err))
                logger.error("[chshigh] %s" % (SQLStatement,))
            except Exception as err:
                logger.error("[chshigh] " + "ERROR when trying to SELECT from SQL Database.")
                logger.error("[chshigh] " + "Something went wrong: {}".format(err))
                logger.error("[chshigh] %s" % (SQLStatement,))

            for row in result:
                eventName = ""

                #Do API call in order to get name of the event
                try:
                    apiheaders = {'Content-Type':'application/json'}
                    response = requests.get(FTCEVENTSERVER + "/api/v1/events/" + row["eventCode"] + "/", headers=apiheaders, timeout=3)
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    #Server is offline and needs to be handled
                    logger.error("[chshigh] Failed to contact FTC Event Server!")
                else:
                    #We received a reply from the server
                    if response.status_code == 200:
                        logger.info("[chshigh] Got data from the FTC Event Server!")
                        #Get basic event information from server API
                        responseData = json.loads(response.text)
                        eventName = str(responseData["name"])
                        logger.debug("[chshigh] Got: " + eventName)
                    else:
                        logger.error("[chshigh] Failed to get event name from FTC Event Server!")

                embedVar = discord.Embed(title="CHS HIGH SCORE", description="Current High Score for CHS", color=discord.Colour.blue())

                if eventName == "":
                    embedVar.add_field(name="Event Name", value=row["eventCode"], inline=False)

                else:
                    embedVar.add_field(name="Event Name", value=eventName, inline=False)

                embedVar.add_field(name="Event Date", value=(row["startTime"].strftime("%B %d, %Y")), inline=False)

                embedVar.add_field(name="Match Number", value=row["matchBrief_matchName"], inline=False)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                #RED LEFT BLUE RIGHT
                if row["redScore"] > row["blueScore"]:
                    embedVar.add_field(name="Red Score", value=(str(row["redScore"]) + " 🏆"), inline=True)
                    embedVar.add_field(name="Blue Score", value=str(row["blueScore"]), inline=True)
                elif row["redScore"] < row["blueScore"]:
                    embedVar.add_field(name="Red Score", value=str(row["redScore"]), inline=True)
                    embedVar.add_field(name="Blue Score", value=(str(row["blueScore"]) + " 🏆"), inline=True)
                elif row["redScore"] == row["blueScore"]:
                    embedVar.add_field(name="Red Score", value=(str(row["redScore"]) + " 🏆"), inline=True)
                    embedVar.add_field(name="Blue Score", value=(str(row["blueScore"]) + " 🏆"), inline=True)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                embedVar.add_field(name="Red Alliance", value=(str(row["matchBrief_red_team1"]) + "\n" + str(row["matchBrief_red_team2"])), inline=False)
                embedVar.add_field(name="Blue Alliance", value=(str(row["matchBrief_blue_team1"]) + "\n" + str(row["matchBrief_blue_team2"])), inline=False)

                await ctx.send(embed=embedVar)
    else:
        logger.error("[chshigh] " + "FTC Event Server is not enabled!")

#23JAN22
@bot.command(name="autohigh", aliases=['ah', 'ahigh'])
async def autohigh(ctx):
    logger.info("[autohigh] " + ctx.message.author.display_name + " tried to run command " + ctx.message.content)

    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 0 or x.channelType == 1]:
        logger.info("[autohigh] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        try:
            mySQLConnection = mysql.connector.connect(user=mySQL_USER, password=mySQL_PASSWORD, host=mySQL_HOST, database=mySQL_DATABASE)
            mySQLCursor = mySQLConnection.cursor(dictionary=True)
            logger.info("[autohigh] " + "Connected to SQL Database")
        except mysql.connector.Error as err:
            logger.error("[autohigh] " + "ERROR when trying to connect to SQL Database.")
            logger.error("[autohigh] " + err.msg)

        # For every event that we are currently monitoring (aka every active event
        for evnt in events:
            logger.info("[autohigh] " + "Processing event: " + evnt.eventCode)

            #get the high score for each event
            SQLStatement = "SELECT eventCode,matchBrief_matchName,startTime,redScore,blueScore,red_auto,blue_auto,matchBrief_red_team1,matchBrief_red_team2,matchBrief_blue_team1,matchBrief_blue_team2 FROM {table_name} WHERE (red_auto = (SELECT GREATEST(MAX(red_auto), MAX(blue_auto)) AS highScore  FROM {table_name} WHERE `eventCode` LIKE '{event_code}') OR blue_auto = (SELECT GREATEST(MAX(red_auto), MAX(blue_auto)) AS highScore  FROM {table_name} WHERE `eventCode` LIKE '{event_code}')) AND `eventCode` LIKE '{event_code}';".format(table_name=mySQL_TABLE,event_code=evnt.eventCode)

            try:
                mySQLCursor.execute(SQLStatement)
                result = mySQLCursor.fetchall()
            except mysql.connector.Error as err:
                logger.error("[autohigh] " + "ERROR when trying to SELECT from SQL Database.")
                logger.error("[autohigh] " + "Something went wrong: {}".format(err))
                logger.error("[autohigh] %s" % (SQLStatement,))
            except Exception as err:
                logger.error("[autohigh] " + "ERROR when trying to SELECT from SQL Database.")
                logger.error("[autohigh] " + "Something went wrong: {}".format(err))
                logger.error("[autohigh] %s" % (SQLStatement,))

            for row in result:
                embedVar = discord.Embed(title="EVENT AUTO HIGH SCORE", description=("Current High Auto Score for " + evnt.eventName), color=discord.Colour.blue())

                embedVar.add_field(name="Match Number", value=row["matchBrief_matchName"], inline=False)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                #RED LEFT BLUE RIGHT
                embedVar.add_field(name="Red Score", value=str(row["redScore"]), inline=True)
                embedVar.add_field(name="Blue Score", value=str(row["blueScore"]), inline=True)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                if row["red_auto"] > row["blue_auto"]:
                    embedVar.add_field(name="Red Auto", value=(str(row["red_auto"]) + " 🏆"), inline=True)
                    embedVar.add_field(name="Blue Auto", value=str(row["blue_auto"]), inline=True)
                elif row["red_auto"] < row["blue_auto"]:
                    embedVar.add_field(name="Red Auto", value=str(row["red_auto"]), inline=True)
                    embedVar.add_field(name="Blue Auto", value=(str(row["blue_auto"]) + " 🏆"), inline=True)
                elif row["red_auto"] == row["blue_auto"]:
                    embedVar.add_field(name="Red Auto", value=(str(row["red_auto"]) + " 🏆"), inline=True)
                    embedVar.add_field(name="Blue Auto", value=(str(row["blue_auto"]) + " 🏆"), inline=True)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                embedVar.add_field(name="Red Alliance", value=(str(row["matchBrief_red_team1"]) + " - " + evnt.teams[row["matchBrief_red_team1"]].name + "\n" + str(row["matchBrief_red_team2"]) + " - " + evnt.teams[row["matchBrief_red_team2"]].name), inline=False)
                embedVar.add_field(name="Blue Alliance", value=(str(row["matchBrief_blue_team1"]) + " - " + evnt.teams[row["matchBrief_blue_team1"]].name + "\n" + str(row["matchBrief_blue_team2"]) + " - " + evnt.teams[row["matchBrief_blue_team2"]].name), inline=False)

                await ctx.send(embed=embedVar)

#23JAN22
@bot.command(name="highscore", aliases=['hs', 'high', 'h'])
async def highscore(ctx):
    logger.info("[highscore] " + ctx.message.author.display_name + " tried to run command " + ctx.message.content)

    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 0 or x.channelType == 1]:
        logger.info("[highscore] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        try:
            mySQLConnection = mysql.connector.connect(user=mySQL_USER, password=mySQL_PASSWORD, host=mySQL_HOST, database=mySQL_DATABASE)
            mySQLCursor = mySQLConnection.cursor(dictionary=True)
            logger.info("[highscore] " + "Connected to SQL Database")
        except mysql.connector.Error as err:
            logger.error("[highscore] " + "ERROR when trying to connect to SQL Database.")
            logger.error("[highscore] " + err.msg)

        # For every event that we are currently monitoring (aka every active event
        for evnt in events:
            logger.info("[highscore] " + "Processing event: " + evnt.eventCode)

            #get the high score for each event
            SQLStatement = "SELECT eventCode,matchBrief_matchName,startTime,redScore,blueScore,red_auto,blue_auto,matchBrief_red_team1,matchBrief_red_team2,matchBrief_blue_team1,matchBrief_blue_team2 FROM {table_name} WHERE (redScore = (SELECT GREATEST(MAX(redScore), MAX(blueScore)) AS highScore  FROM {table_name} WHERE `eventCode` LIKE '{event_code}') OR blueScore = (SELECT GREATEST(MAX(redScore), MAX(blueScore)) AS highScore  FROM {table_name} WHERE `eventCode` LIKE '{event_code}')) AND `eventCode` LIKE '{event_code}';".format(table_name=mySQL_TABLE,event_code=evnt.eventCode)

            try:
                mySQLCursor.execute(SQLStatement)
                result = mySQLCursor.fetchall()
            except mysql.connector.Error as err:
                logger.error("[highscore] " + "ERROR when trying to SELECT from SQL Database.")
                logger.error("[highscore] " + "Something went wrong: {}".format(err))
                logger.error("[highscore] %s" % (SQLStatement,))
            except Exception as err:
                logger.error("[highscore] " + "ERROR when trying to SELECT from SQL Database.")
                logger.error("[highscore] " + "Something went wrong: {}".format(err))
                logger.error("[highscore] %s" % (SQLStatement,))

            for row in result:
                embedVar = discord.Embed(title="EVENT HIGH SCORE", description=("Current High Score for " + evnt.eventName), color=discord.Colour.blue())

                embedVar.add_field(name="Match Number", value=row["matchBrief_matchName"], inline=False)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                #RED LEFT BLUE RIGHT
                if row["redScore"] > row["blueScore"]:
                    embedVar.add_field(name="Red Score", value=(str(row["redScore"]) + " 🏆"), inline=True)
                    embedVar.add_field(name="Blue Score", value=str(row["blueScore"]), inline=True)
                elif row["redScore"] < row["blueScore"]:
                    embedVar.add_field(name="Red Score", value=str(row["redScore"]), inline=True)
                    embedVar.add_field(name="Blue Score", value=(str(row["blueScore"]) + " 🏆"), inline=True)
                elif row["redScore"] == row["blueScore"]:
                    embedVar.add_field(name="Red Score", value=(str(row["redScore"]) + " 🏆"), inline=True)
                    embedVar.add_field(name="Blue Score", value=(str(row["blueScore"]) + " 🏆"), inline=True)

                embedVar.add_field(name=chr(173), value=chr(173), inline=False)

                embedVar.add_field(name="Red Alliance", value=(str(row["matchBrief_red_team1"]) + " - " + evnt.teams[row["matchBrief_red_team1"]].name + "\n" + str(row["matchBrief_red_team2"]) + " - " + evnt.teams[row["matchBrief_red_team2"]].name), inline=False)
                embedVar.add_field(name="Blue Alliance", value=(str(row["matchBrief_blue_team1"]) + " - " + evnt.teams[row["matchBrief_blue_team1"]].name + "\n" + str(row["matchBrief_blue_team2"]) + " - " + evnt.teams[row["matchBrief_blue_team2"]].name), inline=False)

                await ctx.send(embed=embedVar)

#KLT - 30NOV21 2058 - Added Ping Command
@bot.command(name="ping")
async def ping(ctx):
    #25AUG22 - Added debug
    logger.debug("[ping] " + ctx.message.author.display_name + " attempting to run command.")
    logger.debug("[ping] ROLE_ADMINISTRATOR: " + ROLE_ADMINISTRATOR.lower())
    for y in ctx.message.author.roles:
        logger.debug("[ping] " + ctx.message.author.display_name + " role: " + y.name.lower())

    #30JAN22 - Removed channel restriction
    if ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info(ctx.message.author.display_name + " ran command " + ctx.message.content)
        await ctx.send("Pong")

#22JAN22 - Added vPing Command
@bot.command(name="vping")
async def vPing(ctx):
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info("[vping] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        quotes = [
            "So. How are you holding up?",
            "Thank you for helping us help you help us all.",
            #"Momentum, a function of mass and velocity, is conserved between portals. In layman's terms, speedy thing goes in, speedy thing comes out.",
            "There. Try it now.",
            "This is one of MY tests!",
            "For the record: You ARE adopted, and that's TERRIBLE.",
            "Press the button!",
            "Here Come The Test Results: You Are A Horrible Person. That's What It Says, A Horrible Person. We Weren't Even Testing For That.",
            "How Are You Holding Up? Because I'm A Potato."
            "I'm fine. Two plus two is...ten, in base four, I'm fine!"
        ]

        message = random.choice(quotes)
        await playVoice(ctx, message, "com.au")
            
#23JAN22 - Moved this to its own function so we can call it multiple times
async def playVoice(ctx, msg, accent='com'):
    if BOTTTSENABLED.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']:
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if not voice is None: #test if voice is None
            if not voice.is_connected():
                await voiceJoin()
        else:
            await voiceJoin()

        if not bot.voice_clients == None:
            logger.debug("[playVoice] " + "Trying to play TTS: " + msg)

            fp = BytesIO()
            gTTS(text=msg, lang='en', tld=accent, slow=False).write_to_fp(fp)
            fp.seek(0)

            for vc in bot.voice_clients:
                if vc.is_playing():
                    logger.info("[playVoice] " + "Sound is already playing. Stopping.")
                    vc.stop()

                try:
                    #22JAN22 - Using Example Code (https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py)
                    #https://stackoverflow.com/questions/68123040/discord-py-play-gtts-without-saving-the-audio-file
                    #https://github.com/Rapptz/discord.py/pull/5855
                    vc.play(FFmpegPCMAudioGTTS(fp.read(), pipe=True))

                    while vc.is_playing():
                        await asyncio.sleep(1)
                        
                    logger.info("[playVoice] " + "Finished playing audio")
                except Exception as err:
                    logger.error("[playVoice] " + "ERROR when trying to send TTS to channel .")
                    logger.error("[playVoice] " + "Something went wrong: {}".format(err))
                    logger.error("[playVoice] %s" % (err,))

        if not voice is None:
            if not voice.is_connected():
                await voiceStop()
        else:
            await voiceStop()

@bot.command(name='ftcteamtoa')
async def getFTCTeamDataTOA(ctx, team_number: str):
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 0 or x.channelType == 1]:
    #if ctx.message.channel.name == BOTPRODUCTIONCHANNEL or ctx.message.channel.name == BOTADMINCHANNEL:
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
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 0 or x.channelType == 1]:
        teamNumberInt = int(team_number)
        if team_number.isnumeric() and teamNumberInt >= 0 and len(team_number) <= 5:
            logger.info(ctx.message.author.display_name + " requested team number " + team_number + " from FIRST FTC DB.")
            teamFound = False
 
            for evnt in events: #30JAN22 - Updated to use new for loop format
                logger.info("[ftcteam] " + "Processing event: " + evnt.eventCode)
                if teamNumberInt in evnt.teams:
                    teamFound = True
                    await ctx.send("""```""" + "FIRST Tech Challenge (FTC) Team Information" + "\n" + "--------------------------------------------------" + "\n" + "Team Number: " + team_number + "\n" + "Team Name: " + evnt.teams[teamNumberInt].name + "\n" + "Team Long Name: " + evnt.teams[teamNumberInt].school + "\n" + "Location: " + evnt.teams[teamNumberInt].city + ", " + evnt.teams[teamNumberInt].state + " " + evnt.teams[teamNumberInt].country + "\n" + "Rookie Year: " + str(evnt.teams[teamNumberInt].rookie) + """```""")
                    break            
            if teamFound == False:
                try:
                    apiheaders = {'Accept':'application/json', 'Authorization':'Basic ' + FTCEVENTS_KEY}
                    response = requests.get('https://ftc-api.firstinspires.org/v2.0/2021/teams?teamNumber='+team_number, headers=apiheaders, timeout=3)
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
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 0 or x.channelType == 1]:
        if team_number.isnumeric() and int(team_number) >= 0 and len(team_number) <= 4:
            logger.info(ctx.message.author.display_name + " requested team number " + team_number + " from FIRST FRC DB.")
            
            try:
                apiheaders = {'Accept':'application/json', 'Authorization':'Basic '+FRCEVENTS_KEY}
                response = requests.get('https://frc-api.firstinspires.org/v3.0/2022/teams?teamNumber='+team_number, headers=apiheaders, timeout=3) #v2.3.0 - Updated for 2022 FRC Season and v3 API
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
                
@bot.group(pass_context=True)
async def ftc(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send('Invalid command passed...')
        logger.info("[ftc] " + ctx.message.author.display_name + " ran command " + ctx.message.content)

@ftc.group(pass_context=True)
async def event(ctx):
    if ctx.invoked_subcommand is event:
        await ctx.send('Invalid sub command passed...')  
        logger.info("[ftc][event] " + ctx.message.author.display_name + " ran command " + ctx.message.content)

@event.command(name='get')
async def GetEvents(ctx):
    logger.info("[ftc][event][get] " + ctx.message.author.display_name + " tried to run command " + ctx.message.content)
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info("[ftc][event][get] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        #logger.info("[highscore] " + "Events List: " + events)
        for evnt in events:
            logger.info("[ftc][event][get] Bot is currently monitoring: " + evnt.eventCode )

# TODO - Add Rename capability to event
@event.command(name='edit', aliases=['rename'])
async def editEvent(ctx, eventCode, eventName):
    logger.info("[ftc][event][edit] " + ctx.message.author.display_name + " tried to run command " + ctx.message.content)
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info("[ftc][event][edit] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        
        eventFound = False

        for evnt in events:
            if eventCode == evnt.eventCode:
                eventFound = True

                evnt.eventName = eventName

        if not eventFound:
            logger.error("[ftc][event][edit] Unable to edit event! Event code was not being monitored by system: " + eventCode + ".")
            await ctx.send("[ftc][event][edit] ERROR: System is not monitoring event " + eventCode)

@event.command(name='add', aliases=['start'])
async def addEvent(ctx, eventCode, eventName):
    logger.info("[ftc][event][add] " + ctx.message.author.display_name + " tried to run command " + ctx.message.content)
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info("[ftc][event][add] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        
        #If the event code is NOT already in the events DICT
        if not eventCode in events:
            #Check that we received a valid eventcode
            #Validate Event Code
            
            #If this is the first event we are monitoring join voice
            if (not events):
                if BOTTTSENABLED.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']:
                    await voiceJoin()

                await bot.change_presence(activity=discord.Streaming(name="FIRST Chesapeake Event", url="https://www.twitch.tv/firstchesapeake"))
                
            try:
                apiheaders = {'Content-Type':'application/json'}
                response = requests.get(FTCEVENTSERVER + "/api/v1/events/" + eventCode + "/", headers=apiheaders, timeout=3)
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
                    logger.info("[ftc][event][add] Attempting to make FTCEvent Instance")

                    await ctx.message.add_reaction('⚠')

                    #e = FTCEvent(responseData, bot, BOTPRODUCTIONCHANNEL_ID, BOTADMINCHANNEL_ID)
                    e = FTCEvent(responseData, bot, DiscordChannel.AllDiscordChannels.copy(), eventName)
                    
                    #Store instance in list
                    events.append(e)

                    #Add reaction to message to let user know it was created successfully
                    await ctx.message.remove_reaction('⚠', ctx.message.author)
                    await ctx.message.add_reaction('✅')
                    await playVoice(ctx, "Monitoring " + eventName)

                else:
                    logger.warning("[ftc][event][add] " + ctx.message.author.display_name + " provided an invalid event code to the FTC Event Command!")
                    await ctx.send("ERROR: Invalid event code provided.")
        else:
            logger.info("[ftc][event][add] Already monitoring event code " + eventCode + ".")
            await ctx.send("ERROR: System is already monitoring event " + eventCode)
    else:
        logger.warning(ctx.message.author.display_name + " attempted to invoke the FTC Event Command on server " + ctx.guild.name + "! Command provided: " + ctx.message.content)

@event.command(name='remove', aliases=['stop'])
async def removeEvent(ctx, eventCode):
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
        logger.info("[ftc][event][remove] " + ctx.message.author.display_name + " ran command " + ctx.message.content)
        logger.info("[ftc][event][remove] " + ctx.message.author.display_name + " is trying to stop the following event code: " + eventCode)

        if eventCode.lower() == "all".lower():
            for evnt in events:
                await evnt.stopWebSocket()
                events.remove(evnt)
                await ctx.message.add_reaction('🛑')
                
                #If this is the last event we were monitoring disconnect voice
                if not events and BOTTTSENABLED.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']:
                    await voiceStop()
        else:
            eventFound = False

            for evnt in events:
                if eventCode == evnt.eventCode:
                    eventFound = True

                    await evnt.stopWebSocket()
                    events.remove(evnt)
                    await ctx.message.add_reaction('🛑')
                    
                    #If this is the last event we were monitoring disconnect voice
                    if (not events): 
                        if BOTTTSENABLED.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']:
                            await voiceStop()
                        await bot.change_presence(status=None)
            if not eventFound:
                logger.error("Unable to remove event! Event code was not being monitored by system: " + eventCode + ".")
                await ctx.send("ERROR: System is not monitoring event " + eventCode)
    else:
        logger.warning(ctx.message.author.display_name + " attempted to invoke the FTC Event Command on server " + ctx.guild.name + "! Command provided: " + ctx.message.content)

@ftc.command()
async def server(ctx, verb: str, noun: str):
    if ctx.message.channel.name in [x.name.lower() for x in DiscordChannel.AllDiscordChannels if x.channelType == 1] and ROLE_ADMINISTRATOR.lower() in [y.name.lower() for y in ctx.message.author.roles]:
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
                        responseData = json.loads(response.text)

                        logger.info("Received API Key: " + responseData["key"])
                        await ctx.send("Received API Key: " + responseData["key"])
                    elif response.status_code == 400:
                        logger.error("Must include name as a parameter when requesting API key.")
                    else:
                        logger.warning("Invalid response from server.")
                        await ctx.send("ERROR: Invalid response from server.")
            elif checkFTCEVENTSERVER_APIKey() == False:
                #If the API key we have is invalid get a new one
                logger.error("Supplied API Key does not exist. Requesting new API Key as it was explicity requested.")
                logger.info("Requesting FTC Event Server API Key")

                try:
                    apiheaders = {'Content-Type':'application/json'}
                    response = requests.post(FTCEVENTSERVER + "/api/v1/keyrequest/", data = {"name":"FIRSTChesapeakeDiscordBot"}, timeout=3)

                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    #Server is offline and needs to be handled
                    logger.error("Failed to contact FTC Event Server!")
                    await ctx.send("ERROR: Failed to contact FTC Event Server!")
                except:
                    logger.error("Unspecified Error!")
                else:
                    #We received a reply from the server
                    logger.info("Received Response Code: " + response.status_code)

                    responseData = json.loads(response.text)
                    
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
    logger.warning(ctx.message.author.display_name + " has requested the removal of " + str(amount) + " messages from channel " + ctx.message.channel.name)
    
    # Check from https://stackoverflow.com/questions/53643906/discord-py-delete-all-messages-except-pin-messages
    await ctx.channel.purge(limit=amount + 1, check=lambda msg: not msg.pinned)
        
        
# ===== END COMMANDS SECTION =====

# ===== START BOT EVENT SECTION ===== 

#30JAN22 - On Voice Channel Join
#TODO
@bot.event
async def on_voice_state_update(member, before, after):
    logger.info("[on_voice_state_update] " + member.display_name + " has updated their voice status!")

    if after.channel is not None:
        for guild in bot.guilds:
            logger.debug("[on_voice_state_update] Guild Name: " + guild.name)
            obj_ROLE_ACTIVECOMMENTATOR = guild.get_role(ROLE_ACTIVECOMMENTATOR)

        logger.debug("[on_voice_state_update] obj_ROLE_ACTIVECOMMENTATOR: " + obj_ROLE_ACTIVECOMMENTATOR.name)

        if after.channel.id == ID_Channel_Voice_CommentatorLive: # If the joined channel is COMMENTATOR LIVE
            if ROLE_COMMENTATOR in [y.id for y in member.roles]: #If the user is a COMMENTATOR
                if ROLE_ACTIVECOMMENTATOR not in [y.id for y in member.roles]: #If the user is NOT already an ACTIVE COMMANTATOR
                    #Assign the role
                    logger.info("[on_voice_state_update][ACTIVECOMMENTATOR] Adding " + member.display_name + " to Active Commentator Role!")
                    await member.add_roles(obj_ROLE_ACTIVECOMMENTATOR)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        logger.warning(ctx.message.author.display_name + " attempted to invoke an invalid command on server " + ctx.guild.name + "! Command provided: " + ctx.message.content)
        #await ctx.send('ERROR: The entered command does not exist!')
        
@bot.event
async def on_ready():
    # Check if we have a valid API key
    if bool_FTCEVENTSSERVER:
        checkFTCEVENTSERVER_APIKey()
        
    # Get the Channel IDs for the channels we need
    findChannels()
    
    #React to the Alumni Message on bot start
    tChannel = bot.get_channel(ID_Channel_ReactionMonitor)
    tMessage = await tChannel.fetch_message(ID_Message_ReactionMonitor)
    await tMessage.add_reaction('🤖')

    #Start the task to remove the active Commentator Role
    #removeActiveCommentatorRole.start()

@bot.event
async def on_member_join(member):
    logger.info(member.display_name + " has joined the server! Adding member to the " + ROLE_NEWUSER + " role.")
    # Help from https://stackoverflow.com/questions/59052536/attributeerror-bot-object-has-no-attribute-add-roles
    role = discord.utils.get(member.guild.roles, name=ROLE_NEWUSER)
    await member.add_roles(role)

#This requires Intents.reactions to be enabled.
@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return

    # If a user adds a reaction to the specific Message then add the Alumni Role
    if payload.message_id == int(ID_Message_ReactionMonitor):
        if ROLE_NEWUSER.lower() not in [y.name.lower() for y in payload.member.roles]:
            if str(payload.emoji) == '🤖':
                if ROLE_ReactionMonitor.lower() not in [y.name.lower() for y in payload.member.roles]:
                    logger.info("[on_raw_reaction_add] " + payload.member.display_name + " has reacted to the Alumni message, adding them to the Alumni Role!")
                    role = discord.utils.get(payload.member.guild.roles, name=ROLE_ReactionMonitor)
                    await payload.member.add_roles(role)
                else:
                    logger.info("[on_raw_reaction_add] " + payload.member.display_name + " has reacted to the Alumni message but was already an added. Removing  them from the Alumni Role!")
                    role = discord.utils.get(payload.member.guild.roles, name=ROLE_ReactionMonitor)
                    await payload.member.remove_roles(role)
                    
                #Remove the user's reaction when done
                tChannel = bot.get_channel(payload.channel_id)
                tMessage = await tChannel.fetch_message(payload.message_id)
                await tMessage.remove_reaction('🤖', payload.member)
        else:
            logger.info("[on_raw_reaction_add] " + payload.member.display_name + " who is a member of " + ROLE_NEWUSER + " tried to add the Alumni Role!")
            tChannel = bot.get_channel(payload.channel_id)
            tMessage = await tChannel.fetch_message(payload.message_id)
            await tMessage.remove_reaction('🤖', payload.member)
        
#NOTE: I tried to remove the role when the user removes the reaction but payload.member is not exposed in the Discord.py API on removal...

# ===== END BOT EVENT SECTION ===== 


# ===== START FUNCTION SECTION ===== 

#TODO
#30JAN22 - Remove Active Commentator Role at Midnight Eastern
#tz = datetime.timezone(datetime.timedelta(hours=-5))

#when = [
#    datetime.time(0, 0, tzinfo=tz),   # EST midnight
#]

#@tasks.loop(time=when)
#async def removeActiveCommentatorRole():
#    role = discord.utils.get(bot.guilds.roles, id=ROLE_ReactionMonitor)
#    for member in bot.get_all_members():
#        if role in member.roles:
#            await member.remove_roles(role)

async def voiceJoin():
    for channel in bot.get_all_channels(): 
        if channel.name.lower() == BOTTTSCHANNEL.lower() and str(channel.type) == "voice":
            logger.info("[" + channel.name + "] " + "Channel ID Found: "  + str(channel.id))
            logger.info("[" + channel.name + "] " + "Joining Channel!")
            await channel.connect()
            
async def voiceStop():
    for vc in bot.voice_clients:
        await vc.disconnect(force=True)

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

                #TEMP - Testing casting to bool
                if bool(responseData["active"]):
                    logger.info("API Key is active")
                    return True
                else:
                    #Not a active API key
                    logger.info("API Key is NOT active. Please activate it in the FTC Event Server.")
                    return False
            elif response.status_code == 404:
                logger.error("Supplied API Key does not exist. Please request one, update .env file, and restart the bot.")
                return False
            else:
                logger.warning("Invalid response from server.")
                return False
    else:
        logger.error("FTC Event Server API Key is not set! Please request one, update .env file, and restart the bot.")

def findChannels():
    
    if BOTPRODUCTIONCHANNELS == None:
        #BOTPRODUCTIONCHANNELS is empty and needs to be handled
        logger.error("BOTPRODUCTIONCHANNELS is not set!")
        raise
        
    if BOTADMINCHANNELS == None:
        #BOTADMINCHANNELS is empty and needs to be handled
        logger.error("BOTADMINCHANNELS is not set!")
        raise
    
    if BOTMATCHRESULTCHANNELS == None:
        #BOTMATCHRESULTCHANNELS is empty and needs to be handled
        logger.error("BOTMATCHRESULTCHANNELS is not set!")
        raise
    
    if "," in str(BOTPRODUCTIONCHANNELS):
        f = StringIO(BOTPRODUCTIONCHANNELS)
        channels = next(csv.reader(f, delimiter=','))
        for channel in channels:
            DiscordChannel(bot, bot.get_all_channels(), channel, 0)
    else:
      DiscordChannel(bot, bot.get_all_channels(), BOTPRODUCTIONCHANNELS, 0)  
    
    if "," in str(BOTADMINCHANNELS):
        f = StringIO(BOTADMINCHANNELS)
        channels = next(csv.reader(f, delimiter=','))
        for channel in channels:
            DiscordChannel(bot, bot.get_all_channels(), channel, 1)
    else:
        DiscordChannel(bot, bot.get_all_channels(), BOTADMINCHANNELS, 1)

    if bool_FTCEVENTSSERVER:
        if "," in str(BOTMATCHRESULTCHANNELS):
            f = StringIO(BOTMATCHRESULTCHANNELS)
            channels = next(csv.reader(f, delimiter=','))
            for channel in channels:
                DiscordChannel(bot, bot.get_all_channels(), channel, 3)
        else:
            DiscordChannel(bot, bot.get_all_channels(), BOTMATCHRESULTCHANNELS, 3)
    
    for channel in DiscordChannel.AllDiscordChannels:
        logger.debug("[findChannels] " + channel.name)

async def stopWebSockets():
    #Stop the websocket for each event
    logger.info("Stopping all websockets")

    #28JAN22 - Updated code to use consistant for loop that we know works.
    for evnt in events:
        logger.info("[stopWebSockets] " + "Processing event: " + evnt.eventCode)
        await evnt.stopWebSocket()

async def stopDiscordBot():
    #Stop the Discord Bot
    logger.info("[stopDiscordBot] Logging out Discord bot!")

    #Set the bot's status to offline
    await bot.change_presence(status=discord.Status.offline)

    #Logout/Close the bot
    await bot.close()   

async def stopBot():
    logger.info("[stopBot] Function was called!")

    #Removing because default close() command handles this
    #f_task3 = asyncio.create_task(voiceStop())
    #loop.run_until_complete(f_task3)
    if bool_FTCEVENTSSERVER:
        f_task1 = asyncio.create_task(stopWebSockets())
        f_task2 = asyncio.create_task(stopDiscordBot())
        await asyncio.wait({f_task1, f_task2}, return_when=asyncio.ALL_COMPLETED)

    #Tell logger to orderly shutdown all logs
    logger.warning("[stopBot] Bot has shut down. Stopping logging!")
    logging.shutdown()

    # FIN
# ===== END FUNCTION SECTION =====     


# Write to the log to let us know the bot is, about to be, online and ready to go
logger.info("[main] Bot started and connecting to DISCORD")

# Script will hold on this call untill process/container is stopped
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print(e)
finally:
    # All calls after the above should only run when process/container is being stopped
    logger.warning("[WARNING] THE BOT IS SHUTTING DOWN!")
    asyncio.run(stopBot())