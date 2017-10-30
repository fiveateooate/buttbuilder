"""libvirt connection client"""

import libvirt


class LibvirtClient():
    def __init__(self, libvirt_uri):
        self.__connection = libvirt.open(libvirt_uri)
        if self.__connection is None:
            raise buttlib.exceptions.LibVirtConnectionError("Failed to connect to {}".format(libvirt_uri))

    @property
    def connection(self):
        return self.__connection

    @connection.setter
    def connection(self, value):
        self.__connection = value
