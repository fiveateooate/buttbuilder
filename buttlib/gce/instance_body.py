"""
instance body was complex enough to warrant this?
https://cloud.google.com/compute/docs/reference/latest/instances#resource
"""


class InstanceBody(object):
    def __init__(self):
        self.name = ""
        self.machineType = ""
        self.metadata = {
            "items": []
        }
        self.serviceAccounts = [{
            "email": "default",
            "scopes": [
                "https://www.googleapis.com/auth/devstorage.read_write",
                "https://www.googleapis.com/auth/logging.write"
            ]
        }]
        self.disks = [{
            "name": "boot",
            "boot": True,
            "autoDelete": True,
            "initializeParams": {
                "sourceImage": "",
                "diskType": ""
            }
        }]
        self.networkInterfaces = [{
            "network": "",
            "name": "interface0",
            "accessConfigs": [{
                "kind": "compute#accessConfig",
                "type": "ONE_TO_ONE_NAT",
                "name": "External NAT"
            }],
            "networkIP": ""
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

    def set_userdata(self, userdata):
        if not isinstance(userdata, str):
            raise ValueError
        ud = {"key": "user-data", "value": userdata}
        self.__clean_metadata(ud)
        self.metadata["items"].append(ud)

    def set_ip(self, ip_address):
        self.networkInterfaces[0]["networkIP"] = ip_address

    def set_network(self, network):
        self.networkInterfaces[0]["network"] = network
