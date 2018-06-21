"""info about kube workers"""

import buttlib


# sorta not so simialr to kube_masters, an actual list of workers
class KubeWorkers(object):
    def __init__(self, count, butt_ips, cluster_name, provider=None, ip_offset=0, hostname_format_override=None):
        self.__workers = self.fetch_existing_workers(provider)
        self.__count = count
        self.__cluster_name = cluster_name
        self.__provider = provider
        self.__butt_ips = butt_ips
        self.__ip_offset = ip_offset
        self.__hostname_format = hostname_format_override if hostname_format_override else "kube-worker-{cluster_name}-{suffix}"
        self.__random_hostname = True if provider is 'libvirt' else False
        while len(self.__workers) < self.__count:
            self.__workers.append(self.generate_worker(len(self.__workers)))

    # call provider fetch existing function? this is screwy
    def fetch_existing_workers(self, provider):
        # do something like -
        # buttlib.provider.builder.fetch_workers()
        return []

    def generate_worker(self, offset):
        ip = self.__butt_ips.get_ip(self.__ip_offset + offset)
        suffix = buttlib.common.random_hostname_suffix() if self.__random_hostname else "{:02d}".format(offset+1)
        hostname = self.__hostname_format.format(cluster_name=self.__cluster_name, suffix=suffix)
        return (hostname, ip)

    @property
    def workers(self):
        return self.__workers
