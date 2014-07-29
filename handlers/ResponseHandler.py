# The ResponseHandler handles all responses to API calls. Response codes
# are the code sent along with packets to indicate what the packet is for.

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

Response_MapVoteAdded = 1200
Response_MapForced = 1201
Response_MapNotForced = 1202
Response_MapVoteNotInProgress = 1203
Response_InvalidMap = 1204

Response_NoAvailableServers = 1300
Response_ServerConnectionError = 1301

class ResponseHandler(object):
    def __init__(self):
        pass

    def change_response_code(self, packet, new_code):
        packet["response"] = new_code

        return packet

    def no_available_servers(self):
        return { "response": Response_NoAvailableServers }

    def server_connection_error(self):
        return { "response": Response_ServerConnectionError }

    def pug_vote_added(self, pug):
        response = self.pug_status(pug)

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
                "name": pug.server.name,
                "anticheat": pug.server.anticheat,
                "ip": pug.server.ip,
                "port": pug.server.port
            }

        else:
            del packet["server"]

        del packet["_players"]
        del packet["player_stats"]

        packet["named_state"] = pug.get_state_string()
        packet["players"] = self._pug_players_list(pug)
        packet["map_vote_counts"] = self._pug_vote_count_list(pug)
        packet["player_votes"] = self._pug_vote_list(pug)

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

        for mname in pug.map_votes:
            count = dict({
                    "map": mname,
                    "count": pug.map_votes[mname]
                })

            count_list.append(count)

        return count_list
