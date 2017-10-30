"""exceptions used in buttbuilder"""


class LibVirtConnectionError(Exception):
    """ raise if libvirt connection fails """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)
