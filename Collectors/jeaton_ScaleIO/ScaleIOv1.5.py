# Author: James Eaton
# Date: 06/2018
# Filename: jeaton_ScaleIO.py
# Description: Main function to pull API data from ScaleIO servers and push
#              that data to ElasticStack
# Version: 1.5

import requests
import logging
import time
import urllib3
from logging.handlers import RotatingFileHandler
import argparse

import ScaleIO_to_ES
from ScaleIO_to_ES import ScaleIO_to_ES
import ScaleIO_API
from ScaleIO_API import ScaleIO_API

# Disables verification warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 
      
if __name__ == "__main__":
      # Testing Argument Parser
      # If using !! in either your password, added / in there
      parser = argparse.ArgumentParser()
      parser.add_argument("url_address", help = "ScaleIO GW IP address", type = str)
      parser.add_argument("gw_username", help = "ScaleIO GW username", type = str)
      parser.add_argument("gw_password", help = "ScaleIO GW password", type = str)
      parser.add_argument("ES_IP", help = "ElasticSearch IP Address", type = str)
      parser.add_argument("ES_Port", help = "ElasticSearch Port Number", type = int)
      parser.add_argument("--init", help = "reinitialize the data index", type = bool, default = False)
      args = parser.parse_args()

      # Logging for testing
      my_handler = RotatingFileHandler(filename = "ScaleIOLog.log", maxBytes = 1 * 1024 * 1024, backupCount = 10, encoding = None, delay = 0)
      log_level = logging.DEBUG
      logger = logging.getLogger(__name__)
      logger.setLevel(log_level)
      logger.addHandler(my_handler)
      formatter = logging.Formatter("%(levelname)s: %(asctime)s: %(message)s")
      my_handler.setFormatter(formatter)

      # Creates the ScaleIO_API class and logs in
      with ScaleIO_API(args.url_address, args.gw_username, args.gw_password) as r:
            r._login()

            # Creates the ES class
            es = ScaleIO_to_ES(args.ES_IP, args.ES_Port)

            # Reinitializes data if needed
            if args.init:
                  es._create_index()

            
            # Error checking of the username and password
            while type(r._check_auth()) != str:
                  print("\nInvalid credentials. Please try again.")
                  url_address = input("\nEnter the SIO GW IP address: ")
                  gw_username = input("Enter the username: ")
                  gw_password = input("Enter the password: ")
                  r = ScaleIO_API(url_address, gw_username, gw_password)
                  r._login()
            
            try:
                  # Counter to keep track of ID Number
                  counter = 1

                  while True:
                        query_stats = r._query_selected_stats()
                        #system_information = r._query_System()

                        mappedSDCs = query_stats["Volume"]["0bb7627300000004"]["numOfMappedSdcs"]
                        numSecondsW = query_stats["Volume"]["0bb7627300000004"]["userDataWriteBwc"]["numSeconds"]
                        weightInKBW = query_stats["Volume"]["0bb7627300000004"]["userDataWriteBwc"]["totalWeightInKb"]
                        numOccurredW = query_stats["Volume"]["0bb7627300000004"]["userDataWriteBwc"]["numOccured"]
                        numSecondsR = query_stats["Volume"]["0bb7627300000004"]["userDataReadBwc"]["numSeconds"]
                        weightInKBR = query_stats["Volume"]["0bb7627300000004"]["userDataReadBwc"]["totalWeightInKb"]
                        numOccurredR = query_stats["Volume"]["0bb7627300000004"]["userDataReadBwc"]["numOccured"]

                        # Push that data to ES
                        es._write_data(counter, mappedSDCs, numSecondsW, weightInKBW, numOccurredW, numSecondsR, weightInKBR, numOccurredR)

                        # Log information
                        logger.info("Number of mapped SDCs: {}".format(mappedSDCs))
                        logger.info("Number of seconds (write): {}".format(numSecondsW))
                        logger.info("Total weight in KB (write): {}".format(weightInKBW))
                        logger.info("Number of times occured (write): {}\n".format(numOccurredW))
                        logger.info("Number of seconds (read): {}".format(numSecondsR))
                        logger.info("Total weight in KB (read): {}".format(weightInKBR))
                        logger.info("Number of times occured (read): {}\n".format(numOccurredR))

                        print("Information logged!")

                        res = es._query_ES(counter)
                        test1 = res["_source"]["Time"]
                        test2 = res["_source"]["NumberOfSecondsW"]
                        test3 = res["_source"]["WeightInKBW"]
                        test4 = res["_source"]["NumberOfSecondsR"]
                        test5 = res["_source"]["WeightInKBR"]

                        logger.info("Time when pushed: {}".format(str(test1)))
                        logger.info("Number of seconds (write): {}".format(str(test2)))
                        logger.info("Weight in KB (write): {}\n".format(str(test3)))
                        logger.info("Number of seconds (read): {}".format(str(test4)))
                        logger.info("Weight in KB (read): {}\n".format(str(test5)))

                        # Stops program for 5 seconds, then starts again
                        time.sleep(5)

                        # Adds to the counter for ID
                        counter += 1

            except KeyboardInterrupt:
                  print("\nExiting!")



