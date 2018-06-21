""" Exception classes for buttlib
"""


class IncompleteEnvironmentSetup(Exception):
    """ Exception I think is unused, I should delete it """

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


class DoNotDestroyCluster(KeyError):
    """ Exception thorwn if user chooses to not destroy cluster """

    def __init__(self, value):
        KeyError.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class TemplateNotFoundError(Exception):
    """ Exception for error finding proxmox template """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class ClusterExistsError(Exception):
    """ Exception for when building cluster
    instances to be created are found
    """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class MissingCredentialsError(Exception):
    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)
