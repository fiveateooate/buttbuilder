""" Base class for butt builders
    implements common functionallity
"""

# import glob
# import ipaddress
import os
# import re
# import random
# import shutil
# import string
import subprocess
# import hashlib

from sh import kubectl

import buttlib


class ButtBuilder(object):
    """base class set up parameters needed by all butt builders"""
    LB_NAME_TMPLT = "lb-kube-{type}-{cluster_name}-loadbal"
    MASTER_NAME_TMPLT = "kube-master-{cluster_name}-{suffix:02d}"
    WORKER_NAME_TMPLT = "kube-worker-{cluster_name}-{suffix}"
    NETWORK_NAME_TMPLT = "net-{cluster_name}"

    def __init__(self, env_info, args, use_ips=False):
        # set some defaults needed to set some default
        # if using larger then /24 networks set some crap so buttips can create correct ips
        __subnet_mask = env_info['network']['subnetMask'] if 'network' in env_info and 'subnetMask' in env_info['network'] else 24
        __subnet_offset = env_info['network']['subnetOffset'] if 'network' in env_info and 'subnetOffset' in env_info['network'] else 0
        # used in a couple places in __init__
        __cluster_name = "{}-{}".format(args.cluster_env, args.cluster_id)
        # offset begining master ips default is 10 to allow for dns, k8s cluster ip, ...
        __master_ip_offset = env_info['masters']['ipOffset'] if 'masters' in env_info and 'ipOffset' in env_info['masters'] else 10
        # offset for beginning worker ips, leave some room for masters
        __worker_ip_offset = env_info['workers']['ipOffset'] if 'workers' in env_info and 'ipOffset' in env_info['workers'] else 30
        __buttdir_base = args.buttdir if args.buttdir is not None else os.path.expanduser("~")
        __network_name = env_info['network']['networkName'] if 'network' in env_info and 'networkName' in env_info['network'] else __cluster_name + "-net"

        # create objects used by all builders
        # save env info -- used as dict for replacement in ignition files
        self._env_info = env_info
        # args?
        self._args = args
        # get keys from $HOME/.ssh
        __ssh_pub_key_helper = buttlib.helpers.SSHKeyHelper()
        # objects to create ips from
        self._butt_ips = buttlib.common.ButtIps(network=self._env_info['externalNet'], subnet_mask=__subnet_mask, subnet_offset=__subnet_offset)
        self._cluster_internal_ips = buttlib.common.ButtIps(network=self._env_info['clusterNet'])
        # helper to return hostnames, ips in formatted strings
        self._kube_masters = buttlib.common.KubeMasters(
            count=self._env_info['masters']['nodes'],
            cluster_name=__cluster_name,
            butt_ips=self._butt_ips,
            ip_offset=__master_ip_offset,
            use_ips=use_ips
        )
        # huge dict for replacement in ignition files -- created from env_info settings
        self._cluster_info = {
            "cluster_env": args.cluster_env,
            "cluster_id": args.cluster_id,
            "cluster_name": __cluster_name,
            "dns_ip": self._cluster_internal_ips.get_ip(5),
            "master_ip": self._butt_ips.get_ip(__master_ip_offset),  # set master to first master - used to set a lb master if applicable
            "kube_master": self._butt_ips.get_ip(__master_ip_offset),  # wtf? why is this twice
            "master_port": 443,  # do we ever want anything else?
            "cluster_ip": self._cluster_internal_ips.get_ip(1),  # used in ssl certs
            "ssh_pub_keys": __ssh_pub_key_helper.get_pub_keys(),
            "dashboardFQDN": "dashboard-{}.example.com".format(args.cluster_id),
            "etcdVersion": "3.2.9",
            "etcd_hosts": self._kube_masters.etcd_hosts_string,
            "etcd_initial_cluster": self._kube_masters.etcd_initial_cluster_string,
            "kube_masters": self._kube_masters.k8s_masters_string,
            "etcdEndpoints": self._kube_masters.etcd_endpoints_string,
            "buttdir": "{}/{}".format(__buttdir_base, __cluster_name),
            "network_name": __network_name,
            "ip_offset": {
                "masters": __master_ip_offset,
                "workers": __worker_ip_offset
            },
            "kube_master_lb_ip": "",  # these can/should be set in subclass mostly here to keep things from puking
            "optionalHostnameOverride": "",
            "additionalLabels": "",
            "nameserver_config": "",
            "hostsfile": "",
            "resolvconf": "",
            "cloud_provider": "",
            "buttProvider": "",
            "network_config": "",
        }
        self._ssl_helper = buttlib.helpers.SSLHelper(self._env_info['clusterDomain'], "{}/ssl".format(self._cluster_info['buttdir']))
        # create directory for images, configs, certs, ...
        if not os.path.exists(self._cluster_info['buttdir']):
            os.makedirs(self._cluster_info['buttdir'])

    def build(self):
        # should do the following
        # create additional certs
        # create and storage, networks, ...
        # create instances
        pass

    def check_cluster(self):
        # verify cluster state ????
        pass

    # @staticmethod
    # def __read_ud_template(ud_type):
    #     try:
    #         with open("butt-templates/{}/user_data_tmpl.yaml".format(ud_type), 'r') as file:
    #             return file.read()
    #     except IOError as exc:
    #         print(exc)

    # def get_kube_masters(self):
    #     """:returns: list - k8s api endpoints"""
    #     return ','.join(
    #         ["https://%s" % (master) for master in self.get_master_hosts()])
    #
    # def get_etcd_endpoints(self):
    #     """:returns: list - etcd endpoints without http:// fo ruse by gateway"""
    #     return ','.join(
    #         ["%s:2379" % (master) for master in self.get_master_hosts()])
    #
    # def get_master_hosts(self):
    #     """:returns: list - master host names"""
    #     return [
    #         "kube-master-%s-%02d" % (self._cluster_info['cluster_name'], i + 1)
    #         for i in range(self._env_info['masters']['nodes'])
    #     ]
    #
    # def get_worker_hosts(self):
    #     """DEPRICATED - convert to non-deterministic hostnames
    #     :returns: list of worker hostsnames"""
    #     return [
    #         "kube-worker-%s-%02d" % (self._cluster_info['cluster_name'], i + 1)
    #         for i in range(self._env_info['workers']['nodes'])
    #     ]
    #
    # def get_master_ips(self):
    #     """:returns: list of master ip addresses"""
    #     if "ipOffsets" in self._cluster_info:
    #         offset = self._cluster_info['ipOffsets']['masters']
    #     else:
    #         offset = self._master_ip_offset
    #     return [
    #         str(
    #             ipaddress.IPv4Network(self._env_info['externalNet'])[i + offset])
    #         for i in range(self._env_info['masters']['nodes'])
    #     ]
    #
    # def get_initial_cluster(self):
    #     """:returns: - string - etcd initial cluster string"""
    #     masters = self.get_master_hosts()
    #     return ",".join([
    #         "%s=http://%s:2380" % (master, master)
    #         for index, master in enumerate(masters)
    #     ])
    #
    # def get_etcd_hosts(self):
    #     """:returns: string - comma delimeted string of proto://host:port"""
    #     return ",".join(
    #         ["http://%s:2379" % master for master in self.get_master_hosts()])

    # def update_kube_config(self):
    #     """ Add new context into kube config"""
    #     update = 'n'
    #     update = input("Auto update kube config? (y|n)")
    #     if update == 'y':
    #         if os.path.isfile(
    #                 "{}/.kube/config".format(os.path.expanduser("~"))):
    #             shutil.copy(
    #                 "{}/.kube/config".format(os.path.expanduser("~")),
    #                 "{}/.kube/config.bak".format(os.path.expanduser("~")))
    #         kubectl(
    #             "config", "set-cluster", "{}-{}-cluster".format(
    #                 self._cluster_info['cluster_env'],
    #                 self._cluster_info['cluster_id']),
    #             "--server=https://{}:{}".format(
    #                 self._cluster_info["kube_master"],
    #                 self._cluster_info["master_port"]),
    #             "--certificate-authority={}/ssl/ca.pem".format(self._cluster_info['buttdir']))
    #         kubectl(
    #             "config", "set-credentials", "{}-{}-admin".format(
    #                 self._cluster_info['cluster_env'],
    #                 self._cluster_info['cluster_id']),
    #             "--certificate-authority={}/ssl/ca.pem".format(self._cluster_info['buttdir']),
    #             "--client-key={}/ssl/admin-key.pem".format(self._cluster_info['buttdir']),
    #             "--client-certificate={}/ssl/admin.pem".format(self._cluster_info['buttdir']))
    #         kubectl("config", "set-context", "{}-{}-system".format(
    #             self._cluster_info['cluster_env'],
    #             self._cluster_info['cluster_id']),
    #                 "--cluster={}-{}-cluster".format(
    #                     self._cluster_info['cluster_env'],
    #                     self._cluster_info['cluster_id']),
    #                 "--user={}-{}-admin".format(
    #                     self._cluster_info['cluster_env'],
    #                     self._cluster_info['cluster_id']))
    #         kubectl("config", "use-context", "{}-{}-system".format(
    #             self._cluster_info['cluster_env'],
    #             self._cluster_info['cluster_id']))

    # def get_worker_ip(self, index):
    #     """:returns: string - ip in externalNet range"""
    #     return str(
    #         ipaddress.IPv4Network(self._env_info['externalNet'])[
    #             index + self._worker_ip_offset])

    # def get_kube_addons(self):
    #     """:returns: string - everything in butt-templates/addons converted to string"""
    #     addons = []
    #     for addon in glob.glob("butt-templates/addons/*.yaml"):
    #         with open(addon, 'r') as file:
    #             temp = file.read()
    #         if re.search("dashboard-ingress", addon):
    #             temp = temp.format(dashboardFQDN=self._cluster_info['dashboardFQDN'])
    #         addons.append({
    #             "path":
    #             "/etc/kubernetes/addons/%s" % (os.path.basename(addon)),
    #             "content":
    #             temp,
    #             "permissions":
    #             "0644",
    #             "owner":
    #             "root"
    #         })
    #     return addons

    # @staticmethod
    # def get_kube_manifests():
    #     """:returns: dict of strings - everything in butt-templates/manifets/* converted to string"""
    #     manifests = {'master': [], 'worker': []}
    #     for name in ['master', 'worker']:
    #         for manifest in glob.glob(
    #                 "butt-templates/manifests/%s/*.yaml" % name):
    #             with open(manifest, 'r') as file:
    #                 temp = file.read()
    #             manifests[name].append({
    #                 "path":
    #                 "/etc/kubernetes/manifests/%s" %
    #                 (os.path.basename(manifest)),
    #                 "content":
    #                 temp,
    #                 "permissions":
    #                 "0644",
    #                 "owner":
    #                 "root"
    #             })
    #     return manifests
