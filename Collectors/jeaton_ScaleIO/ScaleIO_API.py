# Author: James Eaton
# Date: 06/2018
# Filename: ScaleIO_API.py
# Description: Helper class to login/logout/pull data from ScaleIO networks
# Version: 1.5

import requests
import json
from requests.auth import HTTPBasicAuth

class ScaleIO_API():
      def __init__(self, api_url, username, password):
            """
            Initial setup of the ScaleIO object that includes various items needed for verification

            :param api_url: Base URL for API
            :type api_url: str
            :param username: Username to log in
            :type username: str
            :param password: Password to log in
            :type password: str
            """   
            self._username = username
            self._password = password
            self._api_url = api_url
            self._session = requests.Session()
            self._verify_ssl = False
            self._logged_in = False
    
      def __enter__(self):
            """
            Method that starts when the object is created
                  Returns self so that we can use the variables in the __init__ method in the main code
            """
            return self

      def __exit__(self, type, value, traceback):
            """
            Method to make sure the session logs out and closes
                  Called whenever the program ends
            """
            self._logout()
            self._session.close()

      def _login(self):
            """
            Responsible for logging into the URL and giving back a token
            """
            # Logs in and receives a token if done successfully
            login_response = self._session.get("https://{}/{}".format(self._api_url,"api/login"), verify=self._verify_ssl, auth=HTTPBasicAuth(self._username, self._password)).json()
            
            # Token is used as the password for future API calls
            # Username is no longer required, so it is left empty
            self._auth_token = login_response
            self._session.auth = HTTPBasicAuth('',self._auth_token)
            self._logged_in = True
            
      def _check_login(self):
            """
            Checks if you are logged in
            """
            if not self._logged_in:
                  self._login()
            else:
                  pass
            return None
          
      def _check_auth(self):
            """
            Returns the token to be tested whether it's a string or not
            """
            return self._auth_token

      def _query_System(self):
            """
            Currently queries the API for different things. This changes constantly. Can be deleted/remodeled later.
            """
            self._check_login()
            SystemInfo = self._session.get("https://{}/{}".format(self._api_url,"api/instances/Sds::cf96b80c00000001/relationships/Statistics"), verify=self._verify_ssl, auth=HTTPBasicAuth("", self._auth_token)).json()
            return SystemInfo

      def _query_selected_stats(self):
            """
            Queries the ScaleIO network to grab data specified in the payload variable
            If nothing is found, then a list of details is presented to show why it did not work
            Otherwise, returns the requested information in a json format.
            """

            # Headers var changes an item in the dictionary so the code runs
            # Payload var determines what we want to pull from the API
            headers = {"Content-Type":"application/json"}
            payload = {"selectedStatisticsList": [
                  {"type": "Volume",
                   "allIds": "",
                   "properties": ["numOfMappedSdcs", "userDataWriteBwc", "userDataReadBwc"]
                  }
              ]                
            }

            # Required to prepare the request; otherwise, an error saying that the content-type
            # in the header should be "application/json"
            req = requests.Request("POST", "https://{}/{}".format(self._api_url, "api/instances/querySelectedStatistics"), json=payload, headers=headers, auth=HTTPBasicAuth("", self._auth_token))
            prepped = req.prepare()
            Selected_stats = self._session.send(prepped)

            # Executes if it returns an item
            if Selected_stats.status_code == 200:
                  return Selected_stats.json()
              
            # Prints out some stats about the session to diagnose what happened    
            else:
                 print("Something went wrong")
                 self.print_req_attrs(Selected_stats, "", self._session) 

      def print_req_attrs(self, r, name, s):
            """
            Method to print out stats for help with diagnosing the problem
            """
            print("Session Cookies:", s.cookies)
            print("Session Headers:", s.headers)
            print("{}.request.url: {}".format(name, r.url))
            print("{}.request.headers: {}".format(name, json.dumps(dict(r.headers), indent=3)))
            print("{}.request.body: {}".format(name, r.request.body))
            print("{}.url: {}".format(name, r.url))
            print("{}.headers: {}".format(name, json.dumps(dict(r.headers), indent=3)))
            print("{}.cookies: {}".format(name, r.cookies))
            print("{}.text: {}".format(name, r.text))
            print("{}.status_code: {}".format(name, r.status_code))
            print("{}.reason: {}".format(name, r.reason))
            print()

      def _logout(self):
            """
            Method to log out of the session
            """
            logout = self._session.get("https://{}/{}".format(self._api_url,"api/logout"), verify=self._verify_ssl, auth=HTTPBasicAuth("", self._auth_token))