import BaseJsonInterface.BaseJsonInterface
from entities import Pug

import json

class TFPugJsonInterface(BaseJsonInterface):
    def dumps(self, obj):
        # need to establish a dictionary, and then dump it into a json string

        obj_dict = {}

        return BaseJsonInterface.dumps(obj_dict)

    def loads(self, data):
        # load the data into a dictionary and then set a Pug object's fields
        data_dict = BaseJsonInterface.loads(data)

        pug = Pug.Pug()

        return pug
