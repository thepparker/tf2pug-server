TF2Pug API Response Format Documentation
========================================

This file describes the response format for JSON packets. Such responses include
pug status, pug listing, map votes, etc

Each response is headered by the API function that provides the given response

ITF2Pug/List:
------------
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

ITF2Pug/Status:
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

ITF2Pug/Player/List:
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

ITF2Pug/Vote/Add
----------------
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
