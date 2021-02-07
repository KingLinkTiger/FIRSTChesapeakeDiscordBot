import os
from datetime import datetime, timedelta
import requests
import requests_cache
import json
import asyncio
import websockets
import logging

from discord.ext import commands

class DiscordChannel:
    logger = logging.getLogger('FIRSTChesapeakeBot')
    AllDiscordChannels = []

    def __init__(self, bot, ALLCHANNELS, CHANNELNAME, channelType): 
        self.name = CHANNELNAME
        self.allchannels = ALLCHANNELS
        self.bot = bot
        self.id = None
        self.channelType = channelType
        
        self.getChannelID()
        
        DiscordChannel.AllDiscordChannels.append(self)
        
        self.logger.info("[" + self.name + "] " + "Creating Discord Channel Instance")
        
    def getChannelID(self):   
        for channel in self.allchannels: 
            if channel.name.lower() == self.name.lower() and str(channel.type) == "text":
                self.id = channel.id
                self.logger.info("[" + self.name + "] " + "Channel ID Found: "  + str(channel.id))
        
        if self.id == None:
            self.logger.error("[" + self.name + "] " + "Unable to locate channel ID")