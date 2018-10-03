""" build a gce butt"""

import sys
from termcolor import cprint, colored
import pprint
import copy
import buttlib


_CONFIG_TMPL = {
    'name': '',
    'machineType': '',
    'labels': {},
    # Specify the boot disk and the image to use as a source.
    'disks': [{
        'boot': True,
        'autoDelete': True,
        'initializeParams': {
            'sourceImage': '',
            "diskType": ""
        }
    }],
    # Specify a network interface with NAT to access the public internet.
    'networkInterfaces': [{
        'network':
        'global/networks/default',
        'accessConfigs': [{
            "kind": "compute#accessConfig",
            'type': 'ONE_TO_ONE_NAT',
            'name': 'External NAT'
        }],
        'networkIP':
        ''
    }],
    # Allow the instance to access butt storage and logging.
    'serviceAccounts': [{
        'email': 'default',
        'scopes': [
            'https://www.googleapis.com/auth/devstorage.read_write',
            'https://www.googleapis.com/auth/logging.write',
            'https://www.googleapis.com/auth/monitoring.write',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
    }],
    # Metadata is readable from the instance and allows you to
    # pass configuration from deployment scripts to instances.
    'metadata': {
        'items': [{
            'key': 'user-data',
            'value': ''
        }]
    }
}


class Builder(buttlib.common.ButtBuilder):
    """the gce type butt builder"""

    def __init__(self, env_info, args):
        buttlib.common.ButtBuilder.__init__(self, env_info, args)

        self.client = buttlib.gce.GCEClient(project=self._env_info['project'], region=self._env_info['region'])
        self._cluster_info['ip'] = "$private_ipv4"
        self._cluster_info['master_lb_ip'] = self._butt_ips.get_ip(2)
        self._cluster_info['worker_lb_ip'] = self._butt_ips.get_ip(3)
        # setting butt provider to gce doesn't work out of the box need to figure out a buncha crap
        # enabling it make it do things like try to create load balancers and stuff and breaks scheduling
        self._cluster_info['buttProvider'] = "gce"
        self.__region_info = buttlib.gce.regions.get_region(self.client)
        self.__network_url = buttlib.gce.networks.get_network(self.client, self._cluster_info['network_name'])
        self.__instance_groups = self.__instance_group_skel()
        # if "network" in self._env_info:
        #     with open("butt-templates/stubs/gce_hosts.yaml", "r") as file:
        #         self._cluster_info['hostsfile_tmpl'] = file.read()
        #     with open("butt-templates/stubs/gce_resolvconf.yaml", "r") as file:
        #         self._cluster_info['resolvconf'] = file.read()

    def __create_network(self) -> str:
        network_url = ""
        cprint("Creating network ...", "magenta")
        if self._args.dryrun:
            print("would have created network {}".format(self._cluster_info['network_name']))
        else:
            network_url = buttlib.gce.networks.create_network(self.client, self._cluster_info['network_name'], self._env_info['externalNet'])
        cprint("done", "blue")
        return network_url

    def __provider_additional(self, index: int, ip: str, hostname: str, role: str) -> dict:
        pa = {
            "rootDiskSize": self._env_info[role]['disk']
        }
        return pa

    def __instance_group_skel(self) -> dict:
        instance_groups = {}
        for zone in self.__region_info['zones']:
            zone_name = (zone.split("/")[-1]).strip()
            instance_groups[zone_name] = {
                "masters": {
                    "name": "kube-masters-{}-{}".format(self._cluster_info['cluster_name'], zone_name),
                    "url": ""
                },
                "workers": {
                    "name": "kube-workers-{}-{}".format(self._cluster_info['cluster_name'], zone_name),
                    "url": ""
                }
            }
        return instance_groups

    def __add_instance_groups(self) -> dict:
        """create gce instance groups"""
        cprint("Checking/Creating instance groups ...", "magenta")
        for zone, groups in self.__instance_groups.items():
            for role in ['masters', 'workers']:
                group_url = buttlib.gce.instance_groups.get_group(self.client, zone, groups[role]['name'])
                if group_url == {}:
                    cprint("creating group {} in {}".format(groups[role]['name'], zone), "yellow")
                    if not self._args.dryrun:
                        groups[role]['url'] = buttlib.gce.instance_groups.create_group(self.client, zone, groups[role]['name'], self.__network_url)
                elif group_url is not {} and group_url is not None:
                    cprint("group {} {}".format(groups[role]['name'], colored("ok", "green")))
                    self.__instance_groups[zone][role]['url'] = group_url
                else:
                    cprint("die die die", "red")
                    sys.exit(1)
        cprint("done", "blue")

    def __add_load_balancers(self):
        cprint("Creating load balancers ...", "magenta")
        lb_settings = {
            "name": self._cluster_info['master_lb_name'],
            "proto": "tcp",
            "hcport": "443",
            "lbports": [443, 2379],
            "ip": self._cluster_info['master_lb_ip']
        }
        if self._args.verbose:
            print(lb_settings)
        if not self._args.dryrun:
            pass
            # self.__create_internal_lb(lb_settings, instance_groups['masters'])
        lb_settings = {
            "name": self._cluster_info['worker_lb_name'],
            "proto": "tcp",
            "hcport": "80",
            "lbports": [80, 30000, 30012, 30014, 30016, 30040, 30656],
            "ip": self._cluster_info['worker_lb_ip']
        }
        if self._args.verbose:
            print(lb_settings)
        if not self._args.dryrun:
            pass
            # self.__create_internal_lb(lb_settings, instance_groups['workers'])
        cprint("done", "blue")

    def __instance_config(self, bic: buttlib.common.ButtInstanceConfig, zone: str):
        # vm_config = buttlib.gce.InstanceBody(name=bic.hostname, machine_type=self._env_info[bic.role]['machineType'], zone=zone, image=self.__image['selfLink'], subnetwork_url=self.__network_url, disk_size=self._env_info[bic.role]['disk'])
        zone_name = (zone.split("/")[-1]).strip()
        vm_config = copy.deepcopy(_CONFIG_TMPL)
        vm_config['name'] = bic.hostname
        vm_config['machineType'] = "zones/{}/machineTypes/{}".format(zone_name, self._env_info[bic.role]['machineType'])
        vm_config['disks'][0]['initializeParams']['sourceImage'] = self.__image['selfLink']
        vm_config['disks'][0]['initializeParams']['diskSizeGb'] = self._env_info[bic.role]['disk']
        vm_config['disks'][0]['initializeParams']['diskType'] = "zones/{}/diskTypes/pd-ssd".format(zone_name)
        vm_config['networkInterfaces'][0]['network'] = self.__network_url
        vm_config['networkInterfaces'][0]['networkIP'] = bic.ip
        vm_config['metadata']['items'][0]['value'] = bic.ign
        vm_config['labels']['cenv'] = self._cluster_info['cluster_env']
        vm_config['labels']['cid'] = self._cluster_info['cluster_id'].replace(":", "-")
        vm_config['labels']['cluster-role'] = bic.role
        return vm_config

    def __create_vm(self, vm_config, zone):
        instance = None
        zone_name = (zone.split("/")[-1]).strip()
        if not self._args.dryrun:
            instance = buttlib.gce.instances.get_instance(self.client, zone_name, vm_config['name'])
            if instance == {}:
                cprint("Creating instance {} in {}...".format(vm_config['name'], zone_name), "magenta")
                instance = buttlib.gce.instances.create_instance(self.client, zone_name, vm_config)
                cprint("done", "green")
            elif instance is not None:
                ok = colored("ok", "green")
                cprint("instance {} {}".format(vm_config['name'], ok))
            else:
                cprint("die die die", "red")
                sys.exit(1)
        return instance

    def __create_instance(self, hostname, ip, index, role, zone):
        pp = pprint.PrettyPrinter()
        zone_name = (zone.split("/")[-1]).strip()
        provider_additional = self.__provider_additional(index, ip, hostname, 'masters')
        additional_labels = [
            "failure-domain.beta.kubernetes.io/region={}".format(self._env_info['region']),
            "failure-domain.beta.kubernetes.io/zone={}".format(zone_name)
        ]
        bic = buttlib.common.ButtInstanceConfig(hostname, ip, 'masters', self._ssl_helper, self._env_info, self._cluster_info, platform="gce", provider_additional=provider_additional, additional_labels=additional_labels)
        # write out the config
        bic.write_ign()
        # self.upload_ign(bic.instance_config['filename'], hostname)
        instance_body = self.__instance_config(bic, zone)
        if self._args.verbose:
            pp.pprint(instance_body)
        instance = self.__create_vm(instance_body, zone)
        return instance

    def __add_instance_to_group(self, instance, zone, role):
        cprint("Adding instance to group ...", "magenta")
        if not self._args.dryrun:
            zone_name = (zone.split("/")[-1]).strip()
            group = self.__instance_groups[zone_name][role]['url']
            print(group)
            # if re.search("-master-", instance['targetLink']):
            #     group = instance_groups['masters'][zone]['name']
            # else:
            #     group = instance_groups['workers'][zone]['name']
            # buttlib.gce.group.add_instance_to_group(self.__gce_conn, self._env_info['project'], zone, group, instance['targetLink'])
        cprint("done", "blue")

    def __pre_build(self):
        cprint("Collecting cluster info ...", "cyan")
        masters = self._kube_masters.hostnames + [self._cluster_info['master_lb_name']]
        ips = self._kube_masters.ips + [self._cluster_info['kube_master_lb_ip']]
        self._ssl_helper.create_or_load_certs(ips, self._cluster_info["cluster_ip"], masters)
        self.__image = buttlib.gce.images.getFromFamily(self.client)
        cprint("using image {}".format(self.__image['selfLink']))
        if self.__network_url is None:
            cprint("TODO: self.__create_network()", "red")
            # punt for now
            sys.exit(1)
        cprint("using network {}".format(self.__network_url['selfLink']))
        self.__add_instance_groups()
        self.__add_load_balancers()
        cprint("done", "blue")

    def build(self):
        """create the butt"""
        print("create a butt")
        self.__pre_build()
        instances = []
        index = 0
        num_zones = len(self.__region_info['zones'])
        for hostname, ip in self._kube_masters.masters:
            role = "masters"
            zone = self.__region_info['zones'][index % num_zones]
            instance = self.__create_instance(hostname, ip, index, role, zone)
            self.__add_instance_to_group(instance, zone, role)
            index += 1
        index = 0
        for hostname, ip in self._kube_workers.workers:
            role = "workers"
            zone = self.__region_info['zones'][index % num_zones]
            instance = self.__create_instance(hostname, ip, index, role, zone)
            self.__add_instance_to_group(instance, zone, role)
            index += 1
        # self.__add_to_target_pool(instances)
        # self.__add_firewall_rules()

    # def get_master_info(self):
    #     return [
    #         {
    #          "hostname": "kube-master-{}-{02d}".format(self._cluster_info['cluster_name'], i + 1),
    #          "ip": self._butt_ips.get_ip(self._cluster_info['ipOffsets']['masters'] + i)
    #         }
    #         for i in range(self._env_info['masters']['nodes'])
    #     ]
    #
    # def get_master_ips(self):
    #     return [self._butt_ips.get_ip(i + self._cluster_info['ipOffsets']['masters']) for i in range(self._env_info['masters']['nodes'])]

    #
    # def __create_internal_lb(self, lb_settings, instance_groups):
    #     backend_url = buttlib.gce.gce_network.create_internal_backend_service(self.__gce_conn, self._env_info['project'], self._env_info['region'], lb_settings['name'], instance_groups, lb_settings['hcport'])
    #     buttlib.gce.gce_network.create_forwarding_rule(
    #         self.__gce_conn,
    #         self._env_info['project'],
    #         self._env_info['region'],
    #         self._cluster_info['master_lb_name'],
    #         backend_url,
    #         lb_settings['proto'],
    #         lb_settings['lbports'],
    #         self.__network_url,
    #         internal=True,
    #         ip=lb_settings['ip'])
    #
    # def __create_external_lb(self, lb_settings):
    #     backend_url = buttlib.gce.gce_network.create_target_pool(self.__gce_conn, lb_settings['name'], self._env_info['project'], self._env_info['region'], lb_settings['hcport'])
    #     buttlib.gce.gce_network.create_forwarding_rule(self.__gce_conn, self._env_info['project'], self._env_info['region'], lb_settings['name'], backend_url, lb_settings['schema'], lb_settings['lbports'])
    #
    # def __add_to_target_pool(self, instances):
    #     cprint("Adding instances to target pools ...", "magenta")
    #     if not self._args.dryrun:
    #         worker_instances = [
    #             {
    #                 "instance": instance['targetLink']
    #             } for instance in instances
    #             if not re.search("-master-", instance['targetLink'])
    #         ]
    #         buttlib.gce.gce_network.add_to_target_pool(
    #             self.__gce_conn, worker_instances,
    #             self._cluster_info['worker_lb_name'],
    #             self._env_info['project'], self._env_info['region'])
    #     cprint("done", "blue")
    #
    # def __add_firewall_rules(self):
    #     cprint("Adding default firewall rules ...", "magenta")
    #     if not self._args.dryrun and 'network' not in self._env_info:
    #         buttlib.gce.gce_network.create_firewall_rules(
    #             self.__gce_conn, self.__network_url,
    #             "{}-internal-any".format(self._cluster_info['network_name']),
    #             "tcp", "0-65535", [self._env_info['externalNet']],
    #             self._env_info['project'])
    #         buttlib.gce.gce_network.create_firewall_rules(
    #             self.__gce_conn, self.__network_url,
    #             "{}-office-ssh-web".format(self._cluster_info['network_name']),
    #             "tcp", ["22", "80", "443"], self._env_info['officeIP'],
    #             self._env_info['project'])
    #         buttlib.gce.gce_network.create_firewall_rules(
    #             self.__gce_conn, self.__network_url,
    #             "{}-health-checks".format(self._cluster_info['network_name']),
    #             "tcp", ["80", "443"], self._env_info['googleHealthChecks'],
    #             self._env_info['project'])
    #     cprint("done", "blue")
    #
    # def get_initial_cluster(self):
    #     """:returns: - string - etcd initial cluster string"""
    #     return ",".join([
    #         "{hostname}=http://{ip}:2380".format(ip=master['ip'], hostname=master['hostname'])
    #         for index, master in enumerate(self.get_master_info())
    #     ])

    def create_master_cluster(self):
        pass
        # create master subnet
        # do something about ips and get etcd inital cluster
        # create vms
        # add instance to group
        # crewate whatever lb and fw configs

    def add_worker_node(self, args):
        pass
        # get an ip
        # create a config?
        # create vm
        # add to instance group
        # fw/lb adjustments

    def delete_worker_node(self, instnace_name):
        pass
        # instance = buttlib.instance.get(client, instance_name)
        # buttlib.gce.instance.delete(client, instance_name)
        # adjust fw/lb

    # def get_user_data(self, role, vm_info):
    #     """:params node_type: master or worker
    #     :params vm_info: dict of vm config
    #     :params __ssl_helper: ssl helper class instance to do stuff with certs
    #     :returns: string - big glob of user data"""
    #     user_data = ""
    #     self.__ssl_helper.generateHostName(vm_info['hostname'])
    #     ud_dict = {
    #         "kube_addons":
    #         yaml.dump(self._cluster_info['kube_addons']) % {
    #             **
    #             vm_info,
    #             **
    #             self._env_info,
    #             **
    #             self._cluster_info
    #         },
    #         "kube_manifests":
    #         yaml.dump(self._cluster_info['kube_manifests'][re.sub(
    #             r"s$", "", role)]) % {
    #                 **
    #                 vm_info,
    #                 **
    #                 self._env_info,
    #                 **
    #                 self._cluster_info
    #             },
    #         "host_pem":
    #         self.__ssl_helper.getInfo()["%s_pem" % vm_info['hostname']],
    #         "host_key":
    #         self.__ssl_helper.getInfo()["%s_key" % vm_info['hostname']]
    #     }
    #     if "network" in self._env_info:
    #         self._cluster_info['resolvconf'] = self._cluster_info['resolvconf'] % (self._env_info['network'])
    #         self._cluster_info['hostsfile'] = self._cluster_info['hostsfile_tmpl'] % (vm_info)
    #     if role == 'masters':
    #         user_data = self._cluster_info['user_data_tmpl']['master'] % (
    #             {**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
    #     else:
    #         user_data = self._cluster_info['user_data_tmpl']['worker'] % (
    #             {**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
    #     return user_data
    #
    # def get_kube_masters(self):
    #     """:returns: string"""
    #     return "https://{ip}".format(ip=self._cluster_info['master_ip'])
    #
    # def create_forwarding_rule(self, portrange="443", proto="TCP"):
    #     """create a gce forwarding rule"""
    #     name = "%s-fwd" % self._cluster_info['cluster_name']
    #     buttlib.gce.gce_network.create_forwarding_rule(
    #         self.__gce_conn, name, proto, portrange,
    #         self._cluster_info['master_lb_name'], self._env_info['region'],
    #         self._env_info['project'])
