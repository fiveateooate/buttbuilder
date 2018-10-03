"""hold config and whatevers for instance"""

import buttlib
import hashlib


class ButtInstanceConfig(object):
    __DEFAULT_EXCLUDE_MODULES__ = {
        "masters": [
            "etcd-gateway"
        ],
        "workers": [
            "kube-apiserver",
            "kube-controller-manager",
            "addon-manager",
            "kube-scheduler",
            "etcd"
        ]
    }
    ___ALLOWED_ROLES__ = ['masters', 'workers']

    # the whole point of this is to create the ign
    def __init__(self, hostname, ip, role, ssl_helper, env_info, cluster_info, mac=None, platform="custom", exclude_modules=[], provider_additional=None, additional_labels=[]):
        if role not in ButtInstanceConfig.___ALLOWED_ROLES__:
            raise buttlib.exceptions.UnknownRoleError(role)
        __exclude_modules = exclude_modules if exclude_modules else ButtInstanceConfig.__DEFAULT_EXCLUDE_MODULES__[role]
        ssl_helper.generateHost(hostname, ip)
        self.__buttdir = cluster_info['buttdir']
        self.__instance_config = {
            "role": role,
            "hostname": hostname,
            "buttdir": cluster_info['buttdir'],
            "mac": mac if mac is not None else buttlib.common.random_mac(),
            "ip": ip,
            "disk": env_info[role]['disk'],
            "ram": env_info[role]['ram'] if 'ram' in env_info[role] else None,
            "cpus": env_info[role]['cpus'] if 'cpus' in env_info[role] else None,
            "additionalLabels": ','.join(cluster_info['additionalLabels'] + additional_labels),
            "exclude_modules": __exclude_modules,
            "host_pem": ssl_helper.getInfo()["{}_pem".format(hostname)],
            "host_key": ssl_helper.getInfo()["{}_key".format(hostname)],
            "api_pem": ssl_helper.getInfo()["api_pem"],
            "api_key": ssl_helper.getInfo()["api_key"],
            "ca_pem": ssl_helper.getInfo()["ca_pem"],
            "ca_key": ssl_helper.getInfo()["ca_key"],
            "ign": "",
            "network_name": cluster_info['network_name'],
            "filename": "{}/{}.ign".format(self.__buttdir, hostname)
        }
        # set role specific stuff, if bad role given fail constructor
        if role == 'masters':
            self.__instance_config.update({
                "kubeletRegistration": "--register-with-taints=node.alpha.kubernetes.io/ismaster=:NoSchedule",
                "kubeAPIServer": "http://127.0.0.1:8080",
                "etcdProxy": "off",
                "clusterRole": "master",
            })
        elif role == 'workers':
            self.__instance_config.update({
                "kubeletRegistration": "--register-node=true",
                "etcdProxy": "on",
                "kubeAPIServer": "https://{}:443".format(cluster_info['kube_master_lb_ip']),
                "clusterRole": "worker"
            })
        # append a dict of provider specific config - maybe if I did this right not needed?
        if provider_additional is not None:
            self.__instance_config.update(provider_additional)
        # now that all the info is set lets make an ignition
        __replacements_dict = {**env_info, **cluster_info, **self.__instance_config}
        self.__instance_config['ign'] = buttlib.helpers.IgnitionBuilder(
            replacements_dict=__replacements_dict,
            exclude_modules=__exclude_modules
        ).get_ignition(platform=platform)
        self.__ign_sha512 = hashlib.sha512(self.__instance_config['ign'].encode('utf-8')).hexdigest()

    @property
    def instance_config(self):
        return self.__instance_config

    @instance_config.setter
    def instance_config(self, value):
        self.__instance_config = value

    @property
    def ign(self):
        return self.__instance_config['ign']

    @property
    def ign_sha512(self):
        return self.__ign_sha512

    @property
    def role(self):
        return self.__instance_config['role']

    @property
    def hostname(self):
        return self.__instance_config['hostname']

    @property
    def ip(self):
        return self.__instance_config['ip']

    def write_ign(self):
        with open(self.__instance_config['filename'], "w+b") as fp:
            fp.write(self.__instance_config['ign'].encode())

    # these don't belong here
    # comment to remind me
    def make_awsy(self):
        pass

    def make_gcey(self):
        # make ign work on gce
        pass

    # or could I do something like ?
    def convert_ign_for_provider(self, provider, function):
        # buttlib.provider.function()
        pass
