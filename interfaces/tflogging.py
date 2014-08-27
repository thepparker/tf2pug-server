"""
tflogging.py

TF2 Logging Interface
"""


import logging
import re

from BaseInterfaces import BaseLogInterface

round_win = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Win" \x28winner "(Blue|Red)"\x29$')
round_overtime = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Overtime"$')
round_length = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_length" \x28seconds "(\d+)\.(\d+)"\x29$')
round_start = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Start"$')
round_setup_start = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Setup_Begin$"')
round_setup_end = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Setup_End"$')

player_connect = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" connected, address "(.*?):(.*?)"$')
player_disconnect = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(.*?)>" disconnected \x28reason "(.*?)"\x29$')
player_validated = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" STEAM USERID validated$')

team_score = re.compile(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" current score "(\d+)" with "(\d+)" players$')
final_team_score = re.compile(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" final score "(\d+)" with "(\d+)" players$')
game_over = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Game_Over" reason "(.*?)"$')

chat_message = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue|Spectator|Console)>" (say|say_team) "(.+)"$')

regex = {
    "round": (round_win, round_overtime, round_length, round_start, 
         round_setup_start, round_setup_end),
    "player_connection": (player_disconnect, player_connect, 
            player_validated),
    "team_score": (team_score, final_team_score, game_over),
    "chat": (chat_message,)
}

def check_regex_match(data):
    for group in regex:
        for expr in regex[group]:
            match = expr.match(data)
            if match:
                return (group, match, expr) # return at the first regex match

    return None

def re_group(match, group):
    return match.group(group)

def steamid_to_64bit(steam_id):
    # takes a steamid in the format STEAM_x:x:xxxxx or [U:1:xxxx] and converts
    # it to a 64bit community id

    if steam_id == "BOT":
        return steam_id

    cm_modifier = 76561197960265728
    account_id = 0

    # support oldage STEAM_0:A:B user SteamIDs (TF2 now uses [U:1:2*B+A])
    if "STEAM_" in steam_id:
        auth_server = 0
        auth_id = 0
        
        steam_id_tok = steam_id.split(':')

        if len(steam_id_tok) == 3:
            auth_server = int(steam_id_tok[1])
            auth_id = int(steam_id_tok[2])
            
            account_id = auth_id * 2 #multiply auth id by 2
            account_id += auth_server #add the auth server. even ids are on server 0, odds on server 1

    else:
        # steamid is [U:1:####]. All we need to do is get the #### out and add
        # the 64bit 76561197960265728
        account_id = re.sub(r'(\[U:1:)|(\])', "", steam_id)
        if bool(account_id):
            account_id = int(account_id)
        
    if not bool(account_id):
        raise ValueError("Invalid SteamID: '%s' gives AccountID '%d'" % (steam_id, account_id))

    # Have non-zero account id. Add the community ID modifier
    community_id = account_id + cm_modifier #add arbitrary number chosen by valve

    return community_id

class TFLogInterface(BaseLogInterface):
    def __init__(self, server):
        BaseLogInterface.__init__(self, server)

        self._using_secret = False
        self._secret = None

        self._dispatch = {
            "player_connection": self.__parse_player_connection,
            "round": self.__parse_round,
            "team_score": self.__parse_team_score,
            "chat": self.__parse_chat
        }

    def __verify_data(self, data):
        # check if we're using a secret
        if self._using_secret or data[0] == "S":
            self._using_secret = True
            secret = mod_data[1:mod_data.find(" ")-1]
            
            if self._secret is None:
                self._secret = secret

            if secret == self._secret:
                return True
            else:
                return False

        elif not self._using_secret and data[0] == "R":
            return True

        else:
            return False

    def parse(self, data):
        # log data in the format \xFF\xFF\xFF\xFFRL dd/mm/yyyy - HH:mm:ss:
        # OR \xFF\xFF\xFF\xFFS<secret>L dd/mm/yyyy - HH:mm:ss:
        # the second version is sent when the server has sv_logsecret
        # set
        logging.debug("Received data: %s", data)

        # We're going to strip the headers and pass just the log data to _parse
        # Sometimes logs can have a trailing null byte (last byte is 0), which
        # we will need to remove if present.
        mod_data = data
        if mod_data[-1] == "\0":
            mod_data = mod_data[:-1]

        # Null byte is stripped. Now we just remove leading \xFF and trailing \n
        mod_data = mod_data.lstrip("\xFF").rstrip()

        if self.__verify_data(mod_data):
            # mod_data is now in the form RL ..., or S<>L ..., we want it to
            # just be L ...
            # could also use mod_data.split(" ", 1)[1]
            mod_data = "L" + mod_data[mod_data.find(" "):]
            self._dispatch_parse(mod_data)

    def _dispatch_parse(self, data):
        # actually parse the log data!
        # match_found is None if no match, else a tuple in the form 
        # (regex group type, match, expr)
        match_found = check_regex_match(data)
        if match_found is None:
            logging.debug("No regex match for: %s", data)

        group, match, expr = match_found

        # some data matched! now, let's dispatch it to the appropriate method
        # based on the group

        if group not in self._dispatch:
            raise NotImplementedError("Dispatch method is not implemented for %s" % group)

        method = self._dispatch[group]
        method(match, expr)

    def __parse_round(self, match, expr):
        if expr is round_win:
            # do what?
            pass
        elif expr is round_start:
            # if first round_start event and the pug hasn't technically
            # started, let's start it!
            if not self.pug.game_started:
                self.start_game()

        pass

    def __parse_player_connection(self, match, expr):
        if expr is player_connect:
            # check if the player id is in the pug player list. if not, kick
            # them (if we're not looking for a replacement...?)
            name = re_group(match, 1)
            sid = re_group(match, 3)
            cid = steamid_to_64bit(sid)

            if not self.pug.has_player(cid):
                # this player is not in the pug, so we need to kick this fucka
                self.kick_player(sid, "Not in pug player list")

        elif expr is player_validated:
            pass

        elif expr is player_disconnect:
            pass

    def __parse_team_score(self, match, expr):
        if expr is team_score:
            team = re_group(match, 1).lower()
            score = re_group(match, 2)

            self.update_score(team, score)

        elif expr is final_team_score:
            # final update, make sure scores are correct
            team = re_group(match, 1).lower()
            score = re_group(match, 2)

            self.update_score(team, score)

        elif expr is game_over:
            # game is over!
            self.end_game()

    def __parse_chat(self, match, expr):
        # this is the fun part............................................
        if expr is chat_message:
            sid = re_group(match, 3)

            if sid == "Console":
                return

            cid = steamid_to_64bit(sid)
            name = re_group(match, 1)

            msg = re_group(match, 6)
            msg_tok = msg.split(" ")
            cmd = msg_tok[0].lower()

            isadmin = self.pug.is_admin(cid)

            if cmd == "!teams":
                self.print_teams()

            elif cmd == "!start" and isadmin:
                self.start_game()

            elif cmd == "":
                pass
