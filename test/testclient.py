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

    add_player(3, "jimmy", int(res["pugs"][0]["id"]))

    create_pug(1, "rick")


def create_pug(pid, name, size = 12):
    create_params = {
        "key": api_key,
        "steamid": pid,
        "name": name,
        "size": size
    }
    create_interface = "ITF2Pug/Create/"
    create_data = get_data(create_interface, create_params)
    
    jdata = json.loads(create_data)

    print "PUG Created: "
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
    add_data = get_data(add_interface, add_params)
    
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
    remove_data = get_data(remove_interface, params)

    jdata = json.loads(remove_data)

    print "PLAYER REMOVED:"
    pprint(jdata)

    return jdata

def get_data(interface, params):
    return urllib2.urlopen(api_address + interface, urllib.urlencode(params)).read()


main()
