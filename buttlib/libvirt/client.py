"""libvirt connection client"""

import libvirt
import buttlib


class LibvirtClient():
    def __init__(self, libvirt_uri):
        self.__connection = libvirt.open(libvirt_uri)
        if self.__connection is None:
            raise buttlib.common.LibVirtConnectionError("Failed to connect to {}".format(libvirt_uri))

    @property
    def connection(self):
        """Short summary.

        Returns
        -------
        libvirt.virConnect
            connection to libvirt.

        """
        return self.__connection

    @connection.setter
    def connection(self, value):
        self.__connection = value
