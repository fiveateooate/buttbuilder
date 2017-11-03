import buttlib
import pytest
import yaml
import string
import libvirt
import os
import time


##
#  Order matters in all this
##
class TestLibvirtStorage():
    def setup_class(self):
        with open("tests/cluster-libvirt.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.client = buttlib.libvirt.LibvirtClient(libvirt_uri=self.args['libvirtURI'])
        self.args['cluster_name'] = "buttbuildertest-noenv"
        self.args['storage_config'] = {"name": "buttbuildertest-noenv-pool", "path": "/tmp/buttbuildertest-noenv", "autostart": True}
        if not os.path.exists(self.args['storage_config']['path']):
            os.makedirs(self.args['storage_config']['path'])

    def test_storage_get_default(self):
        result = buttlib.libvirt.storage.get(self.client, 'default')
        print(result)
        assert result is not None

    def test_storage_get(self):
        result = buttlib.libvirt.storage.get(self.client, self.args['cluster_name'])
        print(result)
        assert result is None

    def test_storage_list(self):
        result = buttlib.libvirt.storage.list(self.client)
        print(result)
        assert isinstance(result, list) and isinstance(result[0], libvirt.virStoragePool)

    def test_storage_create(self):
        result = buttlib.libvirt.storage.create(self.client, self.args['storage_config'])
        print(result)
        assert isinstance(result, libvirt.virStoragePool)

    def test_storage_delete(self):
        result = buttlib.libvirt.storage.delete(self.client, self.args['storage_config']['name'])
        print(result)
        assert result is True


class TestLibvirtVolumes():
    def setup_class(self):
        with open("tests/cluster-libvirt.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.client = buttlib.libvirt.LibvirtClient(libvirt_uri=self.args['libvirtURI'])
        self.args['cluster_name'] = "buttbuildertest-noenv"
        self.args['storage_config'] = {"name": "buttbuildertest-noenv-pool", "path": "/tmp/buttbuildertest-noenv", "autostart": True}
        self.args['image_name'] = "host-" + self.args['cluster_name'] + "-01.img"
        self.args['image_full_path'] = self.args['storage_config']['path'] + "/" + self.args['image_name']
        self.args['base_image'] = "coreos_production_qemu_image.img"
        if not os.path.exists(self.args['storage_config']['path']):
            os.makedirs(self.args['storage_config']['path'])
        self.pool = buttlib.libvirt.storage.create(self.client, self.args['storage_config'])
        self.default_pool = buttlib.libvirt.storage.get(self.client, 'default')
        buttlib.common.fetch_coreos_image(os.getcwd())

    # def teardown_class(self):
    #     buttlib.libvirt.storage.delete(self.client, self.args['storage_config']['name'])

    def test_volume_list_default(self):
        result = buttlib.libvirt.volumes.list(self.client, self.default_pool)
        print(result)
        assert result is not None

    def test_volume_list(self):
        result = buttlib.libvirt.volumes.list(self.client, self.pool)
        print(result)
        assert result is not None

    def test_volume_image_upload(self):
        size = os.path.getsize("coreos_production_qemu_image.img")
        print(size)
        volume_config = {"name": self.args['image_name'], "full_path": self.args['image_full_path'], "size": size}
        result = buttlib.libvirt.volumes.import_image(self.client, self.pool, self.args['base_image'], volume_config)
        print(result)
        assert isinstance(result, libvirt.virStorageVol)

    def test_volume_image_resize(self):
        volume_config = {"name": self.args['image_name'], "full_path": self.args['image_full_path'], "size": 20000000000}
        result = buttlib.libvirt.volumes.resize_image(self.client, self.pool, volume_config)
        print(result)
        assert result is True

    def test_volume_get(self):
        result = buttlib.libvirt.volumes.get(self.client, self.pool, self.args['image_name'])
        print(result)
        assert isinstance(result, libvirt.virStorageVol)

    def test_volume_delete(self):
        result = buttlib.libvirt.volumes.delete(self.client, self.pool, self.args['image_name'])
        print(result)
        assert result is True


class TestLibvirtNetworks():
    def setup_class(self):
        with open("tests/cluster-libvirt.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.client = buttlib.libvirt.LibvirtClient(libvirt_uri=self.args['libvirtURI'])
        self.butt_ips = buttlib.common.ButtIps(self.args['externalNet'])
        self.args['cluster_name'] = "buttbuildertest-noenv"
        self.args['network_config'] = {
            "name": self.args['cluster_name'] + "-net",
            "ip": self.butt_ips.get_ip(1),
            "netmask": self.butt_ips.get_netmask(),
            "ip_range_start": self.butt_ips.get_ip(50),
            "ip_range_end": self.butt_ips.get_ip(60),
            "mac": buttlib.common.random_mac(),
            "autostart": True
        }
        self.args['dhcp_config'] = {
            "network_name": self.args['network_config']['name'],
            "ip": self.butt_ips.get_ip(10),
            "mac": buttlib.common.random_mac(),
            "hostname": "host-" + self.args['cluster_name'] + "-01"
        }

    def test_networks_get_default(self):
        result = buttlib.libvirt.networks.get(self.client, 'default')
        print(result)
        assert result is not None

    def test_networks_get(self):
        result = buttlib.libvirt.networks.get(self.client, self.args['network_config']['name'])
        print(result)
        assert result is None

    def test_networks_list(self):
        result = buttlib.libvirt.networks.list(self.client)
        print(result)
        assert isinstance(result, list) and isinstance(result[0], libvirt.virNetwork)

    def test_networks_create(self):
        result = buttlib.libvirt.networks.create(self.client, self.args['network_config'])
        print(result)
        assert isinstance(result, libvirt.virNetwork)

    def test_networks_dhcp_add(self):
        result = buttlib.libvirt.networks.dhcp_add(self.client, self.args['dhcp_config'])
        print(result)
        assert result is True

    def test_networks_dhcp_delete(self):
        result = buttlib.libvirt.networks.dhcp_delete(self.client, self.args['dhcp_config'])
        print(result)
        assert result is True

    def test_networks_delete(self):
        result = buttlib.libvirt.networks.delete(self.client, self.args['network_config']['name'])
        print(result)
        assert result is True
