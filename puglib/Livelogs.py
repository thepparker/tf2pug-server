
import urllib
import urllib2
import json

import settings

class API(object):
    def __init__(self):
        self.__api_address = settings.livelogs_api_address
        self.__api_key = settings.livelogs_api_key

        self.__api_interface = "/main.php"

    def get_live_logs(self):
        params = {
            "key": self.__api_key
            "action": "get_live"
        }

        return json.loads(self.get_json(self.__api_interface, params))

    def get_player_stats(self, steamids):
        # steamids is a list of IDs

        params = {
            "key": self.__api_key,
            "action": "get_stats",
            "steamids": ",".join(steamids)
        }

        return json.loads(self.get_json(self.__api_interface, params))

    def get_json(self, interface, params):
        return urllib2.urlopen(self.__api_address + interface + "?" + urllib.urlencode(params)).read()
