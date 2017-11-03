""" builder class for libvirt
"""
# import ipaddress
import os
# import stat
# import random
# import subprocess
# import tempfile
import libvirt
import yaml
import buttlib


class Builder(buttlib.common.ButtBuilder):
    def __init__(self, env_info, args):
        print("NOTE: sudo will be used to interact with libvirt")
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        # self.__libvirt_uri = env_info['libvirtURI']
        # self._cluster_info['network_name'] = "%s-net" % (self._cluster_info['cluster_name'])
        self.__client = buttlib.libvirt.LibvirtClient(env_info['libvirtURI'])
        # self.__coreos_image_name_zipped = "coreos_production_qemu_image.img.bz2"
        # self.__coreos_image_name = "coreos_production_qemu_image.img"
        # add some libvirt specific crap
        self._cluster_info.update({
            "image_type": "qcow2",
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
        # for hostname, ip in self._kube_workers.workers:
        #     bic = buttlib.common.ButtInstanceConfig(hostname, ip, 'workers', self._ssl_helper, self._env_info, self._cluster_info['kube_master_lb_ip'])
        #     print(bic.instance_config)
        #     self.create_vm(vm_config, 'worker')

    # def generate_master_config(self, hostname, ip):
    #     self._ssl_helper.generateHost(hostname, ip)
    #     vm_config = {
    #         "hostname": hostname,
    #         "mac": buttlib.common.random_mac(),
    #         "ip": ip,
    #         "disk": self._env_info['masters']['disk'],
    #         "butt_net": self._cluster_info['network_name'],
    #         "butt_dir": self._cluster_info['buttdir'],
    #         "ram": self._env_info['masters']['ram'],
    #         "libvirt_uri": self.__libvirt_uri,
    #         "cpus": self._env_info['masters']['cpus'],
    #         "kubeletRegistration": "--register-with-taints=node.alpha.kubernetes.io/ismaster=:NoSchedule",
    #         "clusterRole": "master",
    #         "additionalLabels": "",
    #         "etcdProxy": "off",
    #         "exclude_modules": [
    #             "etcd-gateway"
    #         ],
    #         "kubeAPIServer": "http://127.0.0.1:8080",
    #         "host_pem": self._ssl_helper.getInfo()["{}_pem".format(hostname)],
    #         "host_key": self._ssl_helper.getInfo()["{}_key".format(hostname)],
    #         "api_pem": self._ssl_helper.getInfo()["api_pem"],
    #         "api_key": self._ssl_helper.getInfo()["api_key"],
    #         "ca_pem": self._ssl_helper.getInfo()["ca_pem"],
    #         "ca_key": self._ssl_helper.getInfo()["ca_key"]
    #     }
    #     return vm_config

    # def generate_worker_config(self):
    #     """ return a dict with config for a worker vm"""
    #     hostname = "kube-worker-{}-{}".format(
    #         self._cluster_info['cluster_name'], buttlib.common.random_hostname_suffix())
    #     host_ip = self.get_random_worker_ip()
    #     self._ssl_helper.generateHost(hostname, host_ip)
    #     vm_config = {
    #         'hostname': hostname,
    #         "mac": self.random_mac(),
    #         "ip": host_ip,
    #         "disk": self._env_info['workers']['disk'],
    #         "butt_net": self._cluster_info['network_name'],
    #         "butt_dir": self._cluster_info['buttdir'],
    #         "ram": self._env_info['workers']['ram'],
    #         "libvirt_uri": self.__libvirt_uri,
    #         "cpus": self._env_info['workers']['cpus'],
    #         "kubeletRegistration": "--register-node=true",
    #         "clusterRole": "worker",
    #         "additionalLabels": "",
    #         "etcdProxy": "on",
    #         "kubeAPIServer": "https://{}:443".format(self._cluster_info['kube_master']),
    #         "exclude_modules": [
    #             "kube-apiserver",
    #             "kube-controller-manager",
    #             "addon-manager",
    #             "kube-scheduler",
    #             "etcd"
    #         ],
    #         "host_pem": self._ssl_helper.getInfo()["{}_pem".format(hostname)],
    #         "host_key": self._ssl_helper.getInfo()["{}_key".format(hostname)],
    #         "api_pem": self._ssl_helper.getInfo()["api_pem"],
    #         "api_key": self._ssl_helper.getInfo()["api_key"],
    #         "ca_pem": self._ssl_helper.getInfo()["ca_pem"],
    #         "ca_key": self._ssl_helper.getInfo()["ca_key"]
    #     }
    #     return vm_config

    # def generate_vm_configs(self):
    #     """ returns list of dicts used to configure indvidual virtual machines
    #         uses parameters read from a yaml file
    #     """
    #     vms = {"masters": [], "workers": []}
    #     # for i in range(self._env_info['masters']['nodes']):
    #     #    vms['masters'].append(self.generate_master_config(i))
    #     for i in range(self._env_info['workers']['nodes']):
    #         vms['workers'].append(self.generate_worker_config())
    #     return vms

    # def get_random_worker_ip(self):
    #     """:reutrns: string random ip within range"""
    #     done = False
    #     random_ip = ""
    #     while not done:
    #         random_ip = ipaddress.IPv4Network(self._env_info['externalNet'])[
    #             random.randrange(self._worker_ip_offset, 250)]
    #         if random_ip not in self.get_used_ips():
    #             done = True
    #     return random_ip
    #
    # def get_used_ips(self):
    #     """:returns: list - ips found in libvirt network config"""
    #     result = subprocess.run(
    #         ["sudo", "virsh", "net-dhcp-leases", self._cluster_info['network_name']],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #     # yeah this is fecked but yeah i don't know ...
    #     return [(line.split()[4]).split("/")[0]
    #             for line in result.stdout.split("\n")[2:-2]]

    # def add_dhcp_entry(self, vm_config):
    #     """adds a dhcp assignement to libvirt network"""
    #     dhcp_xml = "<host mac='%s' name='%s' ip='%s' />" % (
    #         vm_config['mac'], vm_config['hostname'], vm_config['ip'])
    #     subprocess.run(
    #         [
    #             "sudo", "virsh", "net-update", self._cluster_info['network_name'], "add",
    #             "ip-dhcp-host", dhcp_xml, "--live"
    #         ],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #
    # def delete_dhcp_entry(self, vm_name):
    #     """delete dhcp assignement from libvirt network"""
    #     dhcp_xml = "<host name='{}' />".format(vm_name)
    #     subprocess.run(
    #         [
    #             "sudo", "virsh", "net-update", self._cluster_info['network_name'], "delete",
    #             "ip-dhcp-host", dhcp_xml, "--live"
    #         ],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)

    # def create_volume(self, vm_config):
    #     """ Expects configuration dict for a virtual machines
    #         uses subprocess and qemu-img to create and resize an image"""
    #     result = subprocess.run(
    #         [
    #             "qemu-img", "create", "-f", "qcow2", "-b",
    #             "%s/%s" % (self._cluster_info['buttdir'],
    #                        self.__coreos_image_name),
    #             "%s/%s.qcow2" % (self._cluster_info['buttdir'],
    #                              vm_config['hostname'])
    #         ],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #     print(result.stdout)
    #     if vm_config['disk'] > 8:
    #         size = vm_config['disk'] - 8
    #         result = subprocess.run(
    #             [
    #                 "sudo", "qemu-img", "resize",
    #                 "%s/%s.qcow2" % (self._cluster_info['buttdir'],
    #                                  vm_config['hostname']),
    #                 "+%iG" % (size)
    #             ],
    #             stdout=subprocess.PIPE,
    #             universal_newlines=True)
    #         print(result.stdout)

    # def create_user_data(self, vm_config, vm_role):
    #     """Creates and writes out user data specific to given vm config"""
    #     uddir = "%s/%s/openstack/latest" % (self._cluster_info['buttdir'],
    #                                         vm_config['hostname'])
    #     if not os.path.exists(uddir):
    #         os.makedirs(uddir)
    #     ud_dict = {
    #         "kube_addons": yaml.dump(self._cluster_info['kube_addons']) % {
    #             **
    #             vm_config,
    #             **
    #             self._env_info,
    #             **
    #             self._cluster_info
    #         },
    #         "kube_manifests":
    #         yaml.dump(self._cluster_info['kube_manifests'][vm_role]) % {
    #             **
    #             vm_config,
    #             **
    #             self._env_info,
    #             **
    #             self._cluster_info
    #         },
    #     }
    #     with open("%s/user_data" % (uddir), 'w') as file:
    #         file.write(self._cluster_info['user_data_tmpl'][vm_role] %
    #                    {**vm_config, **self._env_info,
    #                     **self._cluster_info,
    #                     **(self._ssl_helper.getInfo()),
    #                     **ud_dict})

    # def create_storage_pool(self):
    #     """ create a libvirt storage pool"""
    #     try:
    #         self.__client.connection.storagePoolLookupByName(self.__buttpool)
    #         print("Storage pool exists")
    #     except libvirt.libvirtError:
    #         print("Creating storage pool %s" % self.__buttpool)
    #         result = subprocess.run(
    #             [
    #                 "sudo", "virsh", "pool-define-as", "--type=dir",
    #                 "--name=%s" % (self.__buttpool),
    #                 "--target=%s" % (self._cluster_info['buttdir'])
    #             ],
    #             stdout=subprocess.PIPE,
    #             universal_newlines=True)
    #         if result.returncode == 0:
    #             subprocess.run(
    #                 [
    #                     "sudo", "virsh", "pool-start", "--pool",
    #                     "%s" % (self.__buttpool)
    #                 ],
    #                 stdout=subprocess.PIPE,
    #                 universal_newlines=True)
    #             storage_pool = self.__client.connection.storagePoolLookupByName(self.__buttpool)
    #             storage_pool.setAutostart(1)
    #             print("Storage pool created")

    # def create_butt_network(self, __vm_initial_configs):
    #     """ create libvirt network including dhcp setup"""
    #     if [
    #             net for net in self.__client.connection.listNetworks()
    #             if net == self._cluster_info['network_name']
    #     ] != []:
    #         # network = self.__client.connection.networkLookupByName(self._cluster_info['network_name'])
    #         print("Destroying Network")
    #         subprocess.run(
    #             ["sudo", "virsh", "net-destroy",
    #              "%s" % self._cluster_info['network_name']],
    #             stdout=subprocess.PIPE,
    #             universal_newlines=True)
    #         subprocess.run(
    #             ["sudo", "virsh", "net-undefine",
    #              "%s" % self._cluster_info['network_name']],
    #             stdout=subprocess.PIPE,
    #             universal_newlines=True)
    #     print("Creating network %s" % (self._cluster_info['network_name']))
    #     dhcp_setup = ""
    #     for master in __vm_initial_configs['masters']:
    #         dhcp_setup += "<host mac='%s' name='%s' ip='%s'/>\n" % (
    #             master['mac'], master['hostname'], master['ip'])
    #     for worker in __vm_initial_configs['workers']:
    #         dhcp_setup += "<host mac='%s' name='%s' ip='%s'/>\n" % (
    #             worker['mac'], worker['hostname'], worker['ip'])
    #     iprange = list(
    #         ipaddress.IPv4Network(self._env_info['externalNet']).hosts())
    #     xml = Builder.__LIBVIRT_NETWORK_TMPLT__ % (
    #         self._cluster_info['network_name'], self._cluster_info['network_name'][:5], self.random_mac(), iprange[-1],
    #         (ipaddress.IPv4Network(self._env_info['externalNet'])).netmask,
    #         iprange[0], iprange[-2], dhcp_setup)
    #     temp_file = tempfile.NamedTemporaryFile()
    #     temp_file.write(xml.encode('utf-8'))
    #     temp_file.seek(0)
    #     subprocess.run(
    #         ["sudo", "virsh", "net-define",
    #          "%s" % temp_file.name],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #     temp_file.close()
    #     subprocess.run(
    #         ["sudo", "virsh", "net-start",
    #          "%s" % self._cluster_info['network_name']],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)
    #     subprocess.run(
    #         ["sudo", "virsh", "net-autostart",
    #          "%s" % self._cluster_info['network_name']],
    #         stdout=subprocess.PIPE,
    #         universal_newlines=True)

    # def get_next_hostname(self):
    #     """ figure out the next hostname from what is running"""
    #     for domain in self.__client.connection.listAllDomains():
    #         print(domain.name())

    def add_node(self):
        """add a node to existing kubernetes cluster"""
        __vm_config = self.generate_worker_config()
        self.add_dhcp_entry(__vm_config)
        self.create_vm(__vm_config, 'worker')

    @staticmethod
    def delete_vm(vm_name):
        """deletes a vm from libvirt"""
        subprocess.run(
            ["sudo", "virsh", "destroy", vm_name],
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            ["sudo", "virsh", "undefine", vm_name],
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def remove_node(self, vm_name):
        """deletes vm from libvirt and libvirt network"""
        self.delete_vm(vm_name)
        self.delete_dhcp_entry(vm_name)

    def delete_node(self, node):
        """delete named node from kubernetes cluster"""
        pass

    def destroy(self):
        """tear down entire cluster"""
        # should ever do???????
        # self.deleteStorage()
        pass
