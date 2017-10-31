import buttlib.libvirt
import pytest
import yaml
import random
import string
import libvirt
import os


##
#  Order matters in all this
##
class TestLibvirt():
    def setup_class(self):
        with open("tests/cluster-libvirt.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.client = buttlib.libvirt.LibvirtClient(libvirt_uri=self.args['libvirtURI'])
        self.modifier = ''.join([random.choice(string.ascii_lowercase + string.digits) for n in range(10)])
        self.args['cluster_name'] = "buttbuildertest-noenv"
        self.args['pool_name'] = "buttbuildertest-noenv-pool"
        self.args['pool_path'] = "/tmp/buttbuildertest-noenv"
        if not os.path.exists(self.args['pool_path']):
            os.makedirs(self.args['pool_path'])

    def test_storage_get_default(self):
        result = buttlib.libvirt.storage.get(self.client, 'default')
        print(result)
        assert result is not None

    def test_storage_get(self):
        result = buttlib.libvirt.storage.get(self.client, self.args['cluster_name'])
        print(result)
        assert isinstance(result, list)

    def test_storage_list(self):
        result = buttlib.libvirt.storage.list(self.client)
        print(result)
        assert isinstance(result, list) and isinstance(result[0], libvirt.virStoragePool)

    def test_storage_create(self):
        storage_config = {"name": self.args['pool_name'], "path": self.args['pool_path'], "autostart": True}
        result = buttlib.libvirt.storage.create(self.client, storage_config)
        print(result)
        assert isinstance(result, libvirt.virStoragePool)
