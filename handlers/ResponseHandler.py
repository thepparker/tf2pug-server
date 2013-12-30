# The ResponseHandler handles responses that require packet construction, so
# the PugManager does not have unnecessary bloat

Response_PugListing = 1000
Response_PugStatus = 1001
Response_InvalidPug = 1002
Response_PugEnded = 1003
Response_PugFull = 1004
Response_EmptyPugEnded = 1005

Response_PlayerList = 1100
Response_PlayerInPug = 1101
Response_PlayerNotInPug = 1102
Response_PlayerAdded = 1103
Response_PlayerRemoved = 1104

Response_MapVoteAdded = 1200

class ResponseHandler(object):
    def __init__(self):
        pass

    def change_response_code(self, packet, new_code):
        packet["response"] = new_code

        return packet

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

    def player_not_in_pug(self, pug):
        return { "response": Response_PlayerNotInPug }

    def pug_full(self, pug):
        response = self.pug_status(pug)

        self.change_response_code(response, Response_PugFull)

        return response

    def invalid_pug(self):
        return { "response": Response_InvalidPug }

    def empty_pug_ended(self):
        return { "response": Response_EmptyPugEnded }

    def player_list(self, pug):
        response = {}

        if pug is None:
            response["response"] = Response_InvalidPug
        else:
            response = {
                "response": Response_PlayerList,
                "players": pug._players
            }

        return response

    def pug_listing(self, pugs):
        response = {
            "response": Response_PugListing,
            "pugs": [ self._pug_status_packet(pug) for pug in pugs ]
        }

        return response

    def pug_status(self, pug):
        response = {}

        if pug is None:
            response["response"] = Response_InvalidPug

        else:
            response["response"] = Response_PugStatus

            response["pugs"] = [ self._pug_status_packet(pug) ]

        return response

    def _pug_status_packet(self, pug):
        packet = {
            "id": pug.id,
            "size": pug.size,
            "map": pug.map,
            "starter"] = pug.starter,

            "ip": pug.ip,
            "port": pug.port,
            "password": pug.password,

            "mumble": "",

            # players is already a dict, so we can just use that
            "players": pug._players
        }

        return packet

    def _pug_player_packet(self, pug):
        packet = {}

