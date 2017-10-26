""" builder class for libvirt
"""
import ipaddress
import os
import subprocess
import tempfile
import random
import libvirt
import yaml

import buttlib

class Builder(buttlib.common.ButtBuilder):
    """ Libvrit module for buttbuilder """
    __LIBVIRT_CREATE_TMPLT__ = """
    virt-install --connect %(libvirt_host)s \
      --import \
      --name %(hostname)s \
      --ram %(ram)s \
      --vcpus %(cpus)s \
      --os-type=linux \
      --os-variant=generic \
      --disk path=%(butt_dir)s/%(hostname)s.qcow2,format=qcow2,bus=virtio \
      --filesystem %(butt_dir)s/%(hostname)s,config-2,type=mount,mode=squash \
      --vnc \
      --noautoconsole \
      --network network=%(butt_net)s,model=virtio,mac=%(mac)s"""

    __LIBVIRT_NETWORK_TMPLT__ = """<network>
  <name>%s</name>
  <forward mode='nat'/>
  <bridge name='%sbr0' stp='on' delay='0'/>
  <mac address='%s'/>
  <ip address='%s' netmask='%s'>
    <dhcp>
      <range start='%s' end='%s'/>
      %s</dhcp>
  </ip>
</network>"""

    def __init__(self, env_info, args):
        print("NOTE: sudo will be used to interact with libvirt")
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        self.__libvirt_host = env_info['libvirtHost']
        self.__buttpool = "%s-pool" % (self._cluster_info['cluster_name'])
        self.__buttnet = "%s-net" % (self._cluster_info['cluster_name'])
        self.__ssl_helper = buttlib.helpers.SSLHelper(self._env_info['clusterDomain'], "{}/ssl".format(self._cluster_info['buttdir']))
        self.__libvirt_conn = libvirt.open(self.__libvirt_host)
        if self.__libvirt_conn is None:
            raise buttlib.common.LibVirtConnectionError("Failed to connect to {}".format(self.__libvirt_host))

    def build(self):
        """Gathers up config and calls various functions to create a kubernetes cluster"""
        self.__ssl_helper.createCerts(self.get_master_ips(),
                                      self._cluster_info["cluster_ip"],
                                      self.get_master_hosts())
        __vm_initial_configs = self.generate_vm_config()
        self.fetch_image()
        #self.set_cluster_info(__vm_initial_configs)
        self.create_butt_pool()
        self.create_butt_network(__vm_initial_configs)
        for vm_config in __vm_initial_configs['masters']:
            self.create_vm(vm_config, 'master')
        for vm_config in __vm_initial_configs['workers']:
            self.create_vm(vm_config, 'worker')

    def generate_vm_config(self):
        """ returns list of dicts used to configure indvidual virtual machines
            uses parameters read from a yaml file
        """
        vms = {"masters": [], "workers": []}
        for i in range(self._env_info['masters']['nodes']):
            hostname = "kube-master-%s-%02d" % (self._cluster_info['cluster_name'], i + 1)
            host_ip = str(
                ipaddress.IPv4Network(
                    self._env_info['externalNet'])[i + self._master_ip_offset])
            self.__ssl_helper.generateHost(hostname, host_ip)
            vms['masters'].append({
                "hostname": hostname,
                "mac": self.random_mac(),
                "ip": host_ip,
                "disk": self._env_info['masters']['disk'],
                "butt_net": self.__buttnet,
                "butt_dir": self._cluster_info['buttdir'],
                "ram": self._env_info['masters']['ram'],
                "libvirt_host": self.__libvirt_host,
                "cpus": self._env_info['masters']['cpus'],
                "host_pem": self.__ssl_helper.getInfo()["%s_pem" % hostname],
                "host_key": self.__ssl_helper.getInfo()["%s_key" % hostname]
            })
        for i in range(self._env_info['workers']['nodes']):
            vms['workers'].append(self.generate_worker_config())
        return vms

    def get_random_worker_ip(self):
        """:reutrns: string random ip within range"""
        done = False
        random_ip = ""
        while not done:
            random_ip = ipaddress.IPv4Network(self._env_info['externalNet'])[random.randrange(self._worker_ip_offset, 250)]
            if random_ip not in self.get_used_ips():
                done = True
        return random_ip

    def get_used_ips(self):
        """:returns: list - ips found in libvirt network config"""
        result = subprocess.run(
            ["sudo", "virsh", "net-dhcp-leases", self.__buttnet],
            stdout=subprocess.PIPE,
            universal_newlines=True)
        # yeah this is fecked but yeah i don't know ...
        return [(line.split()[4]).split("/")[0] for line in result.stdout.split("\n")[2:-2]]

    def add_dhcp_entry(self, vm_config):
        """adds a dhcp assignement to libvirt network"""
        dhcp_xml = "<host mac='%s' name='%s' ip='%s' />"%(vm_config['mac'], vm_config['hostname'], vm_config['ip'])
        subprocess.run(
            ["sudo", "virsh", "net-update", self.__buttnet, "add", "ip-dhcp-host", dhcp_xml, "--live"],
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def delete_dhcp_entry(self, vm_name):
        """delete dhcp assignement from libvirt network"""
        dhcp_xml = "<host name='{}' />".format(vm_name)
        subprocess.run(["sudo", "virsh", "net-update", self.__buttnet, "delete", "ip-dhcp-host", dhcp_xml, "--live"], stdout=subprocess.PIPE, universal_newlines=True)

    def generate_worker_config(self):
        """ return a dict with config for a worker vm"""
        hostname = "kube-worker-{}-{}".format(self._cluster_info['cluster_name'], self.get_hostname_suffix())
        host_ip = self.get_random_worker_ip()
        self.__ssl_helper.generateHost(hostname, host_ip)
        vm_config = {
            'hostname': hostname,
            "mac": self.random_mac(),
            "ip": host_ip,
            "disk": self._env_info['workers']['disk'],
            "butt_net": self.__buttnet,
            "butt_dir": self._cluster_info['buttdir'],
            "ram": self._env_info['workers']['ram'],
            "libvirt_host": self.__libvirt_host,
            "cpus": self._env_info['workers']['cpus'],
            "host_pem": self.__ssl_helper.getInfo()["%s_pem" % hostname],
            "host_key": self.__ssl_helper.getInfo()["%s_key" % hostname]
        }
        return vm_config

    def create_volume(self, vm_config):
        """ Expects configuration dict for a virtual machines
            uses subprocess and qemu-img to create and resize an image"""
        result = subprocess.run([
            "qemu-img", "create", "-f", "qcow2", "-b",
            "%s/%s" % (self._cluster_info['buttdir'], self._cluster_info['base_image']),
            "%s/%s.qcow2" % (self._cluster_info['buttdir'], vm_config['hostname'])
        ],
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        print(result.stdout)
        if vm_config['disk'] > 8:
            size = vm_config['disk'] - 8
            result = subprocess.run([
                "sudo", "qemu-img", "resize", "%s/%s.qcow2" %
                (self._cluster_info['buttdir'], vm_config['hostname']), "+%iG" % (size)
            ],
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            print(result.stdout)

    def create_user_data(self, vm_config, vm_role):
        """Creates and writes out user data specific to given vm config"""
        uddir = "%s/%s/openstack/latest" % (self._cluster_info['buttdir'],
                                            vm_config['hostname'])
        if not os.path.exists(uddir):
            os.makedirs(uddir)
        ud_dict = {
            "kube_addons": yaml.dump(self._cluster_info['kube_addons']) % {
                **
                vm_config,
                **
                self._env_info,
                **
                self._cluster_info
            },
            "kube_manifests": yaml.dump(self._cluster_info['kube_manifests'][vm_role]) % {
                **
                vm_config,
                **
                self._env_info,
                **
                self._cluster_info
            },
        }
        with open("%s/user_data" % (uddir), 'w') as file:
            file.write(self._cluster_info['user_data_tmpl'][vm_role] %
                       {**vm_config, **self._env_info,
                        **self._cluster_info,
                        **(self.__ssl_helper.getInfo()),
                        **ud_dict})

    def create_vm(self, vm_config, vm_role):
        """Use subprocess/virt-install to create/start a vm in libvirt"""
        self.create_volume(vm_config)
        self.create_user_data(vm_config, vm_role)
        cmd = Builder.__LIBVIRT_CREATE_TMPLT__ % (vm_config)
        result = subprocess.run(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        print(result.stdout)

    def create_butt_pool(self):
        """ create a libvirt storage pool"""
        try:
            self.__libvirt_conn.storagePoolLookupByName(self.__buttpool)
            print("Storage pool exists")
        except libvirt.libvirtError:
            print("Creating storage pool %s" % self.__buttpool)
            result = subprocess.run([
                "sudo", "virsh", "pool-define-as", "--type=dir", "--name=%s" %
                (self.__buttpool), "--target=%s" % (self._cluster_info['buttdir'])
            ],
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            if result.returncode == 0:
                subprocess.run([
                    "sudo", "virsh", "pool-start", "--pool",
                    "%s" % (self.__buttpool)
                ],
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
                storage_pool = self.__libvirt_conn.storagePoolLookupByName(
                    self.__buttpool)
                storage_pool.setAutostart(1)
                print("Storage pool created")

    def create_butt_network(self, __vm_initial_configs):
        """ create libvirt network including dhcp setup"""
        if [
                net for net in self.__libvirt_conn.listNetworks()
                if net == self.__buttnet
        ] != []:
            # network = self.__libvirt_conn.networkLookupByName(self.__buttnet)
            print("Destroying Network")
            subprocess.run(
                ["sudo", "virsh", "net-destroy", "%s" % self.__buttnet],
                stdout=subprocess.PIPE,
                universal_newlines=True)
            subprocess.run(
                ["sudo", "virsh", "net-undefine", "%s" % self.__buttnet],
                stdout=subprocess.PIPE,
                universal_newlines=True)
        print("Creating network %s" % (self.__buttnet))
        dhcp_setup = ""
        for master in __vm_initial_configs['masters']:
            dhcp_setup += "<host mac='%s' name='%s' ip='%s'/>\n" % (
                master['mac'], master['hostname'], master['ip'])
        for worker in __vm_initial_configs['workers']:
            dhcp_setup += "<host mac='%s' name='%s' ip='%s'/>\n" % (
                worker['mac'], worker['hostname'], worker['ip'])
        iprange = list(
            ipaddress.IPv4Network(self._env_info['externalNet']).hosts())
        xml = Builder.__LIBVIRT_NETWORK_TMPLT__ % (
            self.__buttnet, self.__buttnet[:5], self.random_mac(), iprange[-1],
            (ipaddress.IPv4Network(self._env_info['externalNet'])).netmask,
            iprange[0], iprange[-2], dhcp_setup)
        temp_file = tempfile.NamedTemporaryFile()
        temp_file.write(xml.encode('utf-8'))
        temp_file.seek(0)
        subprocess.run(["sudo", "virsh", "net-define", "%s" % temp_file.name],
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        temp_file.close()
        subprocess.run(["sudo", "virsh", "net-start", "%s" % self.__buttnet],
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        subprocess.run(
            ["sudo", "virsh", "net-autostart", "%s" % self.__buttnet],
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def get_next_hostname(self):
        """ figure out the next hostname from what is running"""
        for domain in self.__libvirt_conn.listAllDomains():
            print(domain.name())

    def add_node(self):
        """add a node to existing kubernetes cluster"""
        __vm_config = self.generate_worker_config()
        self.add_dhcp_entry(__vm_config)
        self.create_vm(__vm_config, 'worker')

    @staticmethod
    def delete_vm(vm_name):
        """deletes a vm from libvirt"""
        subprocess.run(["sudo", "virsh", "destroy", vm_name],
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        subprocess.run(["sudo", "virsh", "undefine", vm_name],
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
