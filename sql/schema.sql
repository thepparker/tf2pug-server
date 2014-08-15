-- Contains user auth keys
--DROP TABLE IF EXISTS api_keys;
CREATE TABLE api_keys (name text NOT NULL, pug_group integer NOT NULL, 
                       server_group integer NOT NULL, key text UNIQUE NOT NULL
                    );

-- Servers available for use in pugs
--DROP TABLE IF EXISTS servers;
CREATE TABLE servers (id serial, ip cidr NOT NULL, port integer NOT NULL, 
                      rcon_password text NOT NULL, password text, 
                      pug_id integer NOT NULL, log_port integer,
                      server_group integer NOT NULL
                    );

-- The pugs
--DROP TABLE IF EXISTS pugs;
CREATE TABLE pugs (id serial, data text NOT NULL, 
                   modified TIMESTAMP DEFAULT current_timestamp);

-- Update trigger for pugs
CREATE OR REPLACE FUNCTION update_modified_time() 
RETURNS TRIGGER AS $_$
  BEGIN
    NEW.modified = now();
    RETURN new;
  END;
$_$ LANGUAGE 'plpgsql';

CREATE TRIGGER update_pugs_modtime BEFORE UPDATE ON pugs
  FOR EACH ROW EXECUTE PROCEDURE update_modified_time();

--DROP TABLE IF EXISTS pugs_index;
CREATE TABLE pugs_index(id serial, pug_entity_id integer UNIQUE NOT NULL,
                        finished boolean NOT NULL, 
                        api_key text references api_keys(key) ON UPDATE CASCADE
                    );

-- Player stats (games played, games since med) for medic choosing
-- DROP TABLE IF EXISTS players CASCADE;
CREATE TABLE players (id serial, steamid bigint UNIQUE NOT NULL, data text NOT NULL,
                      modified TIMESTAMP DEFAULT current_timestamp);

-- DROP TABLE IF EXISTS players_index;
CREATE TABLE players_index(steamid bigint references players(steamid) ON UPDATE CASCADE, 
                           item text, value decimal, UNIQUE(steamid, item));

-- Trigger for players modified (last playtime)
CREATE TRIGGER update_players_modtime BEFORE UPDATE ON players
  FOR EACH ROW EXECUTE PROCEDURE update_modified_time();
