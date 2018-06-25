# Author: James Eaton
# Date: 06/2018
# Filename: ScaleIO_to_ES.py
# Description: Helper class to push to and query data from ElasticStack
# Version: 1.5

import datetime
from elasticsearch import Elasticsearch

class ScaleIO_to_ES():
      def __init__(self, host, port):
            """
            Initial setup of ElasticSearch object

            :param host: Base IP address of ES
            :type host: str
            :param port: Base port number of ES
            :type port: int
            """ 
            self.host = host
            self.port = port
            self.database = "james_test_db"
            self.table = "james_test_table"
            self.es = Elasticsearch(host=self.host, port=self.port)

      def _create_index(self):
            # Checks if your index already exists.
            #     If so, deletes it and recreates it.
            if self.es.indices.exists(self.database):
                  # Log information here
                  self.es.indices.delete(self.database)

            self.es.indices.create(self.database)

      def _write_data(self, vol_id, mappedSDCs, numSecondsW, weightInKBW, numOccurredW, numSecondsR, weightInKBR, numOccurredR):
            collection_time = datetime.datetime.now()
            
            # Start of a dictionary that will be put into Elasticsearch
            dataToEnter = {}
            dataToEnter["Name"] = "Volumes"
            dataToEnter["VolID"] = "0bb7627300000004"
            dataToEnter["Time"] = collection_time
            dataToEnter["NumberMappedSDCs"] = mappedSDCs
            dataToEnter["NumberOfSecondsW"] = numSecondsW
            dataToEnter["WeightInKBW"] = weightInKBW
            dataToEnter["NumOccurredW"] = numOccurredW
            dataToEnter["NumberOfSecondsR"] = numSecondsR
            dataToEnter["WeightInKBR"] = weightInKBR
            dataToEnter["NumOccurredR"] = numOccurredR

            self.es.index(index=self.database, doc_type=self.table, id=vol_id, body=dataToEnter)

      def _query_ES(self, counter):
            result = self.es.get(index = "james_test_db", doc_type = "james_test_table", id = counter)
            return result




