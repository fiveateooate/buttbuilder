"""build an aws butt"""

import gzip
import ipaddress
import re

import boto3
import yaml

import buttlib


class Builder(buttlib.common.ButtBuilder):
    """makes aws butts"""
    __DISK_MAPPINGS_TEMPLATE = """
        "DeviceName": "/dev/xvda"
        "Ebs":
            "VolumeSize": {VolumeSize}
            "DeleteOnTermination": True
            "VolumeType": "{VolumeType}"
    """

    def __init__(self, env_info, args):
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        self.__aws_session = boto3.Session(profile_name='weave')
        self.__aws_client = self.__aws_session.client('ec2', region_name=self._env_info['Region'])
        self.__aws_resource = self.__aws_session.resource(
            'ec2', region_name=self._env_info['Region'])
        self.__buttnet = "%s-net" % (self._cluster_info['cluster_name'])
        self.__ssl_helper = buttlib.helpers.SSLHelper(self._env_info['clusterDomain'], "%s/ssl" % self._cluster_info['buttdir'])
        # self._master_ip_offset = 30
        # self._worker_ip_offset = 50
        self._cluster_info['network_name'] = "net-%s" % self._cluster_info[
            'cluster_name']
        self._cluster_info['ip'] = "$private_ipv4"
        self._cluster_info['master_ip'] = str(
            ipaddress.IPv4Network(self._env_info['externalNet'])[2])
        self._cluster_info['kube_masters'] = self.get_kube_masters()
        self.__ip_offset = {'masters': 10, "workers": 30}
        self._cluster_info['master_ip'] = "10.250.250.10" # "lb-kube-masters-{}".format(self._cluster_info['cluster_id'])
        self._cluster_info['cloud_provider'] = "aws"

    def __get_ami(self):
        response = self.__aws_client.describe_images(
            Owners=["595879546273"],
            Filters=[{
                "Name": "architecture",
                "Values": ["x86_64"]
            }, {
                "Name": "virtualization-type",
                "Values": ["hvm"]
            }])

        temp = []
        for image in response['Images']:
            if re.search(r"CoreOS-stable.*", image['Name']):
                temp.append(image)
        temp.sort(key=lambda r: r['CreationDate'])
        return temp[-1]['ImageId']

    def get_user_data(self, node_type, vm_info):
        """:returns" string - big long string of user data"""
        self.__ssl_helper.generateHost(vm_info['hostname'], vm_info['ip'])
        user_data = ""
        ud_dict = {
            "kube_addons": yaml.dump(self._cluster_info['kube_addons']) % {**vm_info, **self._env_info, **self._cluster_info},
            "kube_manifests": yaml.dump(self._cluster_info['kube_manifests'][node_type]) % {**vm_info, **self._env_info, **self._cluster_info},
            "host_pem": self.__ssl_helper.getInfo()["%s_pem" % vm_info['hostname']],
            "host_key": self.__ssl_helper.getInfo()["%s_key" % vm_info['hostname']]
        }
        if node_type == 'master':
            user_data = self._cluster_info['user_data_tmpl']['master'] % ({**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
        else:
            user_data = self._cluster_info['user_data_tmpl']['worker'] % ({**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
        # return gzip.compress(user_data.encode('utf-8'))
        return user_data

    def __get_availability_zones(self):
        response = self.__aws_client.describe_availability_zones()
        return response['AvailabilityZones']

    def __get_disk_map(self, host_type, hostname):
        return yaml.load(
            Builder.__DISK_MAPPINGS_TEMPLATE.format(**self._env_info[
                host_type], **{"hostname": hostname}))

    def get_kube_masters(self):
        """:returns: list - k8s api endpoints"""
        ips = self.get_master_ips()
        return ','.join(
            ["https://%s" % (master) for master in self.get_aws_master_hosts(ips)])

    def __get_network_interface(self):  # maybe don't need
        pass

    @staticmethod
    def __make_aws_hostname(ip_address):
        return "ip-{formatted_ip}".format(formatted_ip=re.sub(r"\.", "-", ip_address))

    def __make_hostname(self, index, role):
        return "kube-{role}-{cluster_id}-{suffix:02d}".format(cluster_id=self._cluster_info['cluster_id'], suffix=index + 1, role=role)

    def __make_worker_hostname(self):
        return "kube-worker-{cluster_name}-{suffix}".format(cluster_name=self._cluster_info['cluster_name'], suffix=self.get_hostname_suffix())

    def __make_master_hostname(self, index):
        return "kube-master-{cluster_name}-{suffix:02d}".format(cluster_name=self._cluster_info['cluster_name'], suffix=index + 1)

    def __write_user_data(self, vm_info):
        ud_filename = "{buttdir}/{hostname}.user_data.yaml".format(buttdir=self._cluster_info['buttdir'], hostname=vm_info['hostname'])
        with open(ud_filename, "w") as file:
            file.write(vm_info['UserData'])

    def get_master_hosts(self):
        return [
            "kube-master-{cluster_id}-{suffix:02d}".format(
                cluster_id=self._cluster_info['cluster_id'], suffix=i + 1)
            for i in range(self._env_info['masters']['nodes'])
        ]

    def get_aws_master_hosts(self, ips):
        return [
            "ip-{}".format(re.sub(r"\.", "-", ip))
            for ip in ips
        ]

    def get_etcd_hosts(self):
        return ",".join(["http://{}:2379".format(ip) for ip in self.get_master_ips()])

    def get_initial_cluster(self):
        ips = self.get_master_ips()
        #hosts = self.get_master_hosts()
        hosts = self.get_aws_master_hosts(ips)
        return ",".join(["{}=http://{}:2380".format(hosts[i], ips[i]) for i in range(len(hosts))])

    def get_master_ips(self):
        return [str(ipaddress.IPv4Network(self._env_info['externalNet'])[i + 10]) for i in range(self._env_info['masters']['nodes'])]

    def get_vm_config(self, index, zone, role):
        """gather up vm specific crap
        :returns: dict - info for one vm
        """
        vm_info = {}
        #vm_info['hostname'] = self.__make_hostname(index, re.sub("s$", "", role))
        vm_info['ip'] = str(
            ipaddress.IPv4Network(self._env_info['externalNet'])[
                index + self.__ip_offset[role]])
        vm_info['hostname'] = self.__make_aws_hostname(vm_info['ip'])
        vm_info['Placement'] = {"AvailabilityZone": zone}
        vm_info['InstanceType'] = self._env_info[role]['InstanceType']
        vm_info['BlockDeviceMappings'] = [self.__get_disk_map(
            role, vm_info['hostname'])]
        vm_info[
            'additionalLabels'] = ",failure-domain.beta.kubernetes.io/region={},failure-domain.beta.kubernetes.io/zone={}".format(
                self._env_info['Region'], zone)
        vm_info['TagSpecifications'] = [{'ResourceType': 'instance', 'Tags':[{"Key": "Name", "Value": vm_info['hostname']}, {"Key": "cluster-role", "Value": re.sub(r"s$", "", role)}]}]
        vm_info['NetworkInterfaces'] = [{
            "SubnetId": self._env_info['SubnetId'],
            "PrivateIpAddress": vm_info['ip'],
            "DeviceIndex": 0,
            "Groups": self._env_info[role]['SecurityGroupIds']
        }]
        vm_info['UserData'] = self.get_user_data(
            re.sub(r"s$", "", role), vm_info)
        return vm_info

    def build(self):
        """build a k8s butt in aws"""
        instances = []
        hostnames = self.get_master_hosts()
        hostnames.append(self._cluster_info['master_ip'])
        self.__ssl_helper.createCerts(self.get_master_ips(),
                                      self._cluster_info["cluster_ip"],
                                      hostnames)
        ami = self.__get_ami()
        availability_zones = self.__get_availability_zones()
        for cluster_role in ['masters', 'workers']:
            for index in range(self._env_info[cluster_role]['nodes']):
                zone = self._env_info['Zone'] if 'Zone' in self._env_info else availability_zones[index % len(availability_zones)]['ZoneName']
                vm_info = self.get_vm_config(index, zone, cluster_role)
                vm_info['ami'] = ami
                self.__write_user_data(vm_info)
                vm_info['UserData'] = gzip.compress(vm_info['UserData'].encode('utf-8'))
                instances.append(self.__aws_resource.create_instances(
                    DryRun=self._args.dryrun,
                    MinCount=1,
                    MaxCount=1,
                    ImageId=ami,
                    UserData=vm_info['UserData'],
                    InstanceType=vm_info['InstanceType'],
                    Placement=vm_info['Placement'],
                    NetworkInterfaces=vm_info['NetworkInterfaces'],
                    BlockDeviceMappings=vm_info['BlockDeviceMappings'],
                    TagSpecifications=vm_info['TagSpecifications']))
        for instance in instances:
            print(instance)
