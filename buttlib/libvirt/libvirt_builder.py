""" builder class for libvirt
"""
import os
import libvirt
import yaml
import buttlib


class Builder(buttlib.common.ButtBuilder):
    def __init__(self, env_info, args):
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        self.__client = buttlib.libvirt.LibvirtClient(env_info['libvirtURI'])
        # add some libvirt specific crap
        self._cluster_info.update({
            "image_type": args.image_format,
            'network_config': {
                "name": self._cluster_info['cluster_name'] + "-net",
                "ip": self._butt_ips.get_ip(1),
                "netmask": self._butt_ips.get_netmask(),
                "ip_range_start": self._butt_ips.get_ip(2),
                "ip_range_end": self._butt_ips.get_ip(254),
                "mac": buttlib.common.random_mac(),
                "autostart": True
            },
            'storage_pool_config': {
                "name": self._cluster_info['cluster_name'] + "-pool",
                "path": self._cluster_info['buttdir'],
                "autostart": True
            },
            'kube_master_lb_ip': self._butt_ips.get_ip(self._cluster_info['ip_offset']['masters']),
            'base_image': self._cluster_info['buttdir'] + "/" + "coreos_production_qemu_image.img"
        })
        self.__storage_pool = None
        self.__network = None

    def __pre_build(self):
        # probably do some checking exists stuff
        # gen admin and api certs
        self._ssl_helper.create_or_load_certs(self._kube_masters.ips, self._cluster_info["cluster_ip"], self._kube_masters.hostnames)
        # fetch the base image
        buttlib.common.fetch_coreos_image(self._cluster_info['buttdir'], self._env_info['coreosChannel'])
        # create the storage pool
        if not buttlib.libvirt.storage.exists(self.__client, self._cluster_info['storage_pool_config']['name']):
            self.__storage_pool = buttlib.libvirt.storage.create(self.__client, self._cluster_info['storage_pool_config'])
        else:
            self.__storage_pool = buttlib.libvirt.storage.get(self.__client, self._cluster_info['storage_pool_config']['name'])
        # create the network
        if not buttlib.libvirt.networks.exists(self.__client, self._cluster_info['network_config']['name']):
            self.__network = buttlib.libvirt.networks.create(self.__client, self._cluster_info['network_config'])
        else:
            self.__network = buttlib.libvirt.networks.get(self.__client, self._cluster_info['network_config']['name'])

    def __create_volume(self, hostname, size):
        __vol_name = hostname + "." + self._cluster_info['image_type']
        __volume_config = {
            "name": __vol_name,
            "full_path": "{}/{}".format(self._cluster_info['buttdir'], __vol_name),
            "size": os.path.getsize(self._cluster_info['base_image'])
        }
        # create a new volume
        buttlib.libvirt.volumes.import_image(self.__client, self.__storage_pool, self._cluster_info['base_image'], __volume_config)
        # size it correctly
        __final_size = size * 1024000000
        if __final_size > __volume_config['size']:
            __volume_config['size'] = __final_size
            buttlib.libvirt.volumes.resize_image(self.__client, self.__storage_pool, __volume_config)

    def __create_vm(self, instance_config):
        """create a new instance in libvirt"""
        self.__create_volume(instance_config['hostname'], instance_config['disk'])
        __dhcp_config = {
            "network_name": instance_config['network_name'],
            "ip": instance_config['ip'],
            "mac": instance_config['mac'],
            "hostname": instance_config['hostname']
        }
        buttlib.libvirt.networks.dhcp_add(self.__client, __dhcp_config)
        buttlib.libvirt.instances.create(self.__client, instance_config)

    def build(self):
        """Gathers up config and calls various functions to create a kubernetes cluster"""
        self.__pre_build()
        provider_additional = {"image_type": self._cluster_info['image_type']}
        for hostname, ip in self._kube_masters.masters:
            bic = buttlib.common.ButtInstanceConfig(
                hostname,
                ip,
                'masters',
                self._ssl_helper,
                self._env_info,
                self._cluster_info,
                provider_additional=provider_additional
            )
            # write out the config
            bic.write_ign()
            self.__create_vm(bic.instance_config)
        for hostname, ip in self._kube_workers.workers:
            bic = buttlib.common.ButtInstanceConfig(
                hostname,
                ip,
                'workers',
                self._ssl_helper,
                self._env_info,
                self._cluster_info,
                provider_additional=provider_additional
            )
            bic.write_ign()
            self.__create_vm(bic.instance_config)

    # putting verify functions here as they need access to all the configs
    def verify_vms(self):
        for dom in buttlib.libvirt.instances.list(self.__client):
            print("name={}".format(dom.name()))
        return True

    def verify(self):
        print("Checking butt state ... ")
        print("Checking vm's ...")
        self.verify_vms()

    # def add_node(self):
    #     """add a node to existing kubernetes cluster"""
    #     __vm_config = self.generate_worker_config()
    #     self.add_dhcp_entry(__vm_config)
    #     self.create_vm(__vm_config, 'worker')
    #
    # @staticmethod
    # def delete_vm(vm_name):
    #     """deletes a vm from libvirt"""
    #     subprocess.run(
    #         ["sudo", "virsh", "destroy", vm_name],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #     subprocess.run(
    #         ["sudo", "virsh", "undefine", vm_name],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #
    # def remove_node(self, vm_name):
    #     """deletes vm from libvirt and libvirt network"""
    #     self.delete_vm(vm_name)
    #     self.delete_dhcp_entry(vm_name)
    #
    # def delete_node(self, node):
    #     """delete named node cluster"""
    #     pass
    #
    # def destroy(self):
    #     """tear down entire cluster"""
    #     # should ever do???????
    #     # self.deleteStorage()
    #     pass
