#!/usr/bin/env python3

import sys
import os
# goofyness to get import working
sys.path.append(os.getcwd())

import pprint

import buttlib

def main():
    pp = pprint.PrettyPrinter()
    butt_ips = buttlib.common.ButtIps(network="10.128.0.0/20", subnet_offset=1)
    pp.pprint(butt_ips.get_subnets())
    pp.pprint(butt_ips.get_ip(12))
    pp.pprint(butt_ips.get_random_ip())

    moar_ips = buttlib.common.ButtIps(network="191.168.0.0/24")
    pp.pprint(moar_ips.get_subnets())
    pp.pprint(moar_ips.get_ip(12))
    pp.pprint(moar_ips.get_random_ip())

if __name__ == "__main__":
    main()
