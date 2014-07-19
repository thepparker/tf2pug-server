from entities import Pug

import json

"""
A JSON Interface class, which will encode/decode Pug objects into/from JSON.
This is nice to have because psycopg2 lets us specify methods for converting
to and from JSON, which means we can just let this class take care of it and
not worry about translations between database and python in the PugManager
class.

This class conforms to psycopg's json methodology, so it can be used freely
with PostgreSQL 9.2+ and JSON fields. You can of course use it to convert
Pug objects to JSON and store it in string fields, or any applicable data
field in your database of choice.
"""
class BaseJsonInterface(object):
    """ 
    Takes a Pug object and converts it into a JSON object
    @param obj The pug object

    @return JSON A JSON (string) object
    """
    def dumps(self, obj):
        return json.dumps(obj)

    """
    Takes a JSON object and converts it to a Pug object

    @param data The JSON object string

    @return Pug A Pug object
    """
    def loads(self, data):
        return json.loads(data)


class TFPugJsonInterface(BaseJsonInterface):
    def dumps(self, pug):
        # need to establish a dictionary, and then dump it into a json string
        # to do this, we use the object's inbuilt __dict__ method (inherited
        # from base object class)
        obj_dict = pug.__dict__.copy()

        obj_dict["server"] = None # remove the server reference

        return json.dumps(obj_dict)

    def loads(self, data):
        # load the data into a dictionary and then set a Pug object's fields
        data_dict = json.loads(data)

        pug = Pug.Pug()

        for key in data_dict:
            if key == u'player_votes' or key == u'_players' or key == 'player_stats':
                # these keys are dictionaries, so we want to do them slightly 
                # different. i.e convert unicode keys back to longs
                tmp = {}
                for itemkey in data_dict[key]:
                    tmp[long(itemkey)] = data_dict[key][itemkey]

                data_dict[key] = tmp

            setattr(pug, str(key), data_dict[key])

        return pug
