using System;
using System.Collections.Generic;
using System.Text;

using SteamBot.PugLib;

namespace ConsoleApplication1
{
    class Program
    {
        static TF2PugAPI api;

        static void Main(string[] args)
        {
            api = new TF2PugAPI();

            AddPlayer();

            //ListPugs();
        }

        static void ListPugs()
        {
            Dictionary<String, dynamic> result;

            result = api.GetPugListing();
            Console.WriteLine("\nPUG LISTING. RESPONSE: {0}", result["response"]);

            EPugAPIResponse response = (EPugAPIResponse)result["response"];
            
            if (response == EPugAPIResponse.Response_PugListing)
            {
                foreach (var pug in result["pugs"])
                {
                    Console.WriteLine(pug);
                }
            }
        }

        static void AddPlayer()
        {
            Dictionary<String, dynamic> result;

            result = api.AddPlayer(15, "joe");

            Console.WriteLine(result["pugs"]);

            EPugAPIResponse response = (EPugAPIResponse)result["response"];

            Console.WriteLine("RESPONSE: {0}", response);

            foreach (var pug in result["pugs"])
            {
                Console.WriteLine("PUG ID: {0}", pug["id"]);

                Console.WriteLine("PLAYERS:");
                foreach (var player in pug["players"])
                {
                    Console.WriteLine("\tid: {0}, name: {1}", player["id"], player["name"]);
                }

                Console.WriteLine("MAP VOTES");

                foreach (var mapvote in pug["map_vote_counts"])
                {
                    Console.WriteLine("map: {0}, votecount: {1}", mapvote["map"], mapvote["count"]);

                }
            }
        }
    }
}
