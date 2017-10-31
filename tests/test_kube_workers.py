"""tests for KubeMasters class"""

import buttlib
import yaml


class TestKubeWorkers():
    def setup_class(self):
        with open("tests/cluster-libvirt.yaml") as fd:
            args = yaml.load(fd.read())
        self.args = args['noenv:buttbuildertest']
        self.butt_ips = buttlib.common.ButtIps(network=self.args['externalNet'])
        self.kube_workers = buttlib.common.KubeWorkers(
            count=self.args['workers']['nodes'], cluster_name="bbtest-noenv", provider="libvirt", butt_ips=self.butt_ips, ip_offset=self.args['workers']['ipOffset'])

    def test_workers_addrs(self):
        print(self.kube_workers.workers)
        assert isinstance(self.kube_workers.workers, list) and len(self.kube_workers.workers) == self.args['workers']['nodes']
