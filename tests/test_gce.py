import buttlib.gce
import pytest
import yaml
import random
import string


##
#  Order matters in all this
##
class TestGCE():
    TEST_CLUSTER_KEY = 'noenv:buttbuildertest'

    def setup_class(self):
        print("Setup")
        with open("tests/cluster.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args[TestGCE.TEST_CLUSTER_KEY]
        self.client = buttlib.gce.GCEClient(region=self.args['region'], project=self.args['project'])
        self.modifier = ''.join([random.choice(string.ascii_lowercase + string.digits) for n in range(10)])
        self.args['test_network_name'] = "buttbuildertest-net-{}".format(self.modifier)
        self.args['test_subnetwork_name'] = "buttbuildertest-subnet-{}-01".format(self.modifier)
        self.args['test_group_name'] = "buttbuildertest-group-{}".format(self.modifier)
        self.args['test_instance_name'] = "buttbuildertest-instance-{}".format(self.modifier)
        self.args['test_zone'] = "us-central1-a"

    # tests for gce.regions
    def test_gce_regions_list(self):
        """Test buttlib.gce.regions.list()"""
        result = buttlib.gce.regions.list(self.client)
        assert isinstance(result, dict) and result['kind'] == 'compute#regionList'

    def test_gce_regions_get(self):
        """Test buttlib.gce.regions.get()"""
        result = buttlib.gce.regions.get(self.client)
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#region'

    # tests for gce.images
    def test_gce_images_getFromFamily(self):
        """Test buttlib.gce.regions.get()"""
        result = buttlib.gce.images.getFromFamily(self.client)
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#image'

    # tests for gce.networks
    def test_gce_networks_list(self):
        """Test buttlib.gce.networks.list()"""
        result = buttlib.gce.networks.list(self.client)
        print(result)
        assert isinstance(result, list)

    def test_gce_networks_create(self):
        """Test buttlib.gce.networks.create()"""
        result = buttlib.gce.networks.create(self.client, self.args['test_network_name'])
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#network' and result['name'] == self.args['test_network_name']

    def test_gce_networks_get(self):
        """Test buttlib.gce.networks.get()"""
        result = buttlib.gce.networks.get(self.client, self.args['test_network_name'])
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#network' and result['name'] == self.args['test_network_name']

    def test_gce_subnetworks_list(self):
        """Test buttlib.gce.subnetworks.list()"""
        result = buttlib.gce.subnetworks.list(self.client)
        print(result)
        assert isinstance(result, list)

    def test_gce_subnetworks_create(self):
        """Test buttlib.gce.networks.create()"""
        network = buttlib.gce.networks.get(self.client, self.args['test_network_name'])
        result = buttlib.gce.subnetworks.create(self.client, self.args['test_subnetwork_name'], self.args['externalNet'], network['selfLink'])
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#subnetwork' and result['ipCidrRange'] == '10.254.0.0/24'

    def test_gce_subnetworks_get(self):
        """Test buttlib.gce.subnetworks.get()"""
        result = buttlib.gce.subnetworks.get(self.client, self.args['test_subnetwork_name'])
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#subnetwork' and result['name'] == self.args['test_subnetwork_name']

    # tests for gce.instanceGroups
    def test_gce_instance_groups_list(self):
        """Test buttlib.gce.instance_groups.list()"""
        region_info = buttlib.gce.regions.get(self.client)
        for zone in region_info['zones']:
            self.client.zone = (zone.split("/")[-1]).strip()
            result = buttlib.gce.instance_groups.list(self.client)
            print(result)
            assert isinstance(result, list)
            for group in result:
                assert group['kind'] == 'compute#instanceGroup'

    def test_gce_instance_groups_get(self):
        """Test buttlib.gce.instance_groups.get()"""
        self.client.zone = self.args['test_zone']
        result = buttlib.gce.instance_groups.get(self.client, self.args['test_group_name'])
        print(result)
        assert isinstance(result, dict)

    def test_gce_instance_groups_create(self):
        """Test buttlib.gce.instance_groups.create()"""
        self.client.zone = self.args['test_zone']
        network = buttlib.gce.networks.get(self.client, self.args['test_network_name'])
        result = buttlib.gce.instance_groups.create(self.client, self.args['test_group_name'], network['selfLink'])
        print(result)
        assert isinstance(result, dict)

    def test_gce_instances_list(self):
        """Test buttlib.gce.instances.list()"""
        result = buttlib.gce.instances.list(self.client)
        print(result)
        assert isinstance(result, list)

    # tests for instances
    def test_gce_instances_get(self):
        """Test buttlib.gce.instances.get()"""
        self.client.zone = self.args['test_zone']
        result = buttlib.gce.instances.get(self.client, self.args['test_instance_name'])
        print(result)
        assert isinstance(result, dict) and result == {}

    def test_gce_create_instance(self):
        image = buttlib.gce.images.getFromFamily(self.client)
        subnetwork = buttlib.gce.subnetworks.get(self.client, self.args['test_subnetwork_name'])
        ib = buttlib.gce.InstanceBody()
        self.client.zone = self.args["test_zone"]
        ib.set_name(self.args["test_instance_name"])
        ib.set_machine_type(self.client.zone, self.args['masters']['machineType'])
        ib.set_interface(subnetwork['selfLink'])
        ib.set_disk(self.client.zone, image['selfLink'])
        result = buttlib.gce.instances.create(self.client, ib.__dict__)
        print(result)
        assert isinstance(result, dict) and result['kind'] == 'compute#instance' and result['name'] == self.args["test_instance_name"]

    def test_instance_delete(self):
        result = buttlib.gce.instances.delete(self.client, self.args["test_instance_name"])
        print(result)
        assert isinstance(result, dict) and result == {}

    # clean up
    def test_gce_instance_groups_delete(self):
        self.client.zone = self.args['test_zone']
        result = buttlib.gce.instance_groups.delete(self.client, self.args['test_group_name'])
        print(result)
        assert isinstance(result, dict) and result == {}

    def test_gce_subnetworks_delete(self):
        """Test buttlib.gce.subnetworks.delete()"""
        result = buttlib.gce.subnetworks.delete(self.client, self.args['test_subnetwork_name'])
        print(result)
        assert isinstance(result, dict) and result == {}

    def test_gce_networks_delete(self):
        """Test buttlib.gce.networks.delete()"""
        result = buttlib.gce.networks.delete(self.client, self.args['test_network_name'])
        print(result)
        assert isinstance(result, dict) and result == {}
