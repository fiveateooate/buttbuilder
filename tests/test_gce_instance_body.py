import buttlib.gce
import pytest
import yaml
import json


##
#  Order matters in all this
##
class TestGCE():
    TEST_CLUSTER_KEY = 'noenv:buttbuildertest'

    def setup_class(self):
        print("Setup")
        with open("tests/cluster-gce.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args[TestGCE.TEST_CLUSTER_KEY]
        self.args['test_subnetwork_url'] = "https://www.googleapis.com/compute/v1/projects/weave-lab/regions/us-central1/subnetworks/buttbuildertest-subnet-xzhmmlp603-01"
        self.args['test_instance_name'] = "buttbuildertest-instance"
        self.args['test_zone'] = "us-central1-a"
        self.args['test_image'] = "https://www.googleapis.com/compute/v1/projects/coreos-cloud/global/images/coreos-stable-1520-8-0-v20171026"
        self.args['test_machine_type'] = "m1-small"

    # tests for instances
    def test_gce_instance_body(self):
        ib = buttlib.gce.InstanceBody(name=self.args["test_instance_name"], machine_type=self.args['test_machine_type'],
                                      zone=self.args['test_zone'], image=self.args['test_image'], subnetwork_url=self.args['test_subnetwork_url'])
        json_ib = ib.json()
        redict_ib = json.loads(json_ib)
        print(json_ib)
        print(redict_ib)
        assert ib.__dict__ == redict_ib
