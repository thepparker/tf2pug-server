"""
PacificES API Interface. This interface is used for recording matches with PES
and storing incident reports during pugs.
"""

import urllib
import json
import time
import hmac
import hashlib
import logging
import operator

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

PES_API_METHODS = {
    "create_match": "createPugMatch",
    "create_report": "createPugReport"
}

from pprint import pprint

class PESAPIInterface(object):
    def __init__(self, base_url, user_id, private_key):
        self.base_url = base_url
        self.user_id = user_id
        self.private_key = private_key

    def get_params(self, params):
        return params

    def __get_params(self, params):
        """
        NO LONGER USED. AUTHENTICATION IS NOW IP WHITELIST

        We need to order the given parameters alphabetically by the values in 
        the given params dict. Then we convert it to a string and hash it
        using our private key, yielding the key used for authentication. We then
        add these parameters to the original params dict.
        """
        # convert params to a URL query string with keyvalues sorted by values
        sorted_params = sorted(params.items(), key = operator.itemgetter(1))
        # sorted_params is now a list in the format [(key, value), ...],
        # ordered by value
        query_string = "&".join(
                [ "{0}={1}".format(x[0], x[1]) for x in sorted_params ]
            )


        h = hmac.new(self.private_key, query_string, hashlib.sha256)
        auth_token = h.hexdigest()

        return dict(params, api_key = auth_token, api_id = self.user_id)

    def create_match(self):
        pass

    def create_report(self, offender, victim, reason, match_id, callback = None):
        # Note that offender and victim are 64bit steamids. We do NOT convert
        # them to STEAM_ format, as the API accepts 64bit ids
        method = PES_API_METHODS["create_report"]

        params = self.get_params({
            "offender_steam_id": offender,
            "victim_steam_id": victim, 
            "reason": reason,
            "match_id": match_id,
            "action": method
        })

        self.post(params, callback)

    def post(self, params, callback):
        client = AsyncHTTPClient()
        request = HTTPRequest(url = self.api_url(), 
                              method = "POST",
                              body = urllib.urlencode(params))

        pprint(self.api_url())
        pprint(urllib.urlencode(params))

        logging.debug("POSTING REPORT")

        client.fetch(request, self.api_callback(callback))

    def get(self, params):
        pass

    def api_url(self, params = None):
        if params is None:
            return self.base_url
        else:
            return "{0}?{1}".format(self.base_url, urllib.urlencode(params))

    def api_callback(self, callback):
        if callback is None:
            return None

        return lambda d: self.wrap_callback(d, callback)

    def wrap_callback(self, response, callback):
        """
        Wraps a callback for AsyncHTTPClient requests, so that we can
        extrapolate the data and only pass that back
        """
        if callback is not None and response.error is None:
            try:
                callback(response.body)
            except:
                raise

        elif response.error is not None:
            logging.error("Exception fetching API request: %s", response.error)
