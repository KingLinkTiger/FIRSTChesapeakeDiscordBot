import logging

class FTCTeam:
    def __init__(self, teamData):
        self.number = teamData["number"]
        #TODO: Support emojis in team name
        self.name = teamData["name"]
        self.school = teamData["school"]
        self.city = teamData["city"]
        self.state = teamData["state"]
        self.country = teamData["country"]
        self.rookie = teamData["rookie"]
        
        self.logger = logging.getLogger('FIRSTChesapeakeBot')
        self.logger.info("[" + str(self.number) + "] " + "Creating Team Instance")