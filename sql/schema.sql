-- Contains user auth keys
--DROP TABLE IF EXISTS api_keys;
CREATE TABLE api_keys (name text, key text UNIQUE);

-- Servers available for use in pugs
--DROP TABLE IF EXISTS servers;
CREATE TABLE servers (id serial, ip cidr NOT NULL, port integer NOT NULL, 
                      rcon_password text NOT NULL, password text, 
                      pug_id integer NOT NULL, log_port integer
                    );

-- The pugs
--DROP TABLE IF EXISTS pugs;
CREATE TABLE pugs (id serial, size integer, state integer, map varchar(32), 
                   map_forced boolean, players hstore, player_votes hstore,
                   map_votes hstore, map_vote_start bigint, 
                   map_vote_end bigint, server_id integer, team_red bigint[],
                   team_blue bigint[], 
                   api_key text references api_keys(key) ON UPDATE CASCADE
                );
