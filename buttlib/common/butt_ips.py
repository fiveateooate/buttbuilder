"""do stuff with ip addresses"""

import ipaddress
import random


class ButtIps():
    """do stuff with ips for butts"""

    def __init__(self, network, subnet_mask=24, subnet_offset=0):
        self.__network = network
        self.__subnet_mask = subnet_mask
        self.__subnet_offset = subnet_offset

    def get_network(self):
        return ipaddress.IPv4Network(self.__network)

    def get_netmask(self):
        return ipaddress.IPv4Network(self.__network).netmask

    def get_subnets(self):
        """:returns: list of subnets broken on subnet_mask"""
        return list(ipaddress.IPv4Network(self.__network).subnets(new_prefix=self.__subnet_mask))

    def get_ip(self, index):
        """:returns: string - ip adderss within network"""
        __subnet = self.get_subnets()[self.__subnet_offset]
        return str(ipaddress.IPv4Network(__subnet)[index])

    def get_random_ip(self):
        """:returns: string - random ip adderss within network"""
        __subnet = self.get_subnets()[self.__subnet_offset]
        num = random.randint(1, 254)
        return str(ipaddress.IPv4Network(__subnet)[num])

    def get_gateway(self):
        return str(ipaddress.IPv4Network(self.__network)[1])

    def get_cidr(self):
        return (self.__network.split("/"))[-1]
