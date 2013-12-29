#!/usr/bin/env python


import logging
import tornado.web
import tornado.ioloop
import PugLib

from tornado.options import define, options, parse_command_line

define("port", default = 51515, help = "take a guess motherfucker", type = int)


class PugApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            # pug creation and player adding/removing
            (r"/ITF2Pug/List", PugListHandler),
            (r"/ITF2Pug/Add", PugAddHandler),
            (r"/ITF2Pug/Remove", PugRemoveHandler),
            (r"/ITF2Pug/Create", PugCreateHandler),
            (r"/ITF2Pug/End", PugEndHandler),

            # pug player listings
            ("r/ITF2Pug/Player/List", PugPlayerListHandler),
        ]

        settings = {
            debug = True,
        }

        tornado.web.Application.__init__(self, handlers, **settings)

        self.pug_manager = PugLib.PugManager()




if __name__ == "__main__":
    parse_command_line()

    app = tornado.web.Application(
        



        )
