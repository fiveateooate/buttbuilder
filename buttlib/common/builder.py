""" Base class for butt builders
    implements common functionallity
"""

import os
import subprocess
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
        __cluster_name = "{}-{}".format(args.cenv, args.cid)
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
        self._kube_workers = buttlib.common.KubeWorkers(
            count=self._env_info['workers']['nodes'],
            cluster_name=__cluster_name,
            butt_ips=self._butt_ips,
            ip_offset=__worker_ip_offset,
            provider=self._env_info['provider']
        )
        # huge dict for replacement in ignition files -- created from env_info settings
        self._cluster_info = {
            "cluster_env": args.cenv,
            "cluster_id": args.cid,
            "cluster_name": __cluster_name,
            "dns_ip": self._cluster_internal_ips.get_ip(5),
            "master_ip": self._butt_ips.get_ip(__master_ip_offset),  # set master to first master - used to set a lb master if applicable
            "kube_master": self._butt_ips.get_ip(__master_ip_offset),  # wtf? why is this twice
            "master_port": 443,  # do we ever want anything else?
            "cluster_ip": self._cluster_internal_ips.get_ip(1),  # used in ssl certs
            "ssh_pub_keys": __ssh_pub_key_helper.get_pub_keys(),
            "dashboardFQDN": "dashboard-{}.example.com".format(args.cid),
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
