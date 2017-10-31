"""tests for KubeMasters class"""

import buttlib
import yaml


class TestKubeMasters():
    def setup_class(self):
        with open("tests/cluster-libvirt.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.butt_ips = buttlib.common.ButtIps(
            network=self.args['externalNet'])
        self.kube_masters = buttlib.common.KubeMasters(
            count=self.args['masters']['nodes'], cluster_name="bbtest-noenv", butt_ips=self.butt_ips, ip_offset=self.args['masters']['ipOffset'])

    def test_initial_cluster(self):
        print(str(self.kube_masters.etcd_initial_cluster_string))
        assert self.kube_masters.etcd_initial_cluster_string == "kube-master-bbtest-noenv-01=http://kube-master-bbtest-noenv-01:2379,kube-master-bbtest-noenv-02=http://kube-master-bbtest-noenv-02:2379"

    def test_k8s_masters_string(self):
        print(str(self.kube_masters.k8s_masters_string))
        assert self.kube_masters.k8s_masters_string == "https://kube-master-bbtest-noenv-01,https://kube-master-bbtest-noenv-02"

    def test_etcd_hosts_string(self):
        print(str(self.kube_masters.etcd_hosts_string))
        assert self.kube_masters.etcd_hosts_string == "http://kube-master-bbtest-noenv-01:2379,http://kube-master-bbtest-noenv-02:2379"

    def test_etcd_endpoints_string(self):
        print(str(self.kube_masters.etcd_endpoints_string))
        assert self.kube_masters.etcd_endpoints_string == "kube-master-bbtest-noenv-01:2379,kube-master-bbtest-noenv-02:2379"

    def test_initial_cluster_ips(self):
        self.kube_masters.use_ips = True
        print(str(self.kube_masters.etcd_initial_cluster_string))
        assert self.kube_masters.etcd_initial_cluster_string == "kube-master-bbtest-noenv-01=http://192.168.69.10:2379,kube-master-bbtest-noenv-02=http://192.168.69.11:2379"

    def test_k8s_masters_string_ips(self):
        self.kube_masters.use_ips = True
        print(str(self.kube_masters.k8s_masters_string))
        assert self.kube_masters.k8s_masters_string == "https://192.168.69.10,https://192.168.69.11"

    def test_etcd_endpoints_string_ips(self):
        self.kube_masters.use_ips = True
        print(str(self.kube_masters.etcd_endpoints_string))
        assert self.kube_masters.etcd_endpoints_string == "192.168.69.10:2379,192.168.69.11:2379"

    def test_etcd_hosts_string_ips(self):
        self.kube_masters.use_ips = True
        print(str(self.kube_masters.etcd_hosts_string))
        assert self.kube_masters.etcd_hosts_string == "http://192.168.69.10:2379,http://192.168.69.11:2379"

    def test_ips(self):
        print(self.kube_masters.ips)
        assert isinstance(self.kube_masters.ips, list) and self.kube_masters.ips[0] == '192.168.69.10'

    def test_hostnames(self):
        print(self.kube_masters.hostnames)
        assert isinstance(self.kube_masters.hostnames, list) and self.kube_masters.hostnames[0] == 'kube-master-bbtest-noenv-01'

    def test_masters(self):
        print(self.kube_masters.masters)
        assert isinstance(self.kube_masters.hostnames, list) and len(self.kube_masters.masters) == self.args['masters']['nodes']
