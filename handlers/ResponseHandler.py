# The ResponseHandler handles all responses to API calls. Response codes
# are the code sent along with packets to indicate what the packet is for.

from collections import OrderedDict

Response_None = 0 # for when shit goes completely wrong
Response_PugListing = 1000
Response_PugStatus = 1001
Response_InvalidPug = 1002
Response_PugCreated = 1003
Response_PugEnded = 1004
Response_PugFull = 1005
Response_EmptyPugEnded = 1006

Response_PlayerList = 1100
Response_PlayerInPug = 1101
Response_PlayerNotInPug = 1102
Response_PlayerAdded = 1103
Response_PlayerRemoved = 1104
Response_PlayerBanned = 1105
Response_PlayerRestricted = 1106

Response_MapVoteAdded = 1200
Response_MapForced = 1201
Response_MapNotForced = 1202
Response_MapVoteNotInProgress = 1203
Response_InvalidMap = 1204

Response_NoAvailableServers = 1300
Response_ServerConnectionError = 1301

Response_BanAdded = 1400
Response_InvalidBanData = 1401
Response_BanRemoved = 1402
Response_NoBanFound = 1403
Response_BanList = 1404

Response_PlayerStats = 1500
Response_TopPlayerStats = 1501

class ResponseHandler(object):
    def __init__(self):
        pass

    def change_response_code(self, packet, new_code):
        packet["response"] = new_code

        return packet

    def ban_list(self, bans):
        """
        Parse a list of ban results (dicts) from db.get_bans() into the
        documented format.
        """
        response = { "response": Response_BanList }
        response["bans"] = [ self._ban_packet(x) for x in bans ]

        return response

    def ban_added(self, ban):
        """
        Note that tbe "ban" passed to this method is a bans.Ban object, which
        is different to the ban objects passed to ban_list (psycopg2.DictRow)
        """
        return {
            "response": Response_BanAdded,
            "ban": self._ban_packet(ban)
        }

    def _ban_packet(self, ban):
        """
        ban is a dict in the format:
        {
            "banned_cid": cid,
            "banned_name": name,
            "banner_cid": cid,
            "banner_name": name,
            "ban_start_time": epoch ban start time,
            "ban_duration": ban duration in seconds,
            "reason": ban reason,
            "expired": true/false
        }
        """
        return dict(ban)

    def invalid_ban_data(self):
        return { "response": Response_InvalidBanData }

    def ban_removed(self):
        return { "response": Response_BanRemoved }

    def no_ban_found(self):
        return { "response": Response_NoBanFound }

    def no_available_servers(self):
        return { "response": Response_NoAvailableServers }

    def server_connection_error(self):
        return { "response": Response_ServerConnectionError }

    def pug_vote_added(self, player_id, pug):
        response = self.pug_status(pug)
        response["voter_id"] = player_id

        self.change_response_code(response, Response_MapVoteAdded)

        return response

    def invalid_map(self):
        return { "response": Response_InvalidMap }

    def player_added(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PlayerAdded)

        return response

    def player_removed(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PlayerRemoved)

        return response

    def player_banned(self, reason):
        return { 
                "response": Response_PlayerBanned,
                "ban": {
                    "reason": reason
                }
            }

    def player_restricted(self):
        return { "response": Response_PlayerRestricted }

    def player_in_pug(self):
        return { "response": Response_PlayerInPug }

    def player_not_in_pug(self):
        return { "response": Response_PlayerNotInPug }

    def pug_full(self):
        return { "response": Response_PugFull }

    def invalid_pug(self):
        return { "response": Response_InvalidPug }

    def empty_pug_ended(self):
        return { "response": Response_EmptyPugEnded }

    def pug_created(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PugCreated)

        return response

    def pug_ended(self, pug_id):
        response = {
            "response": Response_PugEnded,
            "id": pug_id
        }

        return response

    def player_list(self, pug):
        response = {}

        if pug is None:
            response["response"] = Response_InvalidPug
        else:
            response = {
                "response": Response_PlayerList,
                "players": self._pug_players_list(pug)
            }

        return response

    def pug_listing(self, pugs):
        response = {
            "response": Response_PugListing,
            "pugs": [ self._pug_status_packet(pug) for pug in pugs ]
        }

        return response

    def pug_map_forced(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_MapForced)

        return response

    def pug_map_not_forced(self):
        return { "response": Response_MapNotForced }

    def pug_no_map_vote(self):
        return { "response": Response_MapVoteNotInProgress }

    def player_stats(self, stats):
        """
        Stats is a list of stat dicts with requested CIDs as the keys
        """
        return {
            "response": Response_PlayerStats,
            "stats": stats
        }

    def top_player_stats(self, sort_key, stats):
        """
        Stats is a list of stat dicts with CID as the key. We should sort
        the dict based on the given key
        """

        # Sorted gives us a list of tuples (i.e sorted stats.items()), sorted
        # in order of the sort key. We then convert this back to a dict using
        # an OrderedDict so the new sort order is maintained.
        sorted_stats = OrderedDict(sorted(stats.iteritems(), 
                                          key = lambda x: x[1][sort_key],
                                          reverse = True
                                        )
                                )

        return {
            "response": Response_TopPlayerStats,
            "stats": sorted_stats
        }

    def pug_status(self, pug):
        response = {}

        if pug is None:
            response["response"] = Response_InvalidPug

        else:
            response["response"] = Response_PugStatus

            response["pug"] = self._pug_status_packet(pug)

        return response

    def _pug_status_packet(self, pug):
        packet = pug.__dict__.copy()

        if pug.server is not None:
            packet["server"] = {
                "id": pug.server.id,
                "anticheat": pug.server.anticheat,
                "ip": pug.server.ip,
                "port": pug.server.port,
                "tv": pug.server.tv_port,
                "password": pug.server.password
            }

        else:
            del packet["server"]

        del packet["_players"]

        # only stats we send are the game stats
        del packet["end_stats"]

        packet["named_state"] = pug.get_state_string()
        packet["players"] = self._pug_players_list(pug)
        packet["map_vote_counts"] = self._pug_vote_count_list(pug)
        packet["player_votes"] = self._pug_vote_list(pug)

        
        # make a copy of the pug teams object so we don't modify it
        packet["teams"] = {}

        # convert sets to list so they can be json serialized
        for team in pug.teams:
            packet["teams"][team] = list(pug.teams[team])

        return packet

    def _pug_players_list(self, pug):
        player_list = []

        for player_id in pug._players:
            player = dict({
                    "id": player_id,
                    "name": pug._players[player_id]
                })

            # if we have the player's stats, merge them into the field for this
            # player
            if player_id in pug.player_stats:
                player = dict(player.items() + pug.player_stats[player_id].items())

            player_list.append(player)

        return player_list

    def _pug_vote_list(self, pug):
        vote_list = []

        for player_id in pug.player_votes:
            vote = dict({
                    "id": player_id,
                    "map": pug.player_votes[player_id]
                })

            vote_list.append(vote)

        return vote_list

    def _pug_vote_count_list(self, pug):
        count_list = []

        votes = pug.map_votes
        for mname in votes:
            count = {
                    "map": mname,
                    "count": votes[mname]
                }
                
            count_list.append(count)

        return count_list
