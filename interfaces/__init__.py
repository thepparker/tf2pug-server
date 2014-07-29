from .tflogging import TFLogInterface
from .jsonconverter import TFPugJsonInterface
from .database import PSQLDatabaseInterface

import UDPServer

GAME_CODES = {
    "TF2": 1,
}

JSON_INTERFACE = {
    1: TFPugJsonInterface
}

LOG_INTERFACE = {
    1: TFLogInterface
}

DB_INTERFACE = {
    "PGSQL": PSQLDatabaseInterface
}

def get_json_interface(game):
    if not game in GAME_CODES:
        raise NotImplementedError("No json interface exists for that game")

    return JSON_INTERFACE[GAME_CODES[game]]

def get_log_interface(game):
    if not game in GAME_CODES:
        raise NotImplementedError("No log interface exists for that game")

    return LOG_INTERFACE[GAME_CODES[game]]

def get_db_interface(provider):
    if not provider in DB_INTERFACE:
        raise NotImplementedError("No db interface exists for that db provider")

    return DB_INTERFACE[provider]
