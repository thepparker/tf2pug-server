#!/usr/bin/env python


import logging
import tornado.web
import tornado.ioloop
import puglib

from tornado.options import define, options, parse_command_line

define("port", default = 51515, help = "take a guess motherfucker", type = int)


class Application(tornado.web.Application):
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

        self.pug_manager = puglib.PugManager()

        tornado.web.Application.__init__(self, handlers, **settings)

    def valid_api_key(self, key):
        return True


if __name__ == "__main__":
    parse_command_line()

    api_server = tornado.httpserver.HTTPServer(Application())
    api_server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()


