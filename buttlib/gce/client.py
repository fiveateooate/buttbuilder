"""Class for connection to and info for gcp"""

import os
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
import buttlib


class GCEClient():
    def __init__(self, region, project, zone=""):
        if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
            raise buttlib.common.MissingEnvVarsError("Google API requires credentials file to be exported ie: GOOGLE_APPLICATION_CREDENTIALS=/path/to/file")
        self._credentials = GoogleCredentials.get_application_default()
        self.__connection = discovery.build('compute', 'v1', credentials=self._credentials)
        self.__region = region
        self.__project = project
        self.__zone = zone

    @property
    def connection(self):
        return self.__connection

    @connection.setter
    def connection(self, value):
        self.__connection = value

    @property
    def region(self):
        return self.__region

    @region.setter
    def region(self, region):
        self.region = region

    @property
    def zone(self):
        return self.__zone

    @zone.setter
    def zone(self, zone):
        self.__zone = zone

    @property
    def project(self):
        return self.__project

    @project.setter
    def project(self, project):
        self.project = project
