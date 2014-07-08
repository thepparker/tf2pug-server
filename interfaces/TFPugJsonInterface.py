from BaseJsonInterface import BaseJsonInterface
from entities import Pug

import json

class TFPugJsonInterface(BaseJsonInterface):
    def dumps(self, pug):
        # need to establish a dictionary, and then dump it into a json string
        # to do this, we use the object's inbuilt __dict__ method (inherited
        # from base object class)
        obj_dict = pug.__dict__

        return BaseJsonInterface.dumps(obj_dict)

    def loads(self, data):
        # load the data into a dictionary and then set a Pug object's fields
        data_dict = BaseJsonInterface.loads(data)

        pug = Pug.Pug()

        for key in data_dict:
            if key == u'player_votes' or key == u'_players':
                # these keys are dictionaries, so we want to do them slightly 
                # different. i.e convert unicode keys back to longs
                tmp = {}
                for itemkey in data_dict[key]:
                    tmp[long(itemkey)] = data_dict[key][itemkey]

                data_dict[key] = tmp

            setattr(pug, str(key), data_dict[key])

        return pug
