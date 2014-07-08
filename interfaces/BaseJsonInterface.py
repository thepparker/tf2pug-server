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
class BaseJsonInterface(json):
    """ 
    Takes a Pug object and converts it into a JSON object
    @param obj The pug object

    @return JSON A JSON (string) object
    """
    def dumps(self, obj):
        raise NotImplementedError("You need to override this method")

    def loads(self, data):
        raise NotImplementedError("You need to override this method")
