import urllib2
import urllib
import json
import hmac
import hashlib
import time

from pprint import pprint

public_key = "publicabc123"
private_key = "123abc"


api_address = "http://192.168.101.128:51515/"

def main():
    res = create_pug(5, 'joebob')
    pugid = int(res["pug"]["id"])

    add_player(1, "rick", pugid)
    add_player(2, "steve", pugid)
    add_player(3, "jimmy", pugid)
    add_player(4, "roight", pugid)
    add_player(5, "kaki", pugid)
    add_player(6, "shneaky", pugid)
    add_player(7, "Faithless", pugid)
    add_player(8, "Shuz", pugid)
    add_player(9, "hero", pugid)
    add_player(10, "zato", pugid)
    add_player(11, "chrome", pugid)
    #add_player(12, "jak", pugid)

    #pug_status(int(res["pug"]["id"]))

    pug_list()

    #add_ban()
    #pug_list()


def vote_map(player_id, map_name):
    interface = "ITF2Pug/Map/Vote/"

    params = {
        "key": public_key,
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
        "key": public_key,
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
        "key": public_key
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
        "key": public_key,
        "pugid": pid
    }

    player_data = get_data(interface, params)
    
    jdata = json.loads(player_data)

    print "PLAYERS IN PUG %d:" % pid
    pprint(jdata)

    return jdata

def create_pug(pid, name, size = 12):
    create_params = {
        "key": public_key,
        "steamid": pid,
        "name": name,
        "size": size,
        "restriction": "+1500",
        "custom_id": "tf2-syd-1"
    }
    create_interface = "ITF2Pug/Create/"
    create_data = post_data(create_interface, create_params)
    
    jdata = json.loads(create_data)

    print "PUG Created: "
    pprint(jdata)

    return jdata

def end_pug(pid):
    params = {
        "key": public_key,
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
        "key": public_key,
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
        "key": public_key,
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
        "key": public_key
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
    # generate authentication
    params["auth_time"] = str(int(time.time()))
    h = hmac.new(private_key, public_key + params["auth_time"], hashlib.sha256)

    params["auth_token"] = h.hexdigest()

    return urllib2.urlopen(api_address + interface + "?" + urllib.urlencode(params)).read()

def post_data(interface, params):
    params["auth_time"] = str(int(time.time()))
    print "Encrypting " + public_key + params["auth_time"] + " with private key " + private_key

    h = hmac.new(private_key, public_key + params["auth_time"], hashlib.sha256)

    params["auth_token"] = h.hexdigest()

    return urllib2.urlopen(api_address + interface, urllib.urlencode(params)).read()


main()
