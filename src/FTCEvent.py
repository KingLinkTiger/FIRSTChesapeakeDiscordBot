import os
from datetime import datetime, timedelta
import requests
import requests_cache
import json
import asyncio
import websockets
import logging

from discord.ext import commands
from dotenv import load_dotenv

from FTCTeam import FTCTeam

load_dotenv()

FTCEVENTSERVER = os.getenv('FTCEVENTSERVER')
FTCEVENTSERVER_WEBSOCKETURL = os.getenv('FTCEVENTSERVER_WEBSOCKETURL')
BOTPRODUCTIONCHANNEL = os.getenv('BOTPRODUCTIONCHANNEL')
FTCEVENTSERVER_APIKey = os.getenv('FTCEVENTSERVER_APIKey')

class FTCEvent:
    logger = logging.getLogger('FIRSTChesapeakeBot')

    def __init__(self, eventData, bot, BOTPRODUCTIONCHANNEL_ID, BOTADMINCHANNEL_ID): 
        self.eventCode = eventData["eventCode"]
        self.name = eventData["name"]
        self.bot = bot
        self.BOTPRODUCTIONCHANNEL_ID = BOTPRODUCTIONCHANNEL_ID
        self.BOTADMINCHANNEL_ID = BOTADMINCHANNEL_ID
        
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
            channel = self.bot.get_channel(self.BOTPRODUCTIONCHANNEL_ID)
            await channel.send("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "--------------------------------------------------" + "\n" + "Red 1: " + str(red1) + " - " + self.teams[red1].name + "\n" + "Red 2: " + str(red2) + " - " + self.teams[red2].name  + "\n" + "Blue 1: " + str(blue1) + " - " + self.teams[blue1].name  + "\n" + "Blue 2: " + str(blue2) + " - " + self.teams[blue2].name  + """```""")     
            
    async def matchStart(self, json_data):     
        channel = self.bot.get_channel(self.BOTPRODUCTIONCHANNEL_ID)
        await channel.send("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH STARTED" + """```""") 
        
    async def matchCommit(self, json_data):         
        if json_data["payload"]["shortName"][0] == 'Q':
            apiheaders = {'Content-Type':'application/json', 'Authorization':FTCEVENTSERVER_APIKey}

            #Clear the cache for this URL in order to get fresh data every time
            with requests_cache.disabled():
                response = requests.get(FTCEVENTSERVER + "/api/2021/v1/events/" + self.eventCode + "/matches/" + str(json_data["payload"]["number"]) + "/", headers=apiheaders)
     
            matchResults = json.loads(response.text)
        
            channel = self.bot.get_channel(self.BOTPRODUCTIONCHANNEL_ID)
            await channel.send("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "--------------------MATCH RESULTS------------------------------" + "\n" + "Blue Score: " + str(matchResults["blueScore"]) + "\n" + "Blue Auto: " + str(matchResults["blue"]["auto"]) + "\n" + "Blue Tele: " + str(matchResults["blue"]["teleop"]) + "\n" + "Blue End: " + str(matchResults["blue"]["end"]) + "\n" + "Blue Penalty: " + str(matchResults["blue"]["penalty"]) + "\n\n" + "Red Score: " + str(matchResults["redScore"]) + "\n" + "Red Auto: " + str(matchResults["red"]["auto"]) + "\n" + "Red Tele: " + str(matchResults["red"]["teleop"]) + "\n" + "Red End: " + str(matchResults["red"]["end"]) + "\n" + "Red Penalty: " + str(matchResults["red"]["penalty"]) + """```""")
        
    #Post
    async def matchPost(self, json_data):     
        channel = self.bot.get_channel(self.BOTPRODUCTIONCHANNEL_ID)
        ctx = await channel.send("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH POSTED" + """```""")
        
    async def matchAbort(self, json_data):     
        channel = self.bot.get_channel(self.BOTPRODUCTIONCHANNEL_ID)
        ctx = await channel.send("""```""" + "Event: " + self.name + "\n" + "Match Number: " + json_data["payload"]["shortName"] + "\n" + "Status: MATCH ABORTED!!!" + """```""")
        await ctx.add_reaction('⚠')
        await ctx.add_reaction('🚨')
    
    async def deleteLastMessage(self):
        channel = self.bot.get_channel(self.BOTPRODUCTIONCHANNEL_ID)
        lastMessage = channel.history("bot-testing", limit=1)
        channel.delete_messages(lastMessage)
        
    async def startWebSocket(self):
        self.logger.info("[" + self.name + "] " + "Starting Websocket")
        uri = FTCEVENTSERVER_WEBSOCKETURL + "/api/v2/stream/?code=" + self.name
        async with websockets.connect(uri) as websocket:
            channel = self.bot.get_channel(self.BOTADMINCHANNEL_ID)
            self.logger.info("[" + self.name + "] " + "Monitoring Event: " + self.name)
            await channel.send("Monitoring Event: " + self.name)
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
        channel = self.bot.get_channel(self.BOTADMINCHANNEL_ID)
        await channel.send("Stopped Monitoring Event: " + self.name)   