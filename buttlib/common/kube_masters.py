"""stuff about kube masters"""


class KubeMasters(object):
    def __init__(self, count, butt_ips, cluster_name, use_ips=False, ip_offset=0, hostname_format_override=None, etcd_port=2379):
        self.__hostname_format = hostname_format_override if hostname_format_override else "kube-master-{cluster_name}-{index:02d}"
        self.__cluster_name = cluster_name
        self.__etcd_port = etcd_port
        self.__count = count
        self.__use_ips = use_ips
        self.__butt_ips = butt_ips
        self.__ip_offset = ip_offset

    def __masters_addrs(self):
        counter = 1
        while True:
            if counter > self.__count:
                return
            yield (self.__hostname_format.format(cluster_name=self.__cluster_name, index=counter), self.__butt_ips.get_ip(self.__ip_offset + (counter-1)))
            counter += 1

    @property
    def use_ips(self):
        return self.__use_ips

    @use_ips.setter
    def use_ips(self, value):
        if value is True or value is False:
            self.__use_ips = value

    @property
    def etcd_initial_cluster_string(self):
        fmt = "{hostname}=http://{hostname}:{etcd_port}"
        if self.__use_ips:
            fmt = "{hostname}=http://{ip}:{etcd_port}"
        return ','.join([fmt.format(hostname=hostname, ip=ip, etcd_port=self.__etcd_port) for hostname, ip in self.__masters_addrs()])

    @property
    def k8s_masters_string(self):
        """:returns: list - k8s api endpoints"""
        fmt = "https://{hostname}"
        if self.__use_ips:
            fmt = "https://{ip}"
        return ','.join([fmt.format(hostname=hostname, ip=ip) for hostname, ip in self.__masters_addrs()])

    @property
    def etcd_endpoints_string(self):
        fmt = "http://{hostname}:{etcd_port}"
        if self.__use_ips:
            fmt = "http://{ip}:{etcd_port}"
        return ','.join([fmt.format(hostname=hostname, ip=ip, etcd_port=self.__etcd_port) for hostname, ip in self.__masters_addrs()])
