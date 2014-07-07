import json

"""
A JSON Interface class, which will encode/decode Pug objects into/from JSON.
This is nice to have because psycopg2 lets us specify methods for converting
to and from JSON, which means we can just let this class take care of it and
not worry about translations between database and python in the PugManager
class.
"""
class JsonInterface(json):
    """ 
    Takes a Pug object and converts it into a JSON object
    @param obj The pug object

    @return JSON A JSON (string) object
    """
    def dumps(self, obj):
        pass

    def loads(self, data):
        pass
