"""reads keys from ~/.ssh to use in butt config"""

import re
import os

class SSHKeyHelper():
    """reads in rsa/dsa/ed25519 public keys for use in butt config"""
    def __init__(self):
        self.__ssh_key_dir = "%s/.ssh/"%(os.path.expanduser("~"))
        self.__ssh_pub_keys = self.read_public_keys()

    def read_public_keys(self):
        """ read pub keys of type rsa, dsa, or ed25519 for use in user_data"""
        ssh_pub_keys = []
        pattern = re.compile(r'^.*_(ras|dsa|ed25519).*.pub$')
        for key in [key for key in os.listdir(self.__ssh_key_dir) if re.search(pattern, key)]:
            with open("%s/%s"%(self.__ssh_key_dir, key), 'r') as file:
                ssh_pub_keys.append(file.read())
        return ssh_pub_keys

    def get_pub_keys(self):
        """:returns: pub keys in string formatted for user_data"""
        pub_key_str = ""
        for pub_key in self.__ssh_pub_keys:
            pub_key_str += " - {pub_key}".format(pub_key=pub_key)
        return pub_key_str
