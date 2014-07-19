"""
This interface parses log data from the game server, and calls the appropriate
server and pug methods. Note that if you wish, you could implement stat parsing
in this class, and pass the database interface in for db interactions
"""

class InvalidServerOrPugException(Exception):
    pass

### This should all possibly be done on the pug directly... ? ###
class BaseLogInterface(object):
    def __init__(self, server, pug):
        if server is None or pug is None:
            raise InvalidServerOrPugException("Server or pug is None in log interface")

        self.server = server
        self.pug = pug

    def parse(self, data):
        raise NotImplementedError("Must implement this method")

    def start_game(self, start_time = 20):
        self.server.start_game(start_time)

    def restart_game(self):
        # just start the game again?
        self.start_game()

    def end_game(self):
        self.pug.end_game()

        self.server.reset()

    def update_score(self, team, score):
        self.pug.update_score(team, score)

    def print_teams(self):
        self.server.print_teams()

    def kick_player(self, sid, reason):
        self.server.kick_player(sid, reason)
