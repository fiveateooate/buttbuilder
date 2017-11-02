"""tests for buttlib.common.butt_instance"""


import buttlib
import pytest
import yaml
import os


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


class TestButtInstanceConfig():
    def setup_class(self):
        args = Struct(**{"cluster_id": "buttbuildertest", "cluster_env": "noenv", "buttdir": os.getcwd()})
        with open("tests/cluster-libvirt.yaml") as fd:
            env_info = yaml.load(fd.read())
        self._env_info = env_info['noenv:buttbuildertest']
        self._builder = buttlib.common.ButtBuilder(self._env_info, args)
        self._builder._ssl_helper.create_or_load_certs(self._builder._kube_masters.ips, self._builder._cluster_info["cluster_ip"], self._builder._kube_masters.hostnames)

    def test_butt_instance_master(self):
        hostname = "kube-master-{}-01".format(self._builder._cluster_info['cluster_name'])
        ip = self._builder._butt_ips.get_ip(10)
        result = buttlib.common.ButtInstanceConfig(hostname, ip, 'masters', self._builder._ssl_helper, self._env_info, self._builder._cluster_info)
        print(result.ign)
        assert isinstance(result, buttlib.common.butt_instance_config.ButtInstanceConfig) and result.instance_config['clusterRole'] == 'master'

    def test_butt_instance_worker(self):
        hostname = "kube-worker-{}-01".format(self._builder._cluster_info['cluster_name'])
        ip = self._builder._butt_ips.get_ip(10)
        result = buttlib.common.ButtInstanceConfig(hostname, ip, 'workers', self._builder._ssl_helper, self._env_info, self._builder._cluster_info)
        print(result.ign)
        assert isinstance(result, buttlib.common.butt_instance_config.ButtInstanceConfig) and result.instance_config['clusterRole'] == 'worker'

    def test_butt_instance_bad_role_throws_exception(self):
        try:
            hostname = "kube-worker-{}-01".format(self._builder._cluster_info['cluster_name'])
            ip = self._builder._butt_ips.get_ip(10)
            result = buttlib.common.ButtInstanceConfig(hostname, ip, 'blurg', self._builder._ssl_helper, self._env_info, self._builder._cluster_info)
            print(result)
        except buttlib.exceptions.UnknownRoleError as exc:
            result = exc
        assert str(result) == "'blurg'"
