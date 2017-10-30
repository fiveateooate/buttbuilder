#!/usr/bin/env python3

import pytest
import buttlib
import yaml
import ipaddress


class TestButtIPs():
    def setup(self):
        with open("tests/cluster.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.butt_ips = buttlib.common.ButtIps(network=self.args['externalNet'])

    def test_get_network(self):
        result = self.butt_ips.get_network()
        print(result)
        assert isinstance(result, ipaddress.IPv4Network)

    def test_subnet_get(self):
        result = self.butt_ips.get_subnets()
        print(result)
        assert isinstance(result, list) and len(result) == 1 and isinstance(result[0], ipaddress.IPv4Network)

    def test_get_ip(self):
        ip = self.butt_ips.get_ip(5)
        print(ip)
        assert ip == '10.254.0.5'

    def test_get_random_ip(self):
        ip = ipaddress.ip_address(self.butt_ips.get_random_ip())
        print(ip)
        assert isinstance(ip, ipaddress.IPv4Address) and ip in self.butt_ips.get_network()
