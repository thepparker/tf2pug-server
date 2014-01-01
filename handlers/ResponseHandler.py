# The ResponseHandler handles all responses to API calls. Response codes
# are the code sent along with packets to indicate what the packet is for.

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

class ResponseHandler(object):
    def __init__(self):
        pass

    def change_response_code(self, packet, new_code):
        packet["response"] = new_code

        return packet

    def vote_status(self, pug):
        response = self._pug_status_packet(pug)

        self.change_response_code(response, Response_MapVoteAdded)

        return response

    def player_added(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PlayerAdded)

        return response

    def player_removed(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PlayerRemoved)

        return response

    def player_in_pug(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PlayerInPug)

        return response

    def player_not_in_pug(self):
        return { "response": Response_PlayerNotInPug }

    def pug_full(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PugFull)

        return response

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
        packet = {
            "id": pug.id,
            "admin": pug.admin,

            # state is an enum style variable which lets us know what stage
            # the pug is at
            "state": pug.state,

            "size": pug.size,

            "map_forced": pug.map_forced,
            "map": pug.map,

            "ip": pug.ip,
            "port": pug.port,
            "password": pug.password,

            "mumble": "",

            # players is converted to a proper json array
            "players": self._pug_players_list(pug),
            "team_red": pug.team_red,
            "team_blue": pug.team_blue,

            # must convert votes to json arrays too
            "player_votes": self._pug_vote_list(pug),
            "map_vote_counts": self._pug_vote_count_list(pug),

            # these fields store the times that map voting has begun and when
            # it will end. this is required so that clients know when they
            # should get an updated status after map voting
            "map_vote_start": pug.map_vote_start,
            "map_vote_end": pug.map_vote_end
        }

        return packet

    def _pug_players_list(self, pug):
        player_list = []

        for player_id in pug._players:
            player = dict({
                    "id": player_id,
                    "name": pug._players[player_id]
                })


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
