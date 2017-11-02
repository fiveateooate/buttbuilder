"""exceptions used in buttbuilder"""


class LibVirtConnectionError(Exception):
    """ raise if libvirt connection fails """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class MissingEnvVarsError(KeyError):
    """ Raise if required env vars are not set """

    def __init__(self, value):
        KeyError.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class UnknownRoleError(KeyError):
    """ Raise if someone is trying to use a weird role"""

    def __init__(self, value):
        KeyError.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)
