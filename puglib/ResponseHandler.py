# The ResponseHandler handles responses that require packet construction, so
# the PugManager does not have unnecessary bloat

Response_PugListing = 1000
Response_PugStatus = 1001
Response_InvalidPug = 1002

Response_PlayerList = 1003

class ResponseHandler(object):
    def __init__(self):
        pass

    def construct_player_list_packet(self, pug):
        response = {}
        if pug is None:
            response["response"] = Response_InvalidPug
        else:
            response = {
                "response": Response_PlayerList,
                "players": pug._players
            }

        return response

    def construct_list_packet(self, pugs):
        response = {
            "response": Response_PugListing

            "pugs": [ self._pug_status_packet(pug) for pug in pugs ]
        }

        return response

    def construct_status_packet(self, pug):
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

