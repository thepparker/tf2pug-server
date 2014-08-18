import urllib2
import urllib
import json

from pprint import pprint

api_key = "123abc"

api_address = "http://192.168.101.128:51515/"

def main():
    """
    res = create_pug(5, 'joebob')
    pugid = int(res["pug"]["id"])

    add_player(1, "rick", pugid)
    add_player(2, "steve", pugid)
    add_res = add_player(3, "jimmy", pugid)
    add_player(76561197976832968, "roight", pugid)
    add_player(76561198031041077, "kaki", pugid)
    add_player(76561198011707860, "shneaky", pugid)
    add_player(76561198064565908, "Faithless", pugid)
    add_player(76561197970805594, "Shuz", pugid)
    add_player(76561197997976691, "hero", pugid)
    add_player(76561198045479800, "zato", pugid)
    add_player(76561198042997347, "chrome", pugid)
    add_player(76561197997302892, "jak", pugid)

    player_list(int(res["pug"]["id"]))
    pug_status(int(res["pug"]["id"]))

    pug_list()

    vote_map(2, "cp_granary")
    vote_map(3, "cp_badlands")
    """
    add_ban()


def vote_map(player_id, map_name):
    interface = "ITF2Pug/Map/Vote/"

    params = {
        "key": api_key,
        "steamid": player_id,
        "map": map_name
    }

    data = post_data(interface, params)

    jdata = json.loads(data)

    print "MAP VOTE RESULT: "
    pprint(jdata)

    return jdata

def pug_status(pid):
    interface = "ITF2Pug/Status/"

    params = {
        "key": api_key,
        "pugid": pid
    }

    data = get_data(interface, params)

    jdata = json.loads(data)

    print "STATUS FOR PUG %d:" % pid
    pprint(jdata)

    return jdata

def pug_list():
    interface = "ITF2Pug/List/"

    params = {
        "key": api_key
    }

    data = get_data(interface, params)

    jdata = json.loads(data)

    print "PUG LISTING:"
    pprint(jdata)

    print "PUG IDS:"
    for pug in jdata["pugs"]:
        print pug["id"]

    return jdata

def player_list(pid):
    interface = "ITF2Pug/Player/List/"

    params = {
        "key": api_key,
        "pugid": pid
    }

    player_data = get_data(interface, params)
    
    jdata = json.loads(player_data)

    print "PLAYERS IN PUG %d:" % pid
    pprint(jdata)

    return jdata

def create_pug(pid, name, size = 12):
    create_params = {
        "key": api_key,
        "steamid": pid,
        "name": name,
        "size": size
    }
    create_interface = "ITF2Pug/Create/"
    create_data = post_data(create_interface, create_params)
    
    jdata = json.loads(create_data)

    print "PUG Created: "
    pprint(jdata)

    return jdata

def end_pug(pid):
    params = {
        "key": api_key,
        "pugid": pid
    }

    end_interface = "ITF2Pug/End/"

    end_data = post_data(end_interface, params)

    jdata = json.loads(end_data)

    print "PUG ENDED"
    pprint(jdata)

    return jdata


def add_player(pid, name, pugid = None, size=12):

    add_params = {
        "key": api_key,
        "steamid": pid,
        "name": name
    }

    if pugid is not None:
        print "Adding %s (%s) to pug %d" % (name, pid, pugid)
        add_params["pugid"] = pugid

    add_interface = "ITF2Pug/Player/Add/"
    add_data = post_data(add_interface, add_params)
    
    jdata = json.loads(add_data)

    print "PLAYER ADDED: "
    pprint(jdata)

    return jdata

def remove_player(pid):
    params = {
        "key": api_key,
        "steamid": pid
    }

    remove_interface = "ITF2Pug/Player/Remove/"
    remove_data = post_data(remove_interface, params)

    jdata = json.loads(remove_data)

    print "PLAYER REMOVED:"
    pprint(jdata)

    return jdata

def add_ban():
    print "Attempting to add ban"
    params = {
        "key": api_key
    }

    data = {
        "bannee": {
            "id": 1,
            "name": "1"
        },
        "banner": {
            "id": 2,
            "name": "2"
        },

        "reason": "banned",
        "duration": 2
    }
    params["data"] = json.dumps(data)

    ban_interface = "ITF2Pug/Ban/Add/"
    ban_data = post_data(ban_interface, params)

    jdata = json.loads(ban_data)
    pprint(jdata)


def get_data(interface, params):
    return urllib2.urlopen(api_address + interface + "?" + urllib.urlencode(params)).read()

def post_data(interface, params):
    return urllib2.urlopen(api_address + interface, urllib.urlencode(params)).read()


main()
