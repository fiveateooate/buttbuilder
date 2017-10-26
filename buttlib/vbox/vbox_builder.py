"""build clusters on vbox"""

import ipaddress
import os
import subprocess

import yaml

import buttlib


class Builder(buttlib.common.ButtBuilder):
    __MKCONFIGDRIVE_ISO_TMPLT = "mkisofs -R -V config-2 -o %s %s"  # iso user_data_dir
    __REGISTER_TMPLT = "VBoxManage createvm --name %s --ostype %s --register"
    #__VM_CONFIG_TMPLT = "VBoxManage modifyvm %s --memory '%s' --nic1 bridged --bridgeadapter1 '%s' --macaddress1 '%s' --natdnshostresolver1"
    __VM_CONFIG_TMPLT = "VBoxManage modifyvm %s --vram 20 --memory '%s' --nic1 natnetwork --nat-network1 %s"
    __ADD_STORAGE_CONTROLLER_TMPLT = "VBoxManage storagectl %s --name 'IDE' --add 'ide'"
    __STORAGE_ATTACH_TMPLT = "VBoxManage storageattach %s --storagectl 'IDE' --port %s --type %s --medium %s --device %s"
    __START_VM_TMPLT = "VBoxManage startvm %s --type headless"
    __CLONEVM_TMPLT = "VBoxManage clonehd %s %s --format VDI"
    __PORTFORWARD_TMPLT = "VBoxManage natnetwork modify --netname %s --port-forward-4 '%s-ssh:tcp:[127.0.0.1]:%i:[%s]:22'"
    __APISERVER_PORTFORWARD_TMPLT = "VBoxManage natnetwork modify --netname %s --port-forward-4 'https:tcp:[127.0.0.1]:10443:[%s]:443'"

    def __init__(self, env_info, args):
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        #print("NOTE: sudo will be used to interact with virtualbox")
        self.__ssl_helper = buttlib.helpers.SSLHelper(
            self._env_info['clusterDomain'],
            "%s/ssl" % self._cluster_info['buttdir'])
        self._coreos_image = 'coreos_production_image.bin.bz2'
        self.__vdi_image = "coreos_image.vdi"
        self.__os_type_id = "Linux26_64"
        self.__net_device = "enp0s3"
        self.__buttnet = "%s-net" % (self._cluster_info['cluster_name'])
        with open("butt-templates/network/network_config.yaml", "r") as file:
            self.__network_config = file.read()
        self.__host_ssh_port = 10022
        self._cluster_info['kube_masters'] = self.get_kube_masters()
        self._cluster_info['etcd_hosts'] = self.get_master_hosts()
        self._cluster_info['etcd_initial_cluster'] = self.get_initial_cluster()
        self._cluster_info['master_port'] = 10443
        self._cluster_info['kube_master'] = "127.0.0.1"

    def get_kube_masters(self):
        return ','.join([
            "https://%s" % (master['ip']) for master in self.get_master_info()
        ])

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

    def get_etcd_hosts(self):
        return ",".join([
            "http://%s:2379" % master['ip']
            for master in self.get_master_info()
        ])

    def createBaseImage(self):
        self.fetch_image()
        dst_image = "%s/%s" % (self._cluster_info['buttdir'], self.__vdi_image)
        src_image = "%s/%s" % (self._cluster_info['buttdir'],
                               self._cluster_info['base_image'])
        if os.path.isfile(dst_image):
            print("removing " + dst_image)
            os.remove(dst_image)
        convert_cmd = "VBoxManage convertdd %s %s --format VDI" % (src_image,
                                                                   dst_image)
        subprocess.run(
            convert_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def createVolume(self, vm):
        print("Creating vdi for %s" % (vm['hostname']))
        src_image = "%s/%s" % (self._cluster_info['buttdir'], self.__vdi_image)
        #dst_image = "%s/%s/%s.vdi"%(self._cluster_info['buttdir'],host,host)
        clone_cmd = Builder.__CLONEVM_TMPLT % (src_image, vm['vdi'])
        resize_cmd = "VBoxManage modifyhd %s --resize %s" % (vm['vdi'],
                                                             vm['disk'])
        if os.path.isfile(vm['vdi']):
            print("removing " + vm['vdi'])
            os.remove(vm['vdi'])
        subprocess.run(
            clone_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            resize_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def createDirectories(self, vm):
        host_dir = "%s/%s" % (self._cluster_info['buttdir'], vm['hostname'])
        if not os.path.exists(host_dir):
            os.makedirs(host_dir)
            os.makedirs(vm['user_data_dir'])

    def createConfigDrive(self, vm):
        self.createUserData(vm)
        cmd = Builder.__MKCONFIGDRIVE_ISO_TMPLT % (
            vm['config-drive'],
            self._cluster_info['buttdir'] + "/" + vm['hostname'] + "/userdata")
        subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)

    def createVM(self, vm):
        register_cmd = Builder.__REGISTER_TMPLT % (vm['hostname'],
                                                   self.__os_type_id)
        vm_config_cmd = Builder.__VM_CONFIG_TMPLT % (vm['hostname'], vm['ram'],
                                                     self.__buttnet)
        storagectl_cmd = Builder.__ADD_STORAGE_CONTROLLER_TMPLT % (
            vm['hostname'])
        attach_vdi_cmd = Builder.__STORAGE_ATTACH_TMPLT % (vm['hostname'], 0,
                                                           'hdd', vm['vdi'], 0)
        attach_configdrive_cmd = Builder.__STORAGE_ATTACH_TMPLT % (
            vm['hostname'], 1, 'dvddrive', vm['config-drive'], 1)
        start_cmd = Builder.__START_VM_TMPLT % (vm['hostname'])
        port_forward_cmd = Builder.__PORTFORWARD_TMPLT % (self.__buttnet,
                                                          vm['hostname'],
                                                          vm['host_ssh_port'],
                                                          vm['ip'])
        subprocess.run(
            register_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            vm_config_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            storagectl_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            attach_vdi_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            attach_configdrive_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            port_forward_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            start_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)

    def createNetwork(self, name, network_cidr):
        network_delete_cmd = "VBoxManage natnetwork remove --netname %s" % (
            name)
        network_create_cmd = "VBoxManage natnetwork add --netname %s --network '%s' --enable --dhcp off" % (
            name, network_cidr)
        https_portforward_cmd = Builder.__APISERVER_PORTFORWARD_TMPLT % (
            self.__buttnet, str(
                ipaddress.IPv4Network(self._env_info['externalNet'])[
                    self._master_ip_offset]))
        #dhcp_server_cmd = "VBoxManage dhcpserver add --netname %s"%(name)
        subprocess.run(
            network_delete_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            network_create_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        subprocess.run(
            https_portforward_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            universal_newlines=True)
        for i in range(30600, 30699):
            portforward_cmd = "VBoxManage natnetwork modify --netname %s --port-forward-4 'port-%i:tcp:[127.0.0.1]:%i:[%s]:%i'" % (
                self.__buttnet, i, i, str(
                    ipaddress.IPv4Network(self._env_info['externalNet'])[
                        self._worker_ip_offset]), i)
            subprocess.run(
                portforward_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                universal_newlines=True)
        #subprocess.run(dhcp_server_cmd, shell=True, stdout=subprocess.PIPE,universal_newlines=True)

    def createUserData(self, vm):
        #user_data_dir = ("%s/%s/userdata/openstack/latest"%(self._cluster_info['buttdir'],vm['hostname']))
        self.__ssl_helper.generateHost(vm['hostname'], vm['ip'])
        ud_dict = {
            "kube_addons": yaml.dump(self._cluster_info['kube_addons']) % {
                **
                vm,
                **
                self._env_info,
                **
                self._cluster_info
            },
            "kube_manifests":
            yaml.dump(self._cluster_info['kube_manifests'][vm['vm_role']]) % {
                **
                vm,
                **
                self._env_info,
                **
                self._cluster_info
            },
            "host_pem": self.__ssl_helper.getInfo()["%s_pem" % vm['hostname']],
            "host_key": self.__ssl_helper.getInfo()["%s_key" % vm['hostname']],
            'optional_hostname_override': "--hostname-override=%s" % vm['ip']
        }
        netcfg = {
            'network_config': self.__network_config % {
                'device': self.__net_device,
                "network_gateway": vm['gateway'],
                'ip_with_cidr': vm['ip'] + "/" + vm['cidr'],
                'host_dns': '8.8.8.8'
            }
        }
        with open("%s/user_data" % (vm['user_data_dir']), 'w') as file:
            file.write(self._cluster_info['user_data_tmpl'][vm['vm_role']] % {**vm, **self._env_info, **self._cluster_info, **(self.__ssl_helper.getInfo()), **ud_dict, **netcfg})

    def build(self):
        proceed = 'n'
        proceed = input("Build is a destructive command, proceed? (YES|no) ")
        if proceed != "YES":
            raise buttlib.common.DoNotDestroyCluster(
                "Leaving cluster alone in whatever state")
        master_ips = self.get_master_ips()
        master_ips.append("127.0.0.1")
        self.__ssl_helper.createCerts(master_ips,
                                      self._cluster_info["cluster_ip"],
                                      self.get_master_hosts())
        self.createBaseImage()
        self.createNetwork(self.__buttnet, self._env_info['externalNet'])
        for i, host in enumerate(self.get_master_hosts()):
            vm = {
                'hostname':
                host,
                'vm_role':
                'master',
                'user_data_dir':
                "%s/%s/userdata/openstack/latest" %
                (self._cluster_info['buttdir'], host),
                'vdi':
                "%s/%s/%s.vdi" % (self._cluster_info['buttdir'], host, host),
                'config-drive':
                "%s/%s/%s.iso" % (self._cluster_info['buttdir'], host, host),
                'disk':
                self._env_info['masters']['disk'],
                #'mac':self._env_info['masters']['macs'][i],
                'ram':
                self._env_info['masters']['ram'],
                'ip':
                str(
                    ipaddress.IPv4Network(self._env_info['externalNet'])[
                        i + self._master_ip_offset]),
                'cidr': (self._env_info['externalNet'].split("/"))[-1],
                'gateway':
                str(ipaddress.IPv4Network(self._env_info['externalNet'])[1]),
                'host_ssh_port':
                self.__host_ssh_port
            }
            self.__host_ssh_port += 1
            self.createDirectories(vm)
            self.createVolume(vm)
            self.createConfigDrive(vm)
            self.createVM(vm)
        for i, host in enumerate(self.get_worker_hosts()):
            vm = {
                'hostname':
                host,
                'vm_role':
                'worker',
                'user_data_dir':
                "%s/%s/userdata/openstack/latest" %
                (self._cluster_info['buttdir'], host),
                'vdi':
                "%s/%s/%s.vdi" % (self._cluster_info['buttdir'], host, host),
                'config-drive':
                "%s/%s/%s.iso" % (self._cluster_info['buttdir'], host, host),
                'disk':
                self._env_info['workers']['disk'],
                #'mac':self._env_info['workers']['macs'][i],
                'ram':
                self._env_info['workers']['ram'],
                'ip':
                str(
                    ipaddress.IPv4Network(self._env_info['externalNet'])[
                        i + self._worker_ip_offset]),
                'cidr': (self._env_info['externalNet'].split("/"))[-1],
                'gateway':
                str(ipaddress.IPv4Network(self._env_info['externalNet'])[1]),
                'host_ssh_port':
                self.__host_ssh_port
            }
            self.__host_ssh_port += 1
            self.createDirectories(vm)
            self.createVolume(vm)
            self.createConfigDrive(vm)
            self.createVM(vm)
