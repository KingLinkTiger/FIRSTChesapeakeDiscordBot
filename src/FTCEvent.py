import os
from datetime import datetime, timedelta
import requests
import requests_cache
import json
import asyncio
import websockets
import logging
import discord

from discord.ext import commands
from dotenv import load_dotenv

import mysql.connector
from mysql.connector import Error

from FTCTeam import FTCTeam
from DiscordChannel import DiscordChannel

#For TTS
from gtts import gTTS
from io import BytesIO

load_dotenv()

FTCEVENTSERVER = os.getenv('FTCEVENTSERVER')
FTCEVENTSERVER_WEBSOCKETURL = os.getenv('FTCEVENTSERVER_WEBSOCKETURL')
BOTPRODUCTIONCHANNEL = os.getenv('BOTPRODUCTIONCHANNEL')
FTCEVENTSERVER_APIKey = os.getenv('FTCEVENTSERVER_APIKey')

mySQL_USER = os.getenv('mySQL_USER')
mySQL_PASSWORD = os.getenv('mySQL_PASSWORD')
mySQL_HOST = os.getenv('mySQL_HOST')
mySQL_DATABASE = os.getenv('mySQL_DATABASE')
mySQL_TABLE = os.getenv('mySQL_TABLE')


class FTCEvent:
    logger = logging.getLogger('FIRSTChesapeakeBot')
  
    def __init__(self, eventData, bot, AllDiscordChannels, eventName): 
        self.eventCode = eventData["eventCode"]
        self.eventName = eventName
        self.name = eventData["name"]
        self.bot = bot
        self.AllDiscordChannels = AllDiscordChannels
   
        self.logger.info("[" + self.name + "] " + "Creating Event Instance")
        
        
        #TODO: USE THIS
        #Initialize a variable to store the last state message we received from the server
        #self.lastState = ""
        
        self.getTeams()

        self.task = asyncio.create_task(self.startWebSocket())

        
    def getTeams(self):
        self.logger.info("[" + self.name + "] " + "Getting teams data")
        if not hasattr(self, "teams"):
            self.logger.info("[" + self.name + "] " + "Teams attribute does not exist making it")
            self.teams = {}
            
            #Get the API calls to get the teams information
            #Get list of compeating teams GetCompetingTeams
            
            apiheaders = {'Content-Type':'application/json', 'Authorization':FTCEVENTSERVER_APIKey}
            
            response = requests.get(FTCEVENTSERVER + "/api/v1/events/" + self.eventCode + "/teams/", headers=apiheaders)
            
            responseData = json.loads(response.text)
            
            #print("Competing Team List Received Status Code: " + str(response.status_code))
            
            #print(response.text)
            
            #Get team details for each team
            for team in responseData["teamNumbers"]:              
                self.logger.info("[" + self.name + "] " + "Sending request for team: " + str(team))
                
                teamResponse = requests.get(FTCEVENTSERVER + "/api/v1/events/" + self.eventCode + "/teams/" + str(team), headers=apiheaders)
                
                #print("Received Status Code: " + str(teamResponse.status_code))
            
                teamResponseData = json.loads(teamResponse.text)

                self.teams[team] = FTCTeam(teamResponseData)
     
    # FTC SCOREKEEPER WEBSOCKET FUNCTIONS

    async def matchLoad(self, json_data):      
        #Query the API for the Match Brief information
        # ***NOTE*** THIS ONLY WORKS FOR QUALIFICATION MATCHES!!!!
        #Error checking to make sure the supplied match is a Q match
        if json_data["payload"]["shortName"][0] == 'Q':
            apiheaders = {'Content-Type':'application/json', 'Authorization':FTCEVENTSERVER_APIKey}
            response = requests.get(FTCEVENTSERVER + "/api/2021/v1/events/" + self.eventCode + "/matches/" + str(json_data["payload"]["number"]) + "/", headers=apiheaders)
            
            matchBrief = json.loads(response.text)
            
            red1 = matchBrief["matchBrief"]["red"]["team1"]
            red2 = matchBrief["matchBrief"]["red"]["team2"]
            blue1 = matchBrief["matchBrief"]["blue"]["team1"]
            blue2 = matchBrief["matchBrief"]["blue"]["team2"]
            
            #Access to the Discord Client
            await self.sendMatchResult("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH LOADED" + "\n" + "--------------------------------------------------" + "\n" + "Red  1: " + str(red1) + " - " + self.teams[red1].name + "\n" + "Red  2: " + str(red2) + " - " + self.teams[red2].name  + "\n" + "Blue 1: " + str(blue1) + " - " + self.teams[blue1].name  + "\n" + "Blue 2: " + str(blue2) + " - " + self.teams[blue2].name  + """```""")
            
    async def matchStart(self, json_data):  
        await self.sendMatchResult("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH STARTED" + """```""")
        await self.sendTTS(self.eventName + " has started")
        
    async def matchCommit(self, json_data):         
        if json_data["payload"]["shortName"][0] == 'Q':
            apiheaders = {'Content-Type':'application/json', 'Authorization':FTCEVENTSERVER_APIKey}

            #Clear the cache for this URL in order to get fresh data every time
            with requests_cache.disabled():
                response = requests.get(FTCEVENTSERVER + "/api/2021/v1/events/" + self.eventCode + "/matches/" + str(json_data["payload"]["number"]) + "/", headers=apiheaders)
     
            matchResults = json.loads(response.text)
        
            #Save the data to the SQL Server
            #Only connect to the SQL server when we're about to write to the DB otherwise the connection dies after a while or on mySQL reboots
            self.logger.info("[" + self.name + "][mySQL] " + "Trying to connect to SQL Database")
            try:
                self.mySQLConnection = mysql.connector.connect(user=mySQL_USER, password=mySQL_PASSWORD, host=mySQL_HOST, database=mySQL_DATABASE)
                self.mySQLCursor = self.mySQLConnection.cursor()
                self.logger.info("[" + self.name + "][mySQL] " + "Connected to SQL Database")
            except mysql.connector.Error as err:
                self.logger.error("[" + self.name + "][mySQL] " + "ERROR when trying to connect to SQL Database.")
                self.logger.error("[" + self.name + "][mySQL] " + err.msg)
            
            #Check if the match already exists in the DB
            SQLStatement = "SELECT EXISTS(SELECT * FROM {table_name} WHERE `eventCode` = %s AND `matchBrief_matchNumber` = %s)".format(table_name=mySQL_TABLE)
            SQLData = (self.eventCode, matchResults["matchBrief"]["matchNumber"])
            
            try:
                self.mySQLCursor.execute(SQLStatement, SQLData)
                result = self.mySQLCursor.fetchall()
            except mysql.connector.Error as err:
                self.logger.error("[" + self.name + "][mySQL] " + "ERROR when trying to INSERT into the SQL Database.")
                self.logger.error("[" + self.name + "][mySQL] " + "Something went wrong: {}".format(err))
                self.logger.error("[" + self.name + "][mySQL] %s" % (SQLData,))
            
            #If the match has already been committed previously we must update the row already there
            if bool(result[0][0]):
                SQLStatement = "UPDATE {table_name} SET `eventCode`=%s,`startTime`=FROM_UNIXTIME(%s),`scheduledTime`=FROM_UNIXTIME(%s),`resultPostedTime`=FROM_UNIXTIME(%s),`redScore`=%s,`blueScore`=%s,`randomization`=%s,`matchBrief_matchState`=%s,`matchBrief_time`=FROM_UNIXTIME(%s),`matchBrief_matchName`=%s,`matchBrief_matchNumber`=%s,`matchBrief_field`=%s,`matchBrief_red_team1`=%s,`matchBrief_red_team2`=%s,`matchBrief_red_isTeam1Surrogate`=%s,`matchBrief_red_isTeam2Surrogate`=%s,`matchBrief_blue_team1`=%s,`matchBrief_blue_team2`=%s,`matchBrief_blue_isTeam1Surrogate`=%s,`matchBrief_blue_isTeam2Surrogate`=%s,`matchBrief_finished`=%s,`red_minorPenalties`=%s,`red_majorPenalties`=%s,`red_navigated1`=%s,`red_navigated2`=%s,`red_wobbleDelivered1`=%s,`red_wobbleDelivered2`=%s,`red_autoTowerLow`=%s,`red_autoTowerMid`=%s,`red_autoTowerHigh`=%s,`red_autoPowerShotLeft`=%s,`red_autoPowerShotCenter`=%s,`red_autoPowerShotRight`=%s,`red_driverControlledTowerLow`=%s,`red_driverControlledTowerMid`=%s,`red_driverControlledTowerHigh`=%s,`red_wobbleEnd1`=%s,`red_wobbleEnd2`=%s,`red_wobbleRings1`=%s,`red_wobbleRings2`=%s,`red_endgamePowerShotLeft`=%s,`red_endgamePowerShotCenter`=%s,`red_endgamePowerShotRight`=%s,`red_autoTowerPoints`=%s,`red_autoWobblePoints`=%s,`red_navigationPoints`=%s,`red_autoPowerShotPoints`=%s,`red_driverControlledTowerPoints`=%s,`red_endgamePowerShotPoints`=%s,`red_wobbleRingPoints`=%s,`red_endgameWobblePoints`=%s,`red_totalPoints`=%s,`red_auto`=%s,`red_teleop`=%s,`red_end`=%s,`red_penalty`=%s,`red_dq1`=%s,`red_dq2`=%s,`blue_minorPenalties`=%s,`blue_majorPenalties`=%s,`blue_navigated1`=%s,`blue_navigated2`=%s,`blue_wobbleDelivered1`=%s,`blue_wobbleDelivered2`=%s,`blue_autoTowerLow`=%s,`blue_autoTowerMid`=%s,`blue_autoTowerHigh`=%s,`blue_autoPowerShotLeft`=%s,`blue_autoPowerShotCenter`=%s,`blue_autoPowerShotRight`=%s,`blue_driverControlledTowerLow`=%s,`blue_driverControlledTowerMid`=%s,`blue_driverControlledTowerHigh`=%s,`blue_wobbleEnd1`=%s,`blue_wobbleEnd2`=%s,`blue_wobbleRings1`=%s,`blue_wobbleRings2`=%s,`blue_endgamePowerShotLeft`=%s,`blue_endgamePowerShotCenter`=%s,`blue_endgamePowerShotRight`=%s,`blue_autoTowerPoints`=%s,`blue_autoWobblePoints`=%s,`blue_navigationPoints`=%s,`blue_autoPowerShotPoints`=%s,`blue_driverControlledTowerPoints`=%s,`blue_endgamePowerShotPoints`=%s,`blue_wobbleRingPoints`=%s,`blue_endgameWobblePoints`=%s,`blue_totalPoints`=%s,`blue_auto`=%s,`blue_teleop`=%s,`blue_end`=%s,`blue_penalty`=%s,`blue_dq1`=%s,`blue_dq2`=%s WHERE `eventCode` = %s AND matchBrief_matchNumber = %s".format(table_name=mySQL_TABLE)
                
                
                SQLData = (self.eventCode, max(1, (matchResults["startTime"]/1000)), max(1, (matchResults["scheduledTime"]/1000)), max(1, (matchResults["resultPostedTime"]/1000)), matchResults["redScore"], matchResults["blueScore"], matchResults["randomization"], matchResults["matchBrief"]["matchState"], max(1, (matchResults["matchBrief"]["time"]/1000)), matchResults["matchBrief"]["matchName"], matchResults["matchBrief"]["matchNumber"], matchResults["matchBrief"]["field"], matchResults["matchBrief"]["red"]["team1"], matchResults["matchBrief"]["red"]["team2"], matchResults["matchBrief"]["red"]["isTeam1Surrogate"], matchResults["matchBrief"]["red"]["isTeam2Surrogate"], matchResults["matchBrief"]["blue"]["team1"], matchResults["matchBrief"]["blue"]["team2"], matchResults["matchBrief"]["blue"]["isTeam1Surrogate"], matchResults["matchBrief"]["blue"]["isTeam2Surrogate"], matchResults["matchBrief"]["finished"], matchResults["red"]["minorPenalties"], matchResults["red"]["majorPenalties"], matchResults["red"]["navigated1"], matchResults["red"]["navigated2"], matchResults["red"]["wobbleDelivered1"], matchResults["red"]["wobbleDelivered2"], matchResults["red"]["autoTowerLow"], matchResults["red"]["autoTowerMid"], matchResults["red"]["autoTowerHigh"], matchResults["red"]["autoPowerShotLeft"], matchResults["red"]["autoPowerShotCenter"], matchResults["red"]["autoPowerShotRight"], matchResults["red"]["driverControlledTowerLow"], matchResults["red"]["driverControlledTowerMid"], matchResults["red"]["driverControlledTowerHigh"], matchResults["red"]["wobbleEnd1"], matchResults["red"]["wobbleEnd2"], matchResults["red"]["wobbleRings1"], matchResults["red"]["wobbleRings2"], matchResults["red"]["endgamePowerShotLeft"], matchResults["red"]["endgamePowerShotCenter"], matchResults["red"]["endgamePowerShotRight"], matchResults["red"]["autoTowerPoints"], matchResults["red"]["autoWobblePoints"], matchResults["red"]["navigationPoints"], matchResults["red"]["autoPowerShotPoints"], matchResults["red"]["driverControlledTowerPoints"], matchResults["red"]["endgamePowerShotPoints"], matchResults["red"]["wobbleRingPoints"], matchResults["red"]["endgameWobblePoints"], matchResults["red"]["totalPoints"], matchResults["red"]["auto"], matchResults["red"]["teleop"], matchResults["red"]["end"], matchResults["red"]["penalty"], matchResults["red"]["dq1"], matchResults["red"]["dq2"], matchResults["blue"]["minorPenalties"], matchResults["blue"]["majorPenalties"], matchResults["blue"]["navigated1"], matchResults["blue"]["navigated2"], matchResults["blue"]["wobbleDelivered1"], matchResults["blue"]["wobbleDelivered2"], matchResults["blue"]["autoTowerLow"], matchResults["blue"]["autoTowerMid"], matchResults["blue"]["autoTowerHigh"], matchResults["blue"]["autoPowerShotLeft"], matchResults["blue"]["autoPowerShotCenter"], matchResults["blue"]["autoPowerShotRight"], matchResults["blue"]["driverControlledTowerLow"], matchResults["blue"]["driverControlledTowerMid"], matchResults["blue"]["driverControlledTowerHigh"], matchResults["blue"]["wobbleEnd1"], matchResults["blue"]["wobbleEnd2"], matchResults["blue"]["wobbleRings1"], matchResults["blue"]["wobbleRings2"], matchResults["blue"]["endgamePowerShotLeft"], matchResults["blue"]["endgamePowerShotCenter"], matchResults["blue"]["endgamePowerShotRight"], matchResults["blue"]["autoTowerPoints"], matchResults["blue"]["autoWobblePoints"], matchResults["blue"]["navigationPoints"], matchResults["blue"]["autoPowerShotPoints"], matchResults["blue"]["driverControlledTowerPoints"], matchResults["blue"]["endgamePowerShotPoints"], matchResults["blue"]["wobbleRingPoints"], matchResults["blue"]["endgameWobblePoints"], matchResults["blue"]["totalPoints"], matchResults["blue"]["auto"], matchResults["blue"]["teleop"], matchResults["blue"]["end"], matchResults["blue"]["penalty"], matchResults["blue"]["dq1"], matchResults["blue"]["dq2"], self.eventCode, matchResults["matchBrief"]["matchNumber"])
                
            else:
                SQLStatement = "INSERT INTO {table_name} (`eventCode`, `startTime`, `scheduledTime`, `resultPostedTime`, `redScore`, `blueScore`, `randomization`, `matchBrief_matchState`, `matchBrief_time`, `matchBrief_matchName`, `matchBrief_matchNumber`, `matchBrief_field`, `matchBrief_red_team1`, `matchBrief_red_team2`, `matchBrief_red_isTeam1Surrogate`, `matchBrief_red_isTeam2Surrogate`, `matchBrief_blue_team1`, `matchBrief_blue_team2`, `matchBrief_blue_isTeam1Surrogate`, `matchBrief_blue_isTeam2Surrogate`, `matchBrief_finished`, `red_minorPenalties`, `red_majorPenalties`, `red_navigated1`, `red_navigated2`, `red_wobbleDelivered1`, `red_wobbleDelivered2`, `red_autoTowerLow`, `red_autoTowerMid`, `red_autoTowerHigh`, `red_autoPowerShotLeft`, `red_autoPowerShotCenter`, `red_autoPowerShotRight`, `red_driverControlledTowerLow`, `red_driverControlledTowerMid`, `red_driverControlledTowerHigh`, `red_wobbleEnd1`, `red_wobbleEnd2`, `red_wobbleRings1`, `red_wobbleRings2`, `red_endgamePowerShotLeft`, `red_endgamePowerShotCenter`, `red_endgamePowerShotRight`, `red_autoTowerPoints`, `red_autoWobblePoints`, `red_navigationPoints`, `red_autoPowerShotPoints`, `red_driverControlledTowerPoints`, `red_endgamePowerShotPoints`, `red_wobbleRingPoints`, `red_endgameWobblePoints`, `red_totalPoints`, `red_auto`, `red_teleop`, `red_end`, `red_penalty`, `red_dq1`, `red_dq2`, `blue_minorPenalties`, `blue_majorPenalties`, `blue_navigated1`, `blue_navigated2`, `blue_wobbleDelivered1`, `blue_wobbleDelivered2`, `blue_autoTowerLow`, `blue_autoTowerMid`, `blue_autoTowerHigh`, `blue_autoPowerShotLeft`, `blue_autoPowerShotCenter`, `blue_autoPowerShotRight`, `blue_driverControlledTowerLow`, `blue_driverControlledTowerMid`, `blue_driverControlledTowerHigh`, `blue_wobbleEnd1`, `blue_wobbleEnd2`, `blue_wobbleRings1`, `blue_wobbleRings2`, `blue_endgamePowerShotLeft`, `blue_endgamePowerShotCenter`, `blue_endgamePowerShotRight`, `blue_autoTowerPoints`, `blue_autoWobblePoints`, `blue_navigationPoints`, `blue_autoPowerShotPoints`, `blue_driverControlledTowerPoints`, `blue_endgamePowerShotPoints`, `blue_wobbleRingPoints`, `blue_endgameWobblePoints`, `blue_totalPoints`, `blue_auto`, `blue_teleop`, `blue_end`, `blue_penalty`, `blue_dq1`, `blue_dq2`) VALUES (%s,FROM_UNIXTIME(%s),FROM_UNIXTIME(%s),FROM_UNIXTIME(%s),%s,%s,%s,%s,FROM_UNIXTIME(%s),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);".format(table_name=mySQL_TABLE)
            
                SQLData = (self.eventCode, max(1, (matchResults["startTime"]/1000)), max(1, (matchResults["scheduledTime"]/1000)), max(1, (matchResults["resultPostedTime"]/1000)), matchResults["redScore"], matchResults["blueScore"], matchResults["randomization"], matchResults["matchBrief"]["matchState"], max(1, (matchResults["matchBrief"]["time"]/1000)), matchResults["matchBrief"]["matchName"], matchResults["matchBrief"]["matchNumber"], matchResults["matchBrief"]["field"], matchResults["matchBrief"]["red"]["team1"], matchResults["matchBrief"]["red"]["team2"], matchResults["matchBrief"]["red"]["isTeam1Surrogate"], matchResults["matchBrief"]["red"]["isTeam2Surrogate"], matchResults["matchBrief"]["blue"]["team1"], matchResults["matchBrief"]["blue"]["team2"], matchResults["matchBrief"]["blue"]["isTeam1Surrogate"], matchResults["matchBrief"]["blue"]["isTeam2Surrogate"], matchResults["matchBrief"]["finished"], matchResults["red"]["minorPenalties"], matchResults["red"]["majorPenalties"], matchResults["red"]["navigated1"], matchResults["red"]["navigated2"], matchResults["red"]["wobbleDelivered1"], matchResults["red"]["wobbleDelivered2"], matchResults["red"]["autoTowerLow"], matchResults["red"]["autoTowerMid"], matchResults["red"]["autoTowerHigh"], matchResults["red"]["autoPowerShotLeft"], matchResults["red"]["autoPowerShotCenter"], matchResults["red"]["autoPowerShotRight"], matchResults["red"]["driverControlledTowerLow"], matchResults["red"]["driverControlledTowerMid"], matchResults["red"]["driverControlledTowerHigh"], matchResults["red"]["wobbleEnd1"], matchResults["red"]["wobbleEnd2"], matchResults["red"]["wobbleRings1"], matchResults["red"]["wobbleRings2"], matchResults["red"]["endgamePowerShotLeft"], matchResults["red"]["endgamePowerShotCenter"], matchResults["red"]["endgamePowerShotRight"], matchResults["red"]["autoTowerPoints"], matchResults["red"]["autoWobblePoints"], matchResults["red"]["navigationPoints"], matchResults["red"]["autoPowerShotPoints"], matchResults["red"]["driverControlledTowerPoints"], matchResults["red"]["endgamePowerShotPoints"], matchResults["red"]["wobbleRingPoints"], matchResults["red"]["endgameWobblePoints"], matchResults["red"]["totalPoints"], matchResults["red"]["auto"], matchResults["red"]["teleop"], matchResults["red"]["end"], matchResults["red"]["penalty"], matchResults["red"]["dq1"], matchResults["red"]["dq2"], matchResults["blue"]["minorPenalties"], matchResults["blue"]["majorPenalties"], matchResults["blue"]["navigated1"], matchResults["blue"]["navigated2"], matchResults["blue"]["wobbleDelivered1"], matchResults["blue"]["wobbleDelivered2"], matchResults["blue"]["autoTowerLow"], matchResults["blue"]["autoTowerMid"], matchResults["blue"]["autoTowerHigh"], matchResults["blue"]["autoPowerShotLeft"], matchResults["blue"]["autoPowerShotCenter"], matchResults["blue"]["autoPowerShotRight"], matchResults["blue"]["driverControlledTowerLow"], matchResults["blue"]["driverControlledTowerMid"], matchResults["blue"]["driverControlledTowerHigh"], matchResults["blue"]["wobbleEnd1"], matchResults["blue"]["wobbleEnd2"], matchResults["blue"]["wobbleRings1"], matchResults["blue"]["wobbleRings2"], matchResults["blue"]["endgamePowerShotLeft"], matchResults["blue"]["endgamePowerShotCenter"], matchResults["blue"]["endgamePowerShotRight"], matchResults["blue"]["autoTowerPoints"], matchResults["blue"]["autoWobblePoints"], matchResults["blue"]["navigationPoints"], matchResults["blue"]["autoPowerShotPoints"], matchResults["blue"]["driverControlledTowerPoints"], matchResults["blue"]["endgamePowerShotPoints"], matchResults["blue"]["wobbleRingPoints"], matchResults["blue"]["endgameWobblePoints"], matchResults["blue"]["totalPoints"], matchResults["blue"]["auto"], matchResults["blue"]["teleop"], matchResults["blue"]["end"], matchResults["blue"]["penalty"], matchResults["blue"]["dq1"], matchResults["blue"]["dq2"])

            try:
                self.mySQLCursor.execute(SQLStatement, SQLData)
                self.mySQLConnection.commit()
            except mysql.connector.Error as err:
                self.logger.error("[" + self.name + "][mySQL] " + "ERROR when trying to INSERT into the SQL Database.")
                self.logger.error("[" + self.name + "][mySQL] " + "Something went wrong: {}".format(err))
                self.logger.error("[" + self.name + "][mySQL] %s" % (SQLData,))
                
            #Cleanly close the cursor and connection once complete
            self.mySQLCursor.close()
            self.mySQLConnection.close()
            
            #Send the message to the production channels
            await self.sendMatchResult("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "--------------------MATCH RESULTS------------------------------" + "\n" + "Blue Score: " + str(matchResults["blueScore"]) + "\n" + "Red Score: " + str(matchResults["redScore"]) + "\n\n\n" + "Blue Score: " + str(matchResults["blueScore"]) + "\n" + "Blue Auto: " + str(matchResults["blue"]["auto"]) + "\n" + "Blue Tele: " + str(matchResults["blue"]["teleop"]) + "\n" + "Blue End: " + str(matchResults["blue"]["end"]) + "\n" + "Blue Penalty: " + str(matchResults["blue"]["penalty"]) + "\n\n" + "Red Score: " + str(matchResults["redScore"]) + "\n" + "Red Auto: " + str(matchResults["red"]["auto"]) + "\n" + "Red Tele: " + str(matchResults["red"]["teleop"]) + "\n" + "Red End: " + str(matchResults["red"]["end"]) + "\n" + "Red Penalty: " + str(matchResults["red"]["penalty"]) + """```""")
            
    #Post
    async def matchPost(self, json_data):     
        await self.sendMatchResult("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH POSTED" + """```""")
        await self.sendTTS(self.eventName + " has posted")
        
    async def matchAbort(self, json_data):     
        await self.sendMatchResult("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH ABORTED!!!" + """```""")
        await self.sendTTS("Warning " + self.eventName + " has aborted")
        #TODO: Fix reactions. This is broken because my custom functions do not return a CTX
        #await ctx.add_reaction('⚠')
        #await ctx.add_reaction('🚨')
    
    async def startWebSocket(self):
        self.logger.info("[" + self.name + "] " + "Starting Websocket")
        uri = FTCEVENTSERVER_WEBSOCKETURL + "/api/v2/stream/?code=" + self.eventCode
        self.logger.debug("[" + self.name + "] Atempting WebSocket connection to the following URL: " + uri)
        async with websockets.connect(uri) as websocket:
            self.logger.info("[" + self.name + "] " + "Monitoring Event: " + self.name)
            await self.sendAdmin("Monitoring Event: " + self.name)
            while True:
                try:
                    #Get the data from the websocket
                    response = await websocket.recv()
                 
                    #Parse the response into JSON
                    json_data = json.loads(response)
                    
                    #Extract the updateType from the response
                    updateType = json_data["updateType"]               
                    
                    #TODO: Add support for repeated server message handaling
                    
                    #Run cooresponding function based on the updateType supplied by the server
                    if updateType == "MATCH_LOAD":
                        self.lastState = "MATCH_LOAD"
                        await self.matchLoad(json_data)
                    elif updateType == "MATCH_START":
                        self.lastState = "MATCH_START"
                        await self.matchStart(json_data)
                    elif updateType == "MATCH_COMMIT":
                        self.lastState = "MATCH_COMMIT"
                        await self.matchCommit(json_data)
                    elif updateType == "MATCH_POST":
                        self.lastState = "MATCH_POST"
                        await self.matchPost(json_data)
                    elif updateType == "MATCH_ABORT":
                        self.lastState = "MATCH_ABORT"
                        await self.matchAbort(json_data)
                    else:
                        self.logger.error("[" + self.name + "] " + "Unknown Update Type provided by server")
                except asyncio.CancelledError:
                    await websocket.close()
                    raise
                
    async def stopWebSocket(self):
        self.logger.info("[" + self.name + "] " + "Stopped Monitoring Event: " + self.name)
        self.task.cancel()
        await self.sendAdmin("Stopped Monitoring Event: " + self.name)

    async def sendAdmin(self, message):
        for adminChannel in self.AllDiscordChannels:
            if adminChannel.channelType == 1:
                channel = self.bot.get_channel(adminChannel.id)
                await channel.send(message)

    async def sendMatchResult(self, message):
        for prodChannel in self.AllDiscordChannels:
            if prodChannel.channelType == 3:
                channel = self.bot.get_channel(prodChannel.id)
                await channel.send(message)
                
    async def sendTTS(self, message):
        if not self.bot.voice_clients == None:
            self.logger.debug("[sendTTS] " + "Trying to play sound file.")
            #Temp Commented out
            tts = gTTS(message, lang='en')
            tts.save('output.mp3')
            
            #TODO Write the data to a data blob and just read it from there
            #mp3_fp = BytesIO()
            #tts.write_to_fp(mp3_fp)
            
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('output.mp3', options="-loglevel panic"), volume=2.0)
            for vc in self.bot.voice_clients:
                vc.play(source, after=lambda e: self.logger.error('[sendTTS] Player error: %s' % e) if e else self.logger.info("[sendTTS] " + "Finished playing audio"))