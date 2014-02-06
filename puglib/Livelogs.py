
import urllib
import urllib2
import json

import settings

class API(object):
    def __init__(self, key, address):
        self.__api_address = address
        self.__api_key = key

        self.__api_interface = "/main.php"

    def get_live_logs(self):
        params = {
            "key": self.__api_key,
            "action": "get_live"
        }

        data = json.loads(self.get_json(self.__api_interface, params))

        if "result" in data and data["result"] == 1:
            return data["idents"]

        else:
            return {}

    def get_player_stats(self, steamids):
        # steamids is a list of IDs

        params = {
            "key": self.__api_key,
            "action": "get_stats",
            "steamids": ",".join(steamids)
        }

        data = json.loads(self.get_json(self.__api_interface, params))

        if "result" in data and data["result"] == 1:
            return data["stats"]

        else:
            return {}

    def get_json(self, interface, params):
        return urllib2.urlopen(self.__api_address + interface + "?" + urllib.urlencode(params)).read()
