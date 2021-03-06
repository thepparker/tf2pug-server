"""
tflogging.py

TF2 Logging Interface
"""


import logging
import re

import settings

from .BaseInterfaces import BaseLogInterface
from .pesapi import PESAPIInterface

USING_UNITY = settings.use_pes_unity
pes_api_interface = None
if USING_UNITY:
    pes_api_interface = PESAPIInterface(settings.pes_api_base_url,
                                        settings.pes_api_userid,
                                        settings.pes_api_privatekey)

round_win = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Win" \x28winner "(Blue|Red)"\x29$')
round_overtime = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Overtime"$')
round_length = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Length" \x28seconds "(\d+)\.(\d+)"\x29$')
round_start = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Start"$')
round_setup_start = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Setup_Begin"$')
round_setup_end = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Setup_End"$')

player_connect = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" connected, address "(.*?):(.*?)"$')
player_disconnect = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(.*?)>" disconnected \x28reason "(.*?)"\x29$')
player_validated = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" STEAM USERID validated$')

team_score = re.compile(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" current score "(\d+)" with "(\d+)" players$')
final_team_score = re.compile(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" final score "(\d+)" with "(\d+)" players$')

game_over = re.compile(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Game_Over" reason "(.*?)"$')

chat_message = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue|Spectator|Console)>" (say|say_team) "(.*)"$')

player_kill = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" killed "(.*?)<(\d+)><(.*?)><(Red|Blue)>" with "(.*?)" \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')
player_kill_special = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" killed "(.*?)<(\d+)><(.*?)><(Red|Blue)>" with "(.*?)" \x28customkill "(.*?)"\x29 \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')
player_assist = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "kill assist" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28assister_position "(.*?)"\x29 \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')

unity_report = re.compile(r'^L [0-9\/]+ - [0-9\:]+: "{"token":"REPORT","data":{"reported":"(.*)","reporter":"(.*)","reason":"(.*)","matchId":(\d+)}}"')

regex = {
    "round": (round_win, round_overtime, round_length, round_start, 
         round_setup_start, round_setup_end),
    "player_connection": (player_disconnect, player_connect, 
            player_validated),
    "team_score": (team_score, final_team_score),
    "game_event": (game_over,),
    "chat": (chat_message,),
    "player_stat": (player_kill, player_kill_special, player_assist),
    "report": (unity_report,),
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

    if steam_id == "BOT" or steam_id == "0":
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
            account_id += auth_server #add the auth server

    elif "[U:1:" in steam_id:
        # steamid is [U:1:####]. All we need to do is get the #### out and add
        # the 64bit 76561197960265728
        account_id = re.sub(r'(\[U:1:)|(\])', "", steam_id)
        if bool(account_id):
            account_id = int(account_id)
    else:
        raise ValueError("Invalid SteamID: '%s'" % steam_id)    

    if not bool(account_id):
        raise ValueError("Invalid SteamID: '%s' gives AccountID '%d'" % (
                         steam_id, account_id))

    # Have non-zero account id. Add the community ID modifier
    community_id = account_id + cm_modifier #add arbitrary number chosen by valve

    return community_id

class TFLogInterface(BaseLogInterface):
    def __init__(self, server):
        BaseLogInterface.__init__(self, server)

        self._using_secret = False
        self._secret = None

        self._dispatch = {
            "player_connection": self._parse_player_connection,
            "round": self._parse_round,
            "team_score": self._parse_team_score,
            "game_event": self._parse_game_event,
            "chat": self._parse_chat,
            "player_stat": self._parse_stat,
            "report": self._parse_report
        }

        # for pausing stat recording when game is not actually in progress
        self.ROUND_PAUSE = True

    def _verify_data(self, data):
        # check if we're using a secret
        if self._using_secret or data[0] == "S":
            self._using_secret = True
            secret = data[1:data.find(" ")-1]
            
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

        if self._verify_data(mod_data):
            # mod_data is now in the form RL ..., or S<>L ..., we want it to
            # just be L ...
            # could also use mod_data.split(" ", 1)[1]
            mod_data = "L" + mod_data[mod_data.find(" "):]
            try:
                self._dispatch_parse(mod_data)

            except:
                logging.exception("Exception parsing data: '%s'", data)

    def _dispatch_parse(self, data):
        # actually parse the log data!
        # match_found is None if no match, else a tuple in the form 
        # (regex group type, match, expr)
        match_found = check_regex_match(data)
        if match_found is None:
            logging.debug("No regex match for: %s", data)
            return

        group, match, expr = match_found

        # some data matched! now, let's dispatch it to the appropriate method
        # based on the group

        if group not in self._dispatch:
            raise NotImplementedError("Dispatch method is not implemented for %s" % group)

        method = self._dispatch[group]

        #logging.debug("Data matches group \"%s\". Method: \"%s\"", group, 
        #              method)

        method(match, expr)

    def _parse_round(self, match, expr):
        if expr is round_win:
            # Stop tracking stats after round_win
            self.ROUND_PAUSE = True

        elif expr is round_start:
            # if first round_start event and the pug hasn't technically
            # started, let's start it!
            if not self.pug.game_started:
                if self.pug.replacement_required:
                    self.server.rcon(
                        "say Cannot start the game while waiting for a "
                        "replacement; mp_tournament_restart")
                
                else:
                    self.start_game()
                    # start tracking stats
                    self.ROUND_PAUSE = False
                    self.server.rcon("say !!! The game is now live !!!")

            else:
                self.ROUND_PAUSE = False

    def _parse_player_connection(self, match, expr):
        if expr is player_connect:
            # check if the player id is in the pug player list. if not, kick
            # them
            name = re_group(match, 1)
            sid = re_group(match, 3)
            cid = steamid_to_64bit(sid)

            if not self.pug.has_player(cid):
                # this player is not in the pug, so we need to kick this fucka
                self.kick_player(sid, "Not in pug player list")

            ip = re_group(match, 4)
            # TODO: Log this connection

            self.pug.remove_disconnect(cid)

        elif expr is player_validated:
            pass

        elif expr is player_disconnect:
            name = re_group(match, 1)
            sid = re_group(match, 3)
            cid = steamid_to_64bit(sid)

            reason = re_group(match, 5)

            self.pug.add_disconnect(cid, reason)

    def _parse_team_score(self, match, expr):
        if expr is team_score:
            team = re_group(match, 1).lower()
            score = int(re_group(match, 2))

            self.update_score(team, score)

        elif expr is final_team_score:
            # final update, make sure scores are correct
            team = re_group(match, 1).lower()
            score = int(re_group(match, 2))

            self.update_score(team, score)

    def _parse_game_event(self, match, expr):
        if expr is game_over:
            # game is over!
            self.end_game()

    def _parse_chat(self, match, expr):
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

    def _parse_stat(self, match, expr):
        if not self.pug.game_started or self.ROUND_PAUSE:
            return

        if expr is player_kill or expr is player_kill_special:
            attacker_cid = steamid_to_64bit(re_group(match, 3))
            victim_cid = steamid_to_64bit(re_group(match, 7))

            self.pug.update_game_stat(attacker_cid, "kills", 1)
            self.pug.update_game_stat(victim_cid, "deaths", 1)

        elif expr is player_assist:
            assister_cid = steamid_to_64bit(re_group(match, 3))

            self.pug.update_game_stat(assister_cid, "assists", 1)

    def _parse_report(self, match, expr):
        # We utilise the Unity API to store this report. Therefore, if not
        # using unity, just skip this. Note that this begs the question of:
        # if we're not using unity, why the fuck are we getting a report?
        if not USING_UNITY:
            return

        if expr is unity_report:
            reporter = steamid_to_64bit(re_group(match, 2))
            reported = steamid_to_64bit(re_group(match, 1))

            reason = re_group(match, 3)

            match_id = re_group(match, 4)

            logging.debug("Report details - REPORTER: %s, REPORTED: %s, "
                          "REASON: '%s', MATCHID: %s", 
                          reporter, reported, reason, match_id)

            pes_api_interface.create_report(reported, reporter, reason, 
                                            match_id)
            

