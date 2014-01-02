using System;
using System.Collections.Generic;
using System.Text;

using SteamBot.TF2PugAPI;

namespace ConsoleApplication1
{
    class Program
    {
        static TF2PugInterface api;

        static void Main(string[] args)
        {
            api = new TF2PugInterface();

            AddPlayer();

            //ListPugs();
        }

        static void ListPugs()
        {
            ResultContainer result = api.GetPugListing();

            Console.WriteLine("\nPUG LISTING. RESPONSE: {0}", result.response);
            
            if (result.response == EPugAPIResponse.Response_PugListing)
            {
                foreach (var pug in result.Data["pugs"])
                {
                    Console.WriteLine(pug);
                }
            }
        }

        static void AddPlayer()
        {
            ResultContainer result = api.AddPlayer(15, "joe");

            Console.WriteLine("RESPONSE: {0}", result.response);

            if (result.response == EPugAPIResponse.Response_PlayerAdded)
            {
                var pug = result.Data["pug"];
                Console.WriteLine(pug);
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
