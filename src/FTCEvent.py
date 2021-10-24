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

#TTS ENV Variables
BOTTTSENABLED = os.getenv('BOTTTSENABLED')

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
            response = requests.get(FTCEVENTSERVER + "/api/2022/v1/events/" + self.eventCode + "/matches/" + str(json_data["payload"]["number"]) + "/", headers=apiheaders)
            
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
                response = requests.get(FTCEVENTSERVER + "/api/2022/v1/events/" + self.eventCode + "/matches/" + str(json_data["payload"]["number"]) + "/", headers=apiheaders)
     
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
                self.logger.info("WAYPOINT 2")
                #KLT 24OCT21 1402ET - Updated for 2022
                SQLStatement = "UPDATE {table_name} SET `matchBrief_matchName`=%s, `matchBrief_matchNumber`=%s, `matchBrief_field`=%s, `matchBrief_red_team1`=%s, `matchBrief_red_team2`=%s, `matchBrief_red_isTeam1Surrogate`=%s, `matchBrief_red_isTeam2Surrogate`=%s, `matchBrief_blue_team1`=%s, `matchBrief_blue_team2`=%s, `matchBrief_blue_isTeam1Surrogate`=%s, `matchBrief_blue_isTeam2Surrogate`=%s, `matchBrief_finished`=%s, `matchBrief_matchState`=%s, `matchBrief_time`=FROM_UNIXTIME(%s), `startTime`=FROM_UNIXTIME(%s), `scheduledTime`=FROM_UNIXTIME(%s), `resultPostedTime`=FROM_UNIXTIME(%s), `redScore`=%s, `blueScore`=%s, `red_minorPenalties`=%s, `red_majorPenalties`=%s, `red_barcodeElement1`=%s, `red_barcodeElement2`=%s, `red_carousel`=%s, `red_autoNavigated1`=%s, `red_autoNavigated2`=%s, `red_autoBonus1`=%s, `red_autoBonus2`=%s, `red_autoStorageFreight`=%s, `red_autoFreight1`=%s, `red_autoFreight2`=%s, `red_autoFreight3`=%s, `red_driverControlledStorageFreight`=%s, `red_driverControlledFreight1`=%s, `red_driverControlledFreight2`=%s, `red_driverControlledFreight3`=%s, `red_sharedFreight`=%s, `red_endgameDelivered`=%s, `red_allianceBalanced`=%s, `red_sharedUnbalanced`=%s, `red_endgameParked1`=%s, `red_endgameParked2`=%s, `red_capped`=%s, `red_carouselPoints`=%s, `red_autoNavigationPoints`=%s, `red_autoFreightPoints`=%s, `red_autoBonusPoints`=%s, `red_driverControlledAllianceHubPoints`=%s, `red_driverControlledSharedHubPoints`=%s, `red_driverControlledStoragePoints`=%s, `red_endgameDeliveryPoints`=%s, `red_allianceBalancedPoints`=%s, `red_sharedUnbalancedPoints`=%s, `red_endgameParkingPoints`=%s, `red_cappingPoints`=%s, `red_totalPoints`=%s, `red_auto`=%s, `red_teleop`=%s, `red_end`=%s, `red_penalty`=%s, `red_dq1`=%s, `red_dq2`=%s, `blue_minorPenalties`=%s, `blue_majorPenalties`=%s, `blue_barcodeElement1`=%s, `blue_barcodeElement2`=%s, `blue_carousel`=%s, `blue_autoNavigated1`=%s, `blue_autoNavigated2`=%s, `blue_autoBonus1`=%s, `blue_autoBonus2`=%s, `blue_autoStorageFreight`=%s, `blue_autoFreight1`=%s, `blue_autoFreight2`=%s, `blue_autoFreight3`=%s, `blue_driverControlledStorageFreight`=%s, `blue_driverControlledFreight1`=%s, `blue_driverControlledFreight2`=%s, `blue_driverControlledFreight3`=%s, `blue_sharedFreight`=%s, `blue_endgameDelivered`=%s, `blue_allianceBalanced`=%s, `blue_sharedUnbalanced`=%s, `blue_endgameParked1`=%s, `blue_endgameParked2`=%s, `blue_capped`=%s, `blue_carouselPoints`=%s, `blue_autoNavigationPoints`=%s, `blue_autoFreightPoints`=%s, `blue_autoBonusPoints`=%s, `blue_driverControlledAllianceHubPoints`=%s, `blue_driverControlledSharedHubPoints`=%s, `blue_driverControlledStoragePoints`=%s, `blue_endgameDeliveryPoints`=%s, `blue_allianceBalancedPoints`=%s, `blue_sharedUnbalancedPoints`=%s, `blue_endgameParkingPoints`=%s, `blue_cappingPoints`=%s, `blue_totalPoints`=%s, `blue_auto`=%s, `blue_teleop`=%s, `blue_end`=%s, `blue_penalty`=%s, `blue_dq1`=%s, `blue_dq2`=%s, `randomization`=%s WHERE eventCode = %s AND matchBrief_matchNumber = %s;".format(table_name=mySQL_TABLE)
                
                #KLT 24OCT21 1410ET - Updated for 2022
                SQLData = (matchResults["matchBrief"]["matchName"], matchResults["matchBrief"]["matchNumber"], matchResults["matchBrief"]["field"], matchResults["matchBrief"]["red"]["team1"], matchResults["matchBrief"]["red"]["team2"], matchResults["matchBrief"]["red"]["isTeam1Surrogate"], matchResults["matchBrief"]["red"]["isTeam2Surrogate"], matchResults["matchBrief"]["blue"]["team1"], matchResults["matchBrief"]["blue"]["team2"], matchResults["matchBrief"]["blue"]["isTeam1Surrogate"], matchResults["matchBrief"]["blue"]["isTeam2Surrogate"], matchResults["matchBrief"]["finished"], matchResults["matchBrief"]["matchState"], max(1, (matchResults["matchBrief"]["time"])/1000), max(1, (matchResults["startTime"])/1000), max(1, (matchResults["scheduledTime"])/1000), max(1, (matchResults["resultPostedTime"])/1000), matchResults["redScore"], matchResults["blueScore"], matchResults["red"]["minorPenalties"], matchResults["red"]["majorPenalties"], matchResults["red"]["barcodeElement1"], matchResults["red"]["barcodeElement2"], matchResults["red"]["carousel"], matchResults["red"]["autoNavigated1"], matchResults["red"]["autoNavigated2"], matchResults["red"]["autoBonus1"], matchResults["red"]["autoBonus2"], matchResults["red"]["autoStorageFreight"], matchResults["red"]["autoFreight1"], matchResults["red"]["autoFreight2"], matchResults["red"]["autoFreight3"], matchResults["red"]["driverControlledStorageFreight"], matchResults["red"]["driverControlledFreight1"], matchResults["red"]["driverControlledFreight2"], matchResults["red"]["driverControlledFreight3"], matchResults["red"]["sharedFreight"], matchResults["red"]["endgameDelivered"], matchResults["red"]["allianceBalanced"], matchResults["red"]["sharedUnbalanced"], matchResults["red"]["endgameParked1"], matchResults["red"]["endgameParked2"], matchResults["red"]["capped"], matchResults["red"]["carouselPoints"], matchResults["red"]["autoNavigationPoints"], matchResults["red"]["autoFreightPoints"], matchResults["red"]["autoBonusPoints"], matchResults["red"]["driverControlledAllianceHubPoints"], matchResults["red"]["driverControlledSharedHubPoints"], matchResults["red"]["driverControlledStoragePoints"], matchResults["red"]["endgameDeliveryPoints"], matchResults["red"]["allianceBalancedPoints"], matchResults["red"]["sharedUnbalancedPoints"], matchResults["red"]["endgameParkingPoints"], matchResults["red"]["cappingPoints"], matchResults["red"]["totalPoints"], matchResults["red"]["auto"], matchResults["red"]["teleop"], matchResults["red"]["end"], matchResults["red"]["penalty"], matchResults["red"]["dq1"], matchResults["red"]["dq2"], matchResults["blue"]["minorPenalties"], matchResults["blue"]["majorPenalties"], matchResults["blue"]["barcodeElement1"], matchResults["blue"]["barcodeElement2"], matchResults["blue"]["carousel"], matchResults["blue"]["autoNavigated1"], matchResults["blue"]["autoNavigated2"], matchResults["blue"]["autoBonus1"], matchResults["blue"]["autoBonus2"], matchResults["blue"]["autoStorageFreight"], matchResults["blue"]["autoFreight1"], matchResults["blue"]["autoFreight2"], matchResults["blue"]["autoFreight3"], matchResults["blue"]["driverControlledStorageFreight"], matchResults["blue"]["driverControlledFreight1"], matchResults["blue"]["driverControlledFreight2"], matchResults["blue"]["driverControlledFreight3"], matchResults["blue"]["sharedFreight"], matchResults["blue"]["endgameDelivered"], matchResults["blue"]["allianceBalanced"], matchResults["blue"]["sharedUnbalanced"], matchResults["blue"]["endgameParked1"], matchResults["blue"]["endgameParked2"], matchResults["blue"]["capped"], matchResults["blue"]["carouselPoints"], matchResults["blue"]["autoNavigationPoints"], matchResults["blue"]["autoFreightPoints"], matchResults["blue"]["autoBonusPoints"], matchResults["blue"]["driverControlledAllianceHubPoints"], matchResults["blue"]["driverControlledSharedHubPoints"], matchResults["blue"]["driverControlledStoragePoints"], matchResults["blue"]["endgameDeliveryPoints"], matchResults["blue"]["allianceBalancedPoints"], matchResults["blue"]["sharedUnbalancedPoints"], matchResults["blue"]["endgameParkingPoints"], matchResults["blue"]["cappingPoints"], matchResults["blue"]["totalPoints"], matchResults["blue"]["auto"], matchResults["blue"]["teleop"], matchResults["blue"]["end"], matchResults["blue"]["penalty"], matchResults["blue"]["dq1"], matchResults["blue"]["dq2"], matchResults["randomization"], self.eventCode, matchResults["matchBrief"]["matchNumber"])
                
            else:
                #KLT 24OCT21 1405ET - Updated for 2022
                SQLStatement = "INSERT INTO {table_name} (`eventCode`, `matchBrief_matchName`, `matchBrief_matchNumber`, `matchBrief_field`, `matchBrief_red_team1`, `matchBrief_red_team2`, `matchBrief_red_isTeam1Surrogate`, `matchBrief_red_isTeam2Surrogate`, `matchBrief_blue_team1`, `matchBrief_blue_team2`, `matchBrief_blue_isTeam1Surrogate`, `matchBrief_blue_isTeam2Surrogate`, `matchBrief_finished`, `matchBrief_matchState`, `matchBrief_time`, `startTime`, `scheduledTime`, `resultPostedTime`, `redScore`, `blueScore`, `red_minorPenalties`, `red_majorPenalties`, `red_barcodeElement1`, `red_barcodeElement2`, `red_carousel`, `red_autoNavigated1`, `red_autoNavigated2`, `red_autoBonus1`, `red_autoBonus2`, `red_autoStorageFreight`, `red_autoFreight1`, `red_autoFreight2`, `red_autoFreight3`, `red_driverControlledStorageFreight`, `red_driverControlledFreight1`, `red_driverControlledFreight2`, `red_driverControlledFreight3`, `red_sharedFreight`, `red_endgameDelivered`, `red_allianceBalanced`, `red_sharedUnbalanced`, `red_endgameParked1`, `red_endgameParked2`, `red_capped`, `red_carouselPoints`, `red_autoNavigationPoints`, `red_autoFreightPoints`, `red_autoBonusPoints`, `red_driverControlledAllianceHubPoints`, `red_driverControlledSharedHubPoints`, `red_driverControlledStoragePoints`, `red_endgameDeliveryPoints`, `red_allianceBalancedPoints`, `red_sharedUnbalancedPoints`, `red_endgameParkingPoints`, `red_cappingPoints`, `red_totalPoints`, `red_auto`, `red_teleop`, `red_end`, `red_penalty`, `red_dq1`, `red_dq2`, `blue_minorPenalties`, `blue_majorPenalties`, `blue_barcodeElement1`, `blue_barcodeElement2`, `blue_carousel`, `blue_autoNavigated1`, `blue_autoNavigated2`, `blue_autoBonus1`, `blue_autoBonus2`, `blue_autoStorageFreight`, `blue_autoFreight1`, `blue_autoFreight2`, `blue_autoFreight3`, `blue_driverControlledStorageFreight`, `blue_driverControlledFreight1`, `blue_driverControlledFreight2`, `blue_driverControlledFreight3`, `blue_sharedFreight`, `blue_endgameDelivered`, `blue_allianceBalanced`, `blue_sharedUnbalanced`, `blue_endgameParked1`, `blue_endgameParked2`, `blue_capped`, `blue_carouselPoints`, `blue_autoNavigationPoints`, `blue_autoFreightPoints`, `blue_autoBonusPoints`, `blue_driverControlledAllianceHubPoints`, `blue_driverControlledSharedHubPoints`, `blue_driverControlledStoragePoints`, `blue_endgameDeliveryPoints`, `blue_allianceBalancedPoints`, `blue_sharedUnbalancedPoints`, `blue_endgameParkingPoints`, `blue_cappingPoints`, `blue_totalPoints`, `blue_auto`, `blue_teleop`, `blue_end`, `blue_penalty`, `blue_dq1`, `blue_dq2`, `randomization`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);".format(table_name=mySQL_TABLE)
                
                #KLT 24OCT21 1413ET - Updated for 2022
                SQLData = (self.eventCode, matchResults["matchBrief"]["matchName"], matchResults["matchBrief"]["matchNumber"], matchResults["matchBrief"]["field"], matchResults["matchBrief"]["red"]["team1"], matchResults["matchBrief"]["red"]["team2"], matchResults["matchBrief"]["red"]["isTeam1Surrogate"], matchResults["matchBrief"]["red"]["isTeam2Surrogate"], matchResults["matchBrief"]["blue"]["team1"], matchResults["matchBrief"]["blue"]["team2"], matchResults["matchBrief"]["blue"]["isTeam1Surrogate"], matchResults["matchBrief"]["blue"]["isTeam2Surrogate"], matchResults["matchBrief"]["finished"], matchResults["matchBrief"]["matchState"], max(1, (matchResults["matchBrief"]["time"]/1000)), max(1, (matchResults["startTime"]/1000)), max(1, (matchResults["scheduledTime"]/1000)), max(1, (matchResults["resultPostedTime"]/1000)), matchResults["redScore"], matchResults["blueScore"], matchResults["red"]["minorPenalties"], matchResults["red"]["majorPenalties"], matchResults["red"]["barcodeElement1"], matchResults["red"]["barcodeElement2"], matchResults["red"]["carousel"], matchResults["red"]["autoNavigated1"], matchResults["red"]["autoNavigated2"], matchResults["red"]["autoBonus1"], matchResults["red"]["autoBonus2"], matchResults["red"]["autoStorageFreight"], matchResults["red"]["autoFreight1"], matchResults["red"]["autoFreight2"], matchResults["red"]["autoFreight3"], matchResults["red"]["driverControlledStorageFreight"], matchResults["red"]["driverControlledFreight1"], matchResults["red"]["driverControlledFreight2"], matchResults["red"]["driverControlledFreight3"], matchResults["red"]["sharedFreight"], matchResults["red"]["endgameDelivered"], matchResults["red"]["allianceBalanced"], matchResults["red"]["sharedUnbalanced"], matchResults["red"]["endgameParked1"], matchResults["red"]["endgameParked2"], matchResults["red"]["capped"], matchResults["red"]["carouselPoints"], matchResults["red"]["autoNavigationPoints"], matchResults["red"]["autoFreightPoints"], matchResults["red"]["autoBonusPoints"], matchResults["red"]["driverControlledAllianceHubPoints"], matchResults["red"]["driverControlledSharedHubPoints"], matchResults["red"]["driverControlledStoragePoints"], matchResults["red"]["endgameDeliveryPoints"], matchResults["red"]["allianceBalancedPoints"], matchResults["red"]["sharedUnbalancedPoints"], matchResults["red"]["endgameParkingPoints"], matchResults["red"]["cappingPoints"], matchResults["red"]["totalPoints"], matchResults["red"]["auto"], matchResults["red"]["teleop"], matchResults["red"]["end"], matchResults["red"]["penalty"], matchResults["red"]["dq1"], matchResults["red"]["dq2"], matchResults["blue"]["minorPenalties"], matchResults["blue"]["majorPenalties"], matchResults["blue"]["barcodeElement1"], matchResults["blue"]["barcodeElement2"], matchResults["blue"]["carousel"], matchResults["blue"]["autoNavigated1"], matchResults["blue"]["autoNavigated2"], matchResults["blue"]["autoBonus1"], matchResults["blue"]["autoBonus2"], matchResults["blue"]["autoStorageFreight"], matchResults["blue"]["autoFreight1"], matchResults["blue"]["autoFreight2"], matchResults["blue"]["autoFreight3"], matchResults["blue"]["driverControlledStorageFreight"], matchResults["blue"]["driverControlledFreight1"], matchResults["blue"]["driverControlledFreight2"], matchResults["blue"]["driverControlledFreight3"], matchResults["blue"]["sharedFreight"], matchResults["blue"]["endgameDelivered"], matchResults["blue"]["allianceBalanced"], matchResults["blue"]["sharedUnbalanced"], matchResults["blue"]["endgameParked1"], matchResults["blue"]["endgameParked2"], matchResults["blue"]["capped"], matchResults["blue"]["carouselPoints"], matchResults["blue"]["autoNavigationPoints"], matchResults["blue"]["autoFreightPoints"], matchResults["blue"]["autoBonusPoints"], matchResults["blue"]["driverControlledAllianceHubPoints"], matchResults["blue"]["driverControlledSharedHubPoints"], matchResults["blue"]["driverControlledStoragePoints"], matchResults["blue"]["endgameDeliveryPoints"], matchResults["blue"]["allianceBalancedPoints"], matchResults["blue"]["sharedUnbalancedPoints"], matchResults["blue"]["endgameParkingPoints"], matchResults["blue"]["cappingPoints"], matchResults["blue"]["totalPoints"], matchResults["blue"]["auto"], matchResults["blue"]["teleop"], matchResults["blue"]["end"], matchResults["blue"]["penalty"], matchResults["blue"]["dq1"], matchResults["blue"]["dq2"], matchResults["randomization"])

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
        if BOTTTSENABLED == True:
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