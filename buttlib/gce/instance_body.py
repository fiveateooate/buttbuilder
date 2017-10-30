"""
instance body was complex enough to warrant this?
https://cloud.google.com/compute/docs/reference/latest/instances#resource
"""

import json


class InstanceBody(object):
    def __init__(self, name="", machine_type="", zone="", image="", subnetwork_url="", disk_size=""):
        # both name and machineType should be set
        self.name = name
        self.machineType = "zones/{zone}/machineTypes/{type}".format(zone=zone, type=machine_type)
        # needs some user-data format - {"key: "user-data", "value": "blah blah" } added to items[]
        self.metadata = {
            "items": []
        }
        # nothing needs to be added
        self.serviceAccounts = [{
            "email": "default",
            "scopes": [
                "https://www.googleapis.com/auth/devstorage.read_write",
                "https://www.googleapis.com/auth/logging.write"
            ]
        }]
        # sourceImage and diskType need to be set
        self.disks = [{
            "name": "boot",
            "boot": True,
            "autoDelete": True,
            "initializeParams": {
                "sourceImage": "/".join(image.split("/")[-3:]),
                "diskType": "zones/{zone}/diskTypes/pd-ssd".format(zone=zone),
                "diskSizeGb": disk_size
            }
        }]
        # network and networkIP need to be set
        self.networkInterfaces = [{
            "subnetwork": subnetwork_url,
            "name": "interface0",
            "accessConfigs": [{
                "kind": "compute#accessConfig",
                "type": "ONE_TO_ONE_NAT",
                "name": "External NAT"
            }],
            # "networkIP": ""
        }]

    def __clean_metadata(self, some_dict):
        for i in range(len(self.metadata["items"])):
            if self.metadata["items"][i].get("key") == some_dict["key"]:
                self.metadata["items"].pop(i)

    def add_metadata(self, some_metadata):
        if not isinstance(some_metadata, dict):
            raise ValueError
        self.__clean_metadata(some_metadata)
        self.metadata["items"].append(some_metadata)

    def set_name(self, name):
        self.name = name

    def set_machine_type(self, zone, machine_type):
        self.machineType = "zones/{zone}/machineTypes/{type}".format(zone=zone, type=machine_type)

    def set_userdata(self, userdata):
        if not isinstance(userdata, str):
            raise ValueError
        ud = {"key": "user-data", "value": userdata}
        self.__clean_metadata(ud)
        self.metadata["items"].append(ud)

    def set_disk(self, zone, image):
        self.disks[0]["initializeParams"]["sourceImage"] = "/".join(image.split("/")[-5:])
        self.disks[0]["initializeParams"]["diskType"] = "zones/{zone}/diskTypes/pd-ssd".format(zone=zone)

    def set_interface(self, subnetwork_url):
        self.networkInterfaces[0]["subnetwork"] = subnetwork_url
        # self.networkInterfaces[0]["networkIP"] = ip_address

    def json(self):
        return json.dumps(self.__dict__)
