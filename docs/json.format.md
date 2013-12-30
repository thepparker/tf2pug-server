TF2Pug API Response Format Documentation
========================================

This file describes the response format for JSON packets. Such responses include
pug status, pug listing, map votes, etc

Each response is headered by the API function that provides the given response.

The values of response codes (the codes prepended with Response_) can be found
in puglib/ResponseHandler.py

ITF2Pug/List/
-------------
Returns a list of all the current pugs and their status.

    JSON
    {
        response: Response_PugListing
        pugs: 
        [
            {
                id: long,
                size: int,
                map: string,
                starter: long (id of pug starter),

                ip: string,
                port: int,
                password: string,

                mumble: string,

                players: {
                    player_id: player_name,
                    player_id: player_name,
                    ...
                },
            },
            {
                ...
            },
        ]
    }

ITF2Pug/Status/
---------------
Returns the status of a single pug.

    JSON
    {
        response: Response_PugStatus
        pugs: [
            {
                id: long,
                size: int,
                map: string,
                starter: long (id of pug starter),

                ip: string,
                port: int,
                password: string,

                mumble: string,

                players: {
                    player_id: player_name,
                    player_id: player_name,
                    ...
                },
            }  
        ]
    }

ITF2Pug/Player/Add/
-------------------
Adds a player to the given pug, the first pug with space available or creates
a new pug.

Response is an ITF2Pug/Status/ response for the pug that the player was added
to with a code of Response_PlayerAdded.

If the player is already in a pug, you will receive an ITF2Pug/Status/
response for the pug the player is already in (so you must check the pug ID)
with a code of Response_PlayerInPug.

If you specified a pug ID and there was no space in the pug, you will receive
an ITF2Pug/Status/ response with a Response_PugFull code.

If the pug does not exist anymore, the response code will be 
Response_InvalidPug. In this case, it is advised to perform an ITF2Pug/List/ to
get an updated pug list.

ITF2Pug/Player/Remove/
----------------------
Removes the given player from the pug they are in.

If the player was successfully removed, and the below responses do not apply,
an ITF2Pug/Status/ response for the pug the player was removed from will be
sent with a code of Response_PlayerRemoved.

If the player is not in a pug, an empty packet with the response code
Response_PlayerNotInPug will be sent. 

If the pug was made empty by removing this player, the response will be an 
otherwise empty packet with the code Response_EmptyPugEnded. It would be
advised to get an updated listing after this response.

ITF2Pug/Player/List/
--------------------
Returns the list of players for a given pug

    JSON
    {
        response: Response_PlayerList
        players: {
            player_id: player_name,
            player_id: player_name,
            ...
        }

    }

ITF2Pug/Vote/Add/
-----------------
Adds a vote for the specified map by the specified player. Returns a list of
current votes and their count.

    JSON
    {
        response: Response_MapVoteAdded
        
        player_votes: {
            player_id: map,
            player_id: map,
            ...
        },

        map_votes: {
            map: count,
            map: count,
            ...
        }
    }
