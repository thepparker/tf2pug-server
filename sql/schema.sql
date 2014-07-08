CREATE EXTENSION hstore;
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
                      server_group integer references api_keys(server_group) ON UPDATE CASCADE
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
-- DROP TABLE IF EXISTS players;
CREATE TABLE players (id serial, steamid bigint UNIQUE NOT NULL, games_since_med integer NOT NULL, 
                      games_played integer NOT NULL, rating decimal DEFAULT 1500,
                      modified TIMESTAMP DEFAULT current_timestamp);

-- Trigger for players modified (last playtime)
CREATE TRIGGER update_players_modtime BEFORE UPDATE ON players
  FOR EACH ROW EXECUTE PROCEDURE update_modified_time();

-- THIS FUNCTION TAKES TWO QUERIES, AN INSERT AND AN UPDATE QUERY. 
-- IT ATTEMPTS TO RUN THE UPDATE QUERY FIRST, IF UNSUCCESSFUL IT 
-- RUNS THE INSERT QUERY.
-- The queries _MUST_ be safe before being passed to this function
CREATE OR REPLACE FUNCTION pgsql_upsert (insert_query text, update_query text) 
RETURNS void AS $_$
BEGIN
    LOOP
        --UPDATE
        EXECUTE update_query;
        --CHECK IF SUCCESSFUL
        IF found THEN
            RETURN;
        END IF;
        
        -- Couldn't update, so let's insert.
        -- This is where the loop comes in. If two updates are attempted
        -- at the same time it will cause a unique_violation. When this 
        -- happens, we loop through again
        BEGIN
            EXECUTE insert_query;
        EXCEPTION WHEN unique_violation THEN
            RETURN;
        END;
    END LOOP;
END;
$_$ LANGUAGE 'plpgsql';
