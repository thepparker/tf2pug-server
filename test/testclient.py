import urllib2
import urllib
import json

from pprint import pprint

api_key = "123abc"

api_address = "http://192.168.106.128:51515/"

def main():
    res = add_player(1, "rick")
    add_player(2, "steve")

    remove_player(1)

    add_player(3, "jimmy", int(res["pug"]["id"]))

    res2 = create_pug(1, "rick", 18)

    player_list(int(res["pug"]["id"]))
    pug_status(int(res["pug"]["id"]))

    pug_list()

    vote_map(1, "cp_granary")
    vote_map(1, "cp_badlands")



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

def get_data(interface, params):
    return urllib2.urlopen(api_address + interface + "?" + urllib.urlencode(params)).read()

def post_data(interface, params):
    return urllib2.urlopen(api_address + interface, urllib.urlencode(params)).read()


main()
