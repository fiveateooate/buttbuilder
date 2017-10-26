"""
kubernetes cluster builder for proxmox
uses ssh and qm
a coreos template must exist on proxmox prior to run
"""

import ipaddress
import os
import re
import subprocess
from proxmoxer import ProxmoxAPI
import yaml
from sh import scp, ssh #pylint:disable=E0611

import buttlib

class Builder(buttlib.common.ButtBuilder):
    """builder for proxmox
    """
    __MKCONFIGDRIVE_ISO_TMPLT = "mkisofs -R -V config-2 -o %s %s"  # iso user_data_dir

    def __init__(self, env_info, args):
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        self.__ssl_helper = buttlib.helpers.SSLHelper(self._env_info['clusterDomain'], "%s/ssl" % self._cluster_info['buttdir'])
        self.__net_device = "eth0"
        with open("butt-templates/network/network_config.yaml", 'r') as file:
            self.__network_config = file.read()
        self._cluster_info['kube_masters'] = self.get_kube_masters()
        self._cluster_info['etcd_hosts'] = self.get_master_hosts()
        self._cluster_info['etcd_initial_cluster'] = self.get_initial_cluster()
        self._cluster_info['master_port'] = 10443
        self._cluster_info['kube_master'] = "127.0.0.1"
        self.__proxmox_host = self._env_info['proxmoxHost']
        self.__proxmox_user = self._env_info['proxmoxUser']
        self.__proxmox_storage_path = self._env_info['storagePath']
        self.__proxmox_storage_name = "local"
        self.__proxmox_instances = {}
        self.__proxmox_tmpl_name = "coreosbase"
        self.__butt_net = env_info['bridge']
        self.__max_vmid = 0
        self.__proxmox = ProxmoxAPI('127.0.0.1', user='user', password='password', verify_ssl=False)


    def get_kube_masters(self):
        return ','.join(
            ["https://%s" % (master['ip']) for master in self.get_master_info()])

    def get_master_info(self):
        return [{
            'hostname':
            "%s-master%02d" % (self._cluster_info['cluster_name'], i + 1),
            'ip':
            str(
                ipaddress.IPv4Network(self._env_info['externalNet'])[
                    i + self._master_ip_offset])
        } for i in range(self._env_info['masters']['nodes'])]

    def get_initial_cluster(self):
        masters = self.get_master_info()
        return ",".join([
            "%s=http://%s:2380" % (master['hostname'], master['ip'])
            for master in masters
        ])

    def get_master_hosts(self):
        return ",".join([
            "http://%s:2379" % master['ip'] for master in self.get_master_info()
        ])

    def _process_list(self, line):
        if not re.match(r"^\s*VMID|^\s*$", line):
            line = line.strip()
            temp = line.split()
            self.__proxmox_instances[temp[1]] = {
                'vmid': temp[0],
                'name': temp[1],
                'status': temp[2],
                'disk': float(temp[4]) * 1000,
                'pid': temp[5]
            }
            if int(temp[0]) > self.__max_vmid:
                self.__max_vmid = int(temp[0])

    def _get_running_instances(self):
        process = ssh("root@%s" % self.__proxmox_host,
                      "qm",
                      "list",
                      _out=self._process_list,
                      _bg=True)
        process.wait()

    def cluster_exists(self):
        """is cluster already set up?
        :returns: boolean"""
        ret_val = False
        if self._cluster_info['buttdir']: # BUG what to really check ????
            ret_val = False
        return ret_val

    def generate_worker_config(self, index):
        """ return a dict with config for a worker vm"""
        hostname = "%s-worker-%s" % (self._cluster_info['cluster_name'],
                                     self.get_hostname_suffix())
        host_ip = self.get_worker_ip(index)
        self.__ssl_helper.generateHost(hostname, host_ip)
        self.__max_vmid += 1
        vm_config = {
            'hostname':
            hostname,
            "ip":
            host_ip,
            "disk":
            self._env_info['workers']['disk'],
            "butt_net":
            self.__butt_net,
            "butt_dir":
            self._cluster_info['buttdir'],
            "ram":
            self._env_info['workers']['ram'],
            "cpus":
            self._env_info['workers']['cpus'],
            "host_pem":
            self.__ssl_helper.getInfo()["%s_pem" % hostname],
            "host_key":
            self.__ssl_helper.getInfo()["%s_key" % hostname],
            'cidr': (self._env_info['externalNet'].split("/"))[-1],
            'gateway':
            str(ipaddress.IPv4Network(self._env_info['externalNet'])[1]),
            'config-drive':
            "%s/%s/%s.iso" % (self._cluster_info['buttdir'], hostname, hostname),
            'vmid':
            self.__max_vmid
        }
        return vm_config

    def generate_master_config(self, index):
        """ return a dict with config for a master vm"""
        hostname = "%s-master%02d" % (self._cluster_info['cluster_name'],
                                      index + 1)
        host_ip = str(
            ipaddress.IPv4Network(self._env_info['externalNet'])[
                index + self._master_ip_offset])
        self.__ssl_helper.generateHost(hostname, host_ip)
        self.__max_vmid += 1
        vm_config = {
            "hostname":
            hostname,
            "ip":
            host_ip,
            "disk":
            self._env_info['masters']['disk'],
            "butt_net":
            self.__butt_net,
            "butt_dir":
            self._cluster_info['buttdir'],
            "ram":
            self._env_info['masters']['ram'],
            "cpus":
            self._env_info['masters']['cpus'],
            "host_pem":
            self.__ssl_helper.getInfo()["%s_pem" % hostname],
            "host_key":
            self.__ssl_helper.getInfo()["%s_key" % hostname],
            'cidr': (self._env_info['externalNet'].split("/"))[-1],
            'gateway':
            str(ipaddress.IPv4Network(self._env_info['externalNet'])[1]),
            'config-drive':
            "%s/%s/%s.iso" % (self._cluster_info['buttdir'], hostname, hostname),
            'vmid':
            self.__max_vmid
        }
        return vm_config

    def generate_vm_config(self):
        """ returns list of dicts used to configure indvidual virtual machines
            uses parameters read from a yaml file
        """
        vms = {"masters": [], "workers": []}
        for i in range(self._env_info['masters']['nodes']):
            vms['masters'].append(self.generate_master_config(i))
        for i in range(self._env_info['workers']['nodes']):
            vms['workers'].append(self.generate_worker_config(i))
        return vms

    def create_user_data(self, vm_config, vm_role):
        """Creates and writes out user data specific to given vm config"""
        uddir = "%s/%s/userdata/openstack/latest" % (self._cluster_info['buttdir'],
                                                     vm_config['hostname'])
        netcfg = {
            'network_config': self.__network_config % {
                'device': self.__net_device,
                "network_gateway": vm_config['gateway'],
                'ip_with_cidr': vm_config['ip'] + "/" + vm_config['cidr'],
                'host_dns': '8.8.8.8'
            }
        }
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
            'optional_hostname_override':"--hostname-override=%s"%vm_config['ip']
        }
        with open("%s/user_data" % (uddir), 'w') as file:
            file.write(self._cluster_info['user_data_tmpl'][vm_role] %
                       {**vm_config, **self._env_info,
                        **self._cluster_info,
                        **(self.__ssl_helper.getInfo()),
                        **ud_dict,
                        **netcfg})

    def _create_user_data_isos(self, vms):
        for vm_config in vms['masters']:
            self.create_user_data(vm_config, 'master')
            cmd = Builder.__MKCONFIGDRIVE_ISO_TMPLT % (
                vm_config['config-drive'],
                self._cluster_info['buttdir'] + "/" + vm_config['hostname'] + "/userdata")
            subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                universal_newlines=True)
        for vm_config in vms['workers']:
            self.create_user_data(vm_config, 'worker')
            cmd = Builder.__MKCONFIGDRIVE_ISO_TMPLT % (
                vm_config['config-drive'],
                self._cluster_info['buttdir'] + "/" + vm_config['hostname'] + "/userdata")
            subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                universal_newlines=True)

    def _scp_user_data_iso(self, vm_config):
        scp(vm_config['config-drive'],
            "%s@%s:%s/" % (self.__proxmox_user, self.__proxmox_host,
            self.__proxmox_storage_path))

    def _create_vm(self, vm_config):
        ssh("%s@%s" % (self.__proxmox_user,
             self.__proxmox_host), "qm", "clone",
            self.__proxmox_instances[self.__proxmox_tmpl_name]['vmid'],
            vm_config['vmid'], "-full", "-name", vm_config['hostname'])
        ssh("%s@%s" % (self.__proxmox_user, self.__proxmox_host), "qm", "set",
            vm_config['vmid'], "-cdrom", "%s:iso/%s.iso" %
            (self.__proxmox_storage_name, vm_config['hostname']), "-memory",
            vm_config['ram'], "-sockets", vm_config['cpus'],
            "-net0 model=virtio,bridge=%s" % (self._env_info['bridge']))
        if int(vm_config['disk']) > self.__proxmox_instances[
                self.__proxmox_tmpl_name]['disk']:
            ssh("%s@%s" % (self.__proxmox_user, self.__proxmox_host), "qm",
                "resize", vm_config['vmid'], "virtio0", "%sM"%(vm_config['disk']))
        ssh("%s@%s" % (self.__proxmox_user, self.__proxmox_host), "qm",
            "start", vm_config['vmid'])

    def testapistuff(self):
        for vm in self.__proxmox.cluster.resources.get(type='vm'):
            print("{0}. {1} => {2}" .format(vm['vmid'], vm['name'], vm['status']))
        for node in self.__proxmox.nodes.get():
            print(node)
            for vm in self.__proxmox.nodes(node['node']).qemu.get():
                print("{0}. {1} => {2}" .format(vm['vmid'], vm['name'], vm['status']))
        node = self.__proxmox.nodes('jessie-proxmox')
        print(node.storage('local').content.get())
        local_storage = self.__proxmox.nodes('jessie-proxmox-02').storage('local')
        local_storage.upload.create(content='ISO image', filename=open(os.path.expanduser('pve-master01.iso')))

    def build(self):
        print("ssh key auth needs to be set up for this all to work")
        self._get_running_instances()
        # check that nothing to be created already exists
        if self.cluster_exists():
            raise buttlib.common.ClusterExistsError("Cluster exists")
        if self.__proxmox_tmpl_name not in self.__proxmox_instances.keys():
            raise buttlib.common.TemplateNotFoundError("cannot find CoreOS template")
        self.__ssl_helper.createCerts(self.get_master_ips(),
                                      self._cluster_info["cluster_ip"],
                                      self.get_master_hosts())
        vms = self.generate_vm_config()
        self._create_user_data_isos(vms)
        for vm_config in vms['masters'] + vms['workers']:
            self._scp_user_data_iso(vm_config)
            self._create_vm(vm_config)
