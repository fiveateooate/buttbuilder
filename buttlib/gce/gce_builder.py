""" build a gce butt"""
import copy
import os
import re

import yaml
#from googleapiclient import discovery
#from oauth2client.client import GoogleCredentials

import buttlib

_CONFIG_TMPL = {
    'name':
    '',
    'machineType':
    '',
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
        'email':
        'default',
        'scopes': [
            'https://www.googleapis.com/auth/devstorage.read_write',
            'https://www.googleapis.com/auth/logging.write'
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

        self.client = buttlib.gce.client(project=self._env_info['project'], region=self._env_info['region'])
        self.__ssl_helper = buttlib.helpers.SSLHelper(self._env_info['clusterDomain'], "{}/ssl".format(self._cluster_info['buttdir']), bits=2048)
        self._cluster_info['master_lb_name'] = ButtBuilder.LB_NAME_TMPLT.format(type="master", cluster_name=self._cluster_info['cluster_name'])
        self._cluster_info['worker_lb_name'] = ButtBuilder.LB_NAME_TMPLT.format(type="worker", cluster_name=self._cluster_info['cluster_name'])
        self._cluster_info['ip'] = "$private_ipv4"
        self.__network_url = None
        self._cluster_info['master_ip'] = self._butt_ips.get_ip(2)
        self._cluster_info['worker_ip'] = self._butt_ips.get_ip(3)
        self._cluster_info['kube_masters'] = self.get_kube_masters()
        self._cluster_info['ipOffsets'] = {"masters": 30, "workers": 50}
        self._cluster_info["etcd_initial_cluster"] = self.get_initial_cluster()
        # setting butt provider to gce doesn't work out of the box need to figure out a buncha crap
        # enabling it make it do things like try to create load balancers and stuff and breaks scheduling
        self._cluster_info['cloud_provider'] = "gce"

        # stupid fecking shit cause we have all this stupid fecking vpn crap
        if "network" in self._env_info:
            with open("butt-templates/stubs/gce_hosts.yaml", "r") as file:
                self._cluster_info['hostsfile_tmpl'] = file.read()
            with open("butt-templates/stubs/gce_resolvconf.yaml", "r") as file:
                self._cluster_info['resolvconf'] = file.read()

    def __get_hostname(self, role, index):
        hostname = "kube-worker-{cluster_name}-{suffix:02d}".format(cluster_name=self._cluster_info['cluster_name'], suffix=index+1)
        if role == "masters":
            hostname = "kube-master-{cluster_name}-{suffix:02d}".format(cluster_name=self._cluster_info['cluster_name'], suffix=index + 1)
        return hostname

    def generate_vm_config(self, role, image, index, zone):
        """
        Generate parameter dictionary sutiable for kubernetes worker
            new SSL keys will be generated
        """
        vm_info = {}
        ip_address = self._butt_ips.get_ip(
            index + self._cluster_info['ipOffsets'][role])
        hostname = self.__get_hostname(role, index)
        vm_tmp = {"hostname": hostname, "ip": ip_address}
        vm_info = copy.deepcopy(_CONFIG_TMPL)
        vm_info['name'] = vm_tmp["hostname"]
        vm_info['machineType'] = "zones/{zone}/machineTypes/{type}".format(zone=zone, type=self._env_info[role]['machineType'])
        vm_info['disks'][0]['initializeParams']['sourceImage'] = image
        vm_info['disks'][0]['initializeParams']['diskSizeGb'] = self._env_info[role]['rootDiskSize']
        vm_info['disks'][0]['initializeParams']['diskType'] = "zones/{}/diskTypes/pd-ssd".format(zone)
        vm_info['networkInterfaces'][0]['network'] = self.__network_url
        vm_info['networkInterfaces'][0]['networkIP'] = ip_address
        vm_info['metadata']['items'][0]['value'] = self.get_user_data(role, vm_tmp)
        vm_info['additionalLabels'] = ",failure-domain.beta.kubernetes.io/region={},failure-domain.beta.kubernetes.io/zone={}".format(self._env_info['region'], zone)
        return vm_info

    def get_master_info(self):
        return [
            {"hostname": "kube-master-%s-%02d" % (self._cluster_info['cluster_name'], i + 1), "ip": self._butt_ips.get_ip(self._cluster_info['ipOffsets']['masters'] + i)} for i in range(self._env_info['masters']['nodes'])
        ]

    def get_master_ips(self):
        return [self._butt_ips.get_ip(i + self._cluster_info['ipOffsets']['masters']) for i in range(self._env_info['masters']['nodes'])]

    def __create_certs(self):
        buttlib.helpers.BColors().bcprint("Creating certs ...", "HEADER")
        master_ips = self.get_master_ips()
        master_ips.append(self._cluster_info['master_ip'])
        self.__ssl_helper.createCerts(master_ips, self._cluster_info["cluster_ip"], self.get_master_hosts())
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")

    def __create_or_get_network(self):
        network_url = ""
        buttlib.helpers.BColors().bcprint("Creating network ...", "HEADER")
        network = buttlib.gce.networks.get(self.client, self._cluster_info['network_name'])
        if network:
            network_url = network['selfLink']
        else:
            if self._args.dryrun:
                print("would have created network {}".format(self._cluster_info['network_name']))
            else:
                network_url = buttlib.gce.networks.create(self.client, self._cluster_info['network_name'], self._env_info['externalNet'])
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")
        return network_url

    def __create_or_get_instance_groups(self):
        """create a gce instance group"""
        instance_groups = {'masters': {}, 'workers': {}}
        region_info = buttlib.gec.regions.get(self.client)
        buttlib.helpers.BColors().bcprint("Creating instance groups ...", "HEADER")
        # if not self._args.dryrun:
        for zone in region_info['zones']:
            zone_name = (zone.split("/")[-1]).strip()
            master_name = "kube-masters-{cluster}-{zone}".format(cluster=self._cluster_info['cluster_name'], zone=zone_name)
            instance_groups['masters'][zone_name] = {"name": master_name, "url": ""}
            worker_name = "kube-workers-{cluster}-{zone}".format(cluster=self._cluster_info['cluster_name'], zone=zone_name)
            instance_groups['workers'][zone_name] = {"name": worker_name, "url": ""}
            if not self._args.dryrun:
                instance_groups['masters'][zone_name]['url'] = buttlib.gce.instance_groups.create(self.client, zone_name, master_name, self.__network_url)
                instance_groups['workers'][zone_name]['url'] = buttlib.gce.instance_groups.create(self.client, zone_name, worker_name, self.__network_url)
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")
        return instance_groups

    def __create_internal_lb(self, lb_settings, instance_groups):
        backend_url = buttlib.gce.gce_network.create_internal_backend_service(self.__gce_conn, self._env_info['project'], self._env_info['region'], lb_settings['name'], instance_groups, lb_settings['hcport'])
        buttlib.gce.gce_network.create_forwarding_rule(
            self.__gce_conn,
            self._env_info['project'],
            self._env_info['region'],
            self._cluster_info['master_lb_name'],
            backend_url,
            lb_settings['proto'],
            lb_settings['lbports'],
            self.__network_url,
            internal=True,
            ip=lb_settings['ip'])

    def __create_external_lb(self, lb_settings):
        backend_url = buttlib.gce.gce_network.create_target_pool(
            self.__gce_conn, lb_settings['name'], self._env_info['project'],
            self._env_info['region'], lb_settings['hcport'])
        buttlib.gce.gce_network.create_forwarding_rule(
            self.__gce_conn, self._env_info['project'],
            self._env_info['region'], lb_settings['name'], backend_url,
            lb_settings['schema'], lb_settings['lbports'])

    def __create_load_balancers(self, instance_groups):
        buttlib.helpers.BColors().bcprint("Creating load balancers ...",
                                          "HEADER")
        if not self._args.dryrun:
            lb_settings = {
                "name": self._cluster_info['master_lb_name'],
                "proto": "tcp",
                "hcport": "443",
                "lbports": [443, 2379, 8080],
                "ip": self._cluster_info['master_ip']
            }
            self.__create_internal_lb(lb_settings, instance_groups['masters'])
            lb_settings = {
                "name": self._cluster_info['worker_lb_name'],
                "proto": "tcp",
                "hcport": "80",
                "lbports": [80,30000,30012,30014,30016,30656],
                "ip": self._cluster_info['worker_ip']
            }
            self.__create_internal_lb(lb_settings, instance_groups['workers'])

            ### EXAMPLE of external load balancer not currently needed for gce k8s setup
            # lb_settings = {
            #     "name": self._cluster_info['master_lb_name'],
            #     "proto": "tcp",
            #     "port": "80-443",
            #     "ip": self._cluster_info['master_ip'],
            #     "schema": "http",
            # }
            # self.__create_external_lb(lb_settings)
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")

    def __create_vm(self, zone, vm_config):
        operation = ""
        buttlib.helpers.BColors().bcprint(
            "Creating VM {} ... ".format(vm_config['name']), "HEADER")
        if not self._args.dryrun:
            operation = (
                self.__gce_conn.instances().insert(  #pylint:disable=E1101
                    project=self._env_info['project'],
                    zone=zone,
                    body=vm_config).execute(),
                zone)
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")
        return operation

    def __add_instance_to_groups(self, instance_groups, instances):
        buttlib.helpers.BColors().bcprint("Adding instances to groups ...",
                                          "HEADER")
        if not self._args.dryrun:
            for instance in instances:
                zone = (instance['zone'].split("/")[-1]).strip()
                if re.search("-master-", instance['targetLink']):
                    group = instance_groups['masters'][zone]['name']
                else:
                    group = instance_groups['workers'][zone]['name']
                buttlib.gce.gce_group.add_instance_to_group(
                    self.__gce_conn, self._env_info['project'], zone, group,
                    instance['targetLink'])
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")

    def __add_to_target_pool(self, instances):
        buttlib.helpers.BColors().bcprint(
            "Adding instances to target pools ...", "HEADER")
        if not self._args.dryrun:
            worker_instances = [
                {
                    "instance": instance['targetLink']
                } for instance in instances
                if not re.search("-master-", instance['targetLink'])
            ]
            buttlib.gce.gce_network.add_to_target_pool(
                self.__gce_conn, worker_instances,
                self._cluster_info['worker_lb_name'],
                self._env_info['project'], self._env_info['region'])
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")

    def __add_firewall_rules(self):
        buttlib.helpers.BColors().bcprint("Adding default firewall rules ...",
                                          "HEADER")
        if not self._args.dryrun and 'network' not in self._env_info:
            buttlib.gce.gce_network.create_firewall_rules(
                self.__gce_conn, self.__network_url,
                "{}-internal-any".format(self._cluster_info['network_name']),
                "tcp", "0-65535", [self._env_info['externalNet']],
                self._env_info['project'])
            buttlib.gce.gce_network.create_firewall_rules(
                self.__gce_conn, self.__network_url,
                "{}-office-ssh-web".format(self._cluster_info['network_name']),
                "tcp", ["22", "80", "443"], self._env_info['officeIP'],
                self._env_info['project'])
            buttlib.gce.gce_network.create_firewall_rules(
                self.__gce_conn, self.__network_url,
                "{}-health-checks".format(self._cluster_info['network_name']),
                "tcp", ["80", "443"], self._env_info['googleHealthChecks'],
                self._env_info['project'])
        buttlib.helpers.BColors().bcprint("done", "OKBLUE")

    def get_initial_cluster(self):
        """:returns: - string - etcd initial cluster string"""
        return ",".join([
            "{hostname}=http://{ip}:2380".format(ip=master['ip'], hostname=master['hostname'])
            for index, master in enumerate(self.get_master_info())
        ])

    def add_node(self, args):
        pass
        # get an ip
        # create a config?
        # create vm
        # return operation

    def build(self):
        """create the butt"""
        instances = []
        operations = []
        image = buttlib.gce.images.getFromFamily(self.client)
        region_info = buttlib.gce.regions.get(self.client)
        num_zones = len(region_info['zones'])
        self.__create_certs()
        self.__network_url = self.__create_or_get_network()
        instance_groups = self.__create_instance_groups()
        self.__create_load_balancers(instance_groups)
        for i in range(self._env_info['masters']['nodes']):
            zone = region_info['zones'][i % num_zones]
            zone_name = (zone.split("/")[-1]).strip()
            vm_config = self.generate_vm_config("masters", image['selfLink'], i, zone_name)
            if self._args.verbose:
                print(vm_config)
            operations.append((self.__create_vm(zone_name, vm_config)))
        for i in range(self._env_info['workers']['nodes']):
            # TODO: change this to add node
            # operation = add_node(config, whateverotherstuff)
            pass
            # zone = region_info['zones'][i % num_zones]
            # zone_name = (zone.split("/")[-1]).strip()
            # vm_config = self.generate_vm_config("workers", image['selfLink'], i, zone_name)
            # if self._args.verbose:
            #     print(vm_config)
            # operations.append((self.__create_vm(zone_name, vm_config)))
        if not self._args.dryrun:
            for operation in operations:
                result = buttlib.gce.gce_common.wait_for_zone_operation(
                    self.__gce_conn, self._env_info['project'], operation[1],
                    operation[0]['name'])
                if self._args.verbose:
                    print(result)
                instances.append(result)
        self.__add_instance_to_groups(instance_groups, instances)
        self.__add_to_target_pool(instances)
        self.__add_firewall_rules()

    def get_user_data(self, role, vm_info):
        """:params node_type: master or worker
        :params vm_info: dict of vm config
        :params __ssl_helper: ssl helper class instance to do stuff with certs
        :returns: string - big glob of user data"""
        user_data = ""
        self.__ssl_helper.generateHostName(vm_info['hostname'])
        ud_dict = {
            "kube_addons":
            yaml.dump(self._cluster_info['kube_addons']) % {
                **
                vm_info,
                **
                self._env_info,
                **
                self._cluster_info
            },
            "kube_manifests":
            yaml.dump(self._cluster_info['kube_manifests'][re.sub(
                r"s$", "", role)]) % {
                    **
                    vm_info,
                    **
                    self._env_info,
                    **
                    self._cluster_info
                },
            "host_pem":
            self.__ssl_helper.getInfo()["%s_pem" % vm_info['hostname']],
            "host_key":
            self.__ssl_helper.getInfo()["%s_key" % vm_info['hostname']]
        }
        if "network" in self._env_info:
            self._cluster_info['resolvconf'] = self._cluster_info['resolvconf']%(self._env_info['network'])
            self._cluster_info['hostsfile'] = self._cluster_info['hostsfile_tmpl']%(vm_info)
        if role == 'masters':
            user_data = self._cluster_info['user_data_tmpl']['master'] % (
                {**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
        else:
            user_data = self._cluster_info['user_data_tmpl']['worker'] % (
                {**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
        return user_data

    def get_kube_masters(self):
        """:returns: string"""
        return "https://{ip}".format(ip=self._cluster_info['master_ip'])

    def create_forwarding_rule(self, portrange="443", proto="TCP"):
        """create a gce forwarding rule"""
        name = "%s-fwd" % self._cluster_info['cluster_name']
        buttlib.gce.gce_network.create_forwarding_rule(
            self.__gce_conn, name, proto, portrange,
            self._cluster_info['master_lb_name'], self._env_info['region'],
            self._env_info['project'])
