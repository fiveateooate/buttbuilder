"""use api functions to do more neat things"""

import buttlib


def used_ips(client, network_url):
    instances = buttlib.gce.instances.list(client)
    for instance in instances:
        print(instance)
