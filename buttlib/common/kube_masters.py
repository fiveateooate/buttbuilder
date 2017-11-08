"""stuff about kube masters"""


class KubeMasters(object):
    def __init__(self, count, butt_ips, cluster_name, use_ips=False, ip_offset=0, hostname_format_override=None, etcd_client_port=2379, etcd_peer_port=2380):
        self.__hostname_format = hostname_format_override if hostname_format_override else "kube-master-{cluster_name}-{index:02d}"
        self.__cluster_name = cluster_name
        self.__etcd_peer_port = etcd_peer_port
        self.__etcd_client_port = etcd_client_port
        self.__count = count
        self.__use_ips = use_ips
        self.__butt_ips = butt_ips
        self.__ip_offset = ip_offset

    def masters_addrs(self):
        counter = 1
        while True:
            if counter > self.__count:
                return
            yield (self.__hostname_format.format(cluster_name=self.__cluster_name, index=counter), self.__butt_ips.get_ip(self.__ip_offset + (counter-1)))
            counter += 1

    @property
    def masters(self):
        return [(hostname, ip) for hostname, ip in self.masters_addrs()]

    @property
    def use_ips(self):
        return self.__use_ips

    @use_ips.setter
    def use_ips(self, value):
        if value is True or value is False:
            self.__use_ips = value

    @property
    def etcd_initial_cluster_string(self):
        fmt = "{hostname}=http://{hostname}:{etcd_peer_port}"
        if self.__use_ips:
            fmt = "{hostname}=http://{ip}:{etcd_peer_port}"
        return ','.join([fmt.format(hostname=hostname, ip=ip, etcd_peer_port=self.__etcd_peer_port) for hostname, ip in self.masters_addrs()])

    @property
    def k8s_masters_string(self):
        """:returns: list - k8s api endpoints"""
        fmt = "http://{hostname}"
        if self.__use_ips:
            fmt = "http://{ip}"
        return ','.join([fmt.format(hostname=hostname, ip=ip) for hostname, ip in self.masters_addrs()])

    # etcd hosts with proto
    @property
    def etcd_hosts_string(self):
        fmt = "http://{hostname}:{etcd_client_port}"
        if self.__use_ips:
            fmt = "http://{ip}:{etcd_client_port}"
        return ','.join([fmt.format(hostname=hostname, ip=ip, etcd_client_port=self.__etcd_client_port) for hostname, ip in self.masters_addrs()])

    # No proto - needed somewhere
    @property
    def etcd_endpoints_string(self):
        fmt = "{hostname}:{etcd_client_port}"
        if self.__use_ips:
            fmt = "{ip}:{etcd_client_port}"
        return ','.join([fmt.format(hostname=hostname, ip=ip, etcd_client_port=self.__etcd_client_port) for hostname, ip in self.masters_addrs()])

    @property
    def ips(self):
        return [ip for hostname, ip in self.masters_addrs()]

    @property
    def hostnames(self):
        return [hostname for hostname, ip in self.masters_addrs()]
