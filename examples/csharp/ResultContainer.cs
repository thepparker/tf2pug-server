using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace SteamBot.TF2PugAPI
{
    class ResultContainer
    {
        public EPugAPIResponse response { get; private set; }

        Dictionary<String, Object> private_data;

        public ResultContainer()
        {
            response = EPugAPIResponse.Response_None;
            private_data = null;
        }

        public ResultContainer(Dictionary<String, dynamic> data)
        {
            if (data.ContainsKey("response"))
            {
                response = (EPugAPIResponse)data["response"];
            }
            else
            {
                response = EPugAPIResponse.Response_None;
            }

            this.private_data = data;
        }

        public Dictionary<String, dynamic> Data
        {
            get { return this.private_data; }
        }
    }
}
