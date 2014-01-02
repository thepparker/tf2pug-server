using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using System.Text;
using System.Net;

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace SteamBot.TF2PugAPI
{
    class TF2PugInterface
    {
        static String api_address = "http://192.168.106.128:51515/";
        static String api_key = "123abc";

        static String pug_interface = "ITF2Pug";
        static String player_interface = pug_interface + "/Player";
        static String map_interface = pug_interface + "/Map";


        /**
         * Adds a player to a pug. See API docs for response format.
         * 
         * @param player_id The ID to add
         * @param name Name of the player being added
         * @param pug_id (optional) The pug to add the player to
         * @param size (optional) The size of the pug to add the player to
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer AddPlayer(ulong player_id, String name, long pug_id = -1, int size = 12)
        {
            String iface = player_interface + "/Add/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("steamid", player_id.ToString());
            aparams.Add("name", name);
            aparams.Add("size", size.ToString());

            if (pug_id >= 0)
            {
                aparams.Add("pugid", pug_id.ToString());
            }

            return PostToAPI(iface, aparams);
        }

        /**
         * Removes a player from whatever pug they are in. See API docs for
         * response format.
         * 
         * @param player_id The ID to remove
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer RemovePlayer(ulong player_id)
        {
            String iface = player_interface + "/Remove/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("steamid", player_id.ToString());
            
            return PostToAPI(iface, aparams);
        }

        /**
         * Creates a new pug. See API docs for response format. Requires
         * player information because they will be the first added to the pug.
         * 
         * @param player_id The ID of the player starting the pug
         * @param player_name The name of the player
         * @param size (optional) The size of the pug. Defaults to 12
         * @param map (optional) Forces the pug's map to be this map
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer CreatePug(ulong player_id, String player_name, 
            int size = 12, String map = "")
        {
            String iface = pug_interface + "/Create/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("steamid", player_id.ToString());
            aparams.Add("name", player_name);
            aparams.Add("key", api_key);
            aparams.Add("size", size.ToString());

            if (map != "")
            {
                aparams.Add("map", map);
            }

            return PostToAPI(iface, aparams);
        }

        /**
         * End a pug. See API docs for response format.
         * 
         * @param pug_id The ID of the pug to end
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer EndPug(long pug_id)
        {
            String iface = pug_interface + "/End/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("pugid", pug_id.ToString());

            return PostToAPI(iface, aparams);
        }

        /**
         * Gets a list of all the running pugs and their status. See API docs
         * for response format.
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer GetPugListing()
        {
            String iface = pug_interface + "/List/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);

            return GetFromAPI(iface, aparams);
        }

        /**
         * Gets the status of a pug. See API docs for response format.
         * 
         * @param pug_id The ID of the pug to get the status for
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer GetPugStatus(long pug_id)
        {
            String iface = pug_interface + "/Status/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("pugid", pug_id.ToString());

            return GetFromAPI(iface, aparams);
        }

        /**
         * Gets the players in the given pug. See API docs.
         * 
         * @param pug_id The ID of the pug to get the players for.
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer GetPugPlayerList(long pug_id)
        {
            String iface = player_interface + "/List/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("pugid", pug_id.ToString());

            return GetFromAPI(iface, aparams);
        }

        /**
         * Adds a player's map vote. Will only work if the pug's state is 
         * MAP_VOTING. Will also not work if the map has been forced.
         * See API docs for response format.
         * 
         * @param player_id The ID of the player performing the vote
         * @param map The map being voted for
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer AddMapVote(ulong player_id, String map)
        {
            String iface = map_interface + "/Vote/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("steamid", player_id.ToString());
            aparams.Add("map", map);

            return PostToAPI(iface, aparams);
        }

        /**
         * Forces a pug's map. Can only be used before map voting has begun,
         * and will prevent map voting from occuring. Furthermore, only the
         * pug admin can change the map. 
         * 
         * @param pug_id The ID of the pug to force the map in
         * @param map The map to force
         * 
         * @return Deserialized JSON object
         */
        public ResultContainer ForceMap(long pug_id, String map)
        {
            String iface = map_interface + "/Force/";

            NameValueCollection aparams = new NameValueCollection();
            aparams.Add("key", api_key);
            aparams.Add("pugid", pug_id.ToString());
            aparams.Add("map", map);

            return PostToAPI(iface, aparams);
        }

        /**
         * Takes a NameValueCollection of parameters and posts them to the
         * given interface of the API. Converts the result into an easily
         * readable dictionary.
         * 
         * @param aparams A NameValueCollection of parameters to post
         * @param interface_name The interface to post to
         * 
         * @return ResultContainer The parsed json result
         */
        ResultContainer PostToAPI(String interface_name, NameValueCollection aparams, string method = "POST")
        {
            String api_url = api_address + interface_name;

            try
            {
                using (WebClient client = new WebClient())
                {
                    byte[] response = client.UploadValues(api_url, method, aparams);
                    string response_body = Encoding.UTF8.GetString(response);

                    return JsonStringToContainer(response_body);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine("EXCEPTION POSTING TO API" + e.Message);
                return new ResultContainer();
            }
        }

        /**
         * Takes a NameValueCollection of parameters and performs a GET on the
         * given interface. Converts the result into a dictionary.
         * 
         * @param aparams The parameters
         * @param interface_name The interface to query
         * 
         * @result ResultContainer The parsed json result
         */
        ResultContainer GetFromAPI(String interface_name, NameValueCollection aparams)
        {
            String api_url = api_address + interface_name;
            try
            {
                using (WebClient client = new WebClient())
                {
                    client.QueryString = aparams;
                    string response_body = client.DownloadString(api_url);

                    return JsonStringToContainer(response_body);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine("EXCEPTION WHEN GETTING FROM API" + e.Message);
                return new ResultContainer();
            }
        }


        /**
         * Takes a JSON serialized string and returns a deseralized dictionary
         * for easy reading.
         * 
         * @param data The serialized json string
         * 
         * @return Deserialized JSON object
         */
        Dictionary<String, Object> JsonStringToDictionary(string data)
        {
            return JsonConvert.DeserializeObject<Dictionary<String, Object>>(data);
        }

        /**
         * Takes a JSON serialized string and returns a result container
         * which has the entire data set and the response code. This allows
         * for simpler returning.
         * 
         * @param data The serialized string
         * 
         * @return ResultContainer The container which has the deserialized data
         */
        ResultContainer JsonStringToContainer(string data)
        {
            return new ResultContainer(JsonStringToDictionary(data)); 
        }
    }

    /**
     * API response codes. These codes indicate the type of the response
     * being received, because some responses contain the same data but
     * not the same code. This is to prevent the need for extra API calls
     * to get data after a response code is received.
     */
    enum EPugAPIResponse
    {
        Response_None = 0,
        Response_PugListing = 1000,
        Response_PugStatus = 1001,
        Response_InvalidPug = 1002,
        Response_PugCreated = 1003,
        Response_PugEnded = 1004,
        Response_PugFull = 1005,
        Response_EmptyPugEnded = 1006,

        Response_PlayerList = 1100,
        Response_PlayerInPug = 1101,
        Response_PlayerNotInPug = 1102,
        Response_PlayerAdded = 1103,
        Response_PlayerRemoved = 1104,

        Response_MapVoteAdded = 1200,
        Response_MapForced = 1201,
        Response_MapNotForced = 1202,
        Response_MapVoteNotInProgress = 1203,
        Response_InvalidMap = 1204
    }
}
