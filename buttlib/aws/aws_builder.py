"""build an aws butt"""

# import ipaddress
import re
import sys
import boto3
import yaml
import json

import buttlib


class Builder(buttlib.common.ButtBuilder):
    """makes aws butts"""
    __DISK_MAPPINGS_TEMPLATE = """
        "DeviceName": "/dev/xvda"
        "Ebs":
            "VolumeSize": {disk}
            "DeleteOnTermination": True
            "VolumeType": "{VolumeType}"
    """

    def __init__(self, env_info, args):
        buttlib.common.ButtBuilder.__init__(self, env_info, args)
        if args.awsprofile is None:
            raise buttlib.common.MissingCredentialsError("missing aws profile")
        self.__aws_session = boto3.Session(profile_name=args.awsprofile)
        self.__aws_client = self.__aws_session.client('ec2', region_name=self._env_info['Region'])
        self.__aws_resource = self.__aws_session.resource('ec2', region_name=self._env_info['Region'])
        self.__s3_client = self.__aws_session.client("s3", region_name=self._env_info['Region'])
        self.__bucket_name = self._env_info['ignBucket']
        # self.__buttnet = "{}-net".format(self._cluster_info['cluster_name'])
        # self.__ssl_helper = buttlib.helpers.SSLHelper(self._env_info['clusterDomain'], "{}/ssl".format(self._cluster_info['buttdir']))
        # self._master_ip_offset = 30
        # self._worker_ip_offset = 50
        # self._cluster_info['network_name'] = "net-{}".format(self._cluster_info['cluster_name'])
        self._cluster_info['ip'] = "$private_ipv4"
        # self._cluster_info['master_ip'] = str(ipaddress.IPv4Network(self._env_info['externalNet'])[2])
        self._cluster_info['kube_master_lb_ip'] = self._env_info['masterLBName']
        # self._cluster_info['kube_masters'] = self.get_kube_masters()
        # self.__ip_offset = {'masters': 10, "workers": 30}
        # self._cluster_info['master_ip'] = "10.250.250.10" # "lb-kube-masters-{}".format(self._cluster_info['cluster_id'])
        self._cluster_info['buttProvider'] = "aws"
        self.__s3_url = "s3.amazonaws.com"
        self.__s3_schema = "https"

    def __get_ami(self):
        response = self.__aws_client.describe_images(
            Owners=["595879546273"],
            Filters=[
                {"Name": "architecture", "Values": ["x86_64"]},
                {"Name": "virtualization-type", "Values": ["hvm"]}
            ]
        )
        temp = []
        for image in response['Images']:
            if re.search(r"CoreOS-stable.*", image['Name']):
                temp.append(image)
        temp.sort(key=lambda r: r['CreationDate'])
        return temp[-1]['ImageId']

    # def get_user_data(self, node_type, vm_info):
    #     """:returns" string - big long string of user data"""
    #     self.__ssl_helper.generateHost(vm_info['hostname'], vm_info['ip'])
    #     user_data = ""
    #     ud_dict = {
    #         "kube_addons": yaml.dump(self._cluster_info['kube_addons']) % {**vm_info, **self._env_info, **self._cluster_info},
    #         "kube_manifests": yaml.dump(self._cluster_info['kube_manifests'][node_type]) % {**vm_info, **self._env_info, **self._cluster_info},
    #         "host_pem": self.__ssl_helper.getInfo()["%s_pem" % vm_info['hostname']],
    #         "host_key": self.__ssl_helper.getInfo()["%s_key" % vm_info['hostname']]
    #     }
    #     if node_type == 'master':
    #         user_data = self._cluster_info['user_data_tmpl']['master'] % ({**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
    #     else:
    #         user_data = self._cluster_info['user_data_tmpl']['worker'] % ({**vm_info, **self._cluster_info, **self._env_info, **(self.__ssl_helper.getInfo()), **ud_dict})
    #     # return gzip.compress(user_data.encode('utf-8'))
    #     return user_data

    def __get_availability_zones(self):
        response = self.__aws_client.describe_availability_zones()
        return response['AvailabilityZones']

    def __get_disk_map(self, host_type, hostname):
        return yaml.load(Builder.__DISK_MAPPINGS_TEMPLATE.format(**self._env_info[host_type], **{"hostname": hostname}))

    def __pre_build(self):
        masters = self._kube_masters.hostnames
        masters.append(self._cluster_info['kube_master_lb_ip'])
        self._ssl_helper.create_or_load_certs(self._kube_masters.ips, self._cluster_info["cluster_ip"], masters)
        self.__availability_zones = self.__get_availability_zones()
        self.__ami = self.__get_ami()
    # def get_kube_masters(self):
    #     """:returns: list - k8s api endpoints"""
    #     ips = self.get_master_ips()
    #     return ','.join(
    #         ["https://%s" % (master) for master in self.get_aws_master_hosts(ips)])

    # def __get_network_interface(self):  # maybe don't need
    #     pass
    #
    # @staticmethod
    # def __make_aws_hostname(ip_address):
    #     return "ip-{formatted_ip}".format(formatted_ip=re.sub(r"\.", "-", ip_address))
    #
    # def __make_hostname(self, index, role):
    #     return "kube-{role}-{cluster_id}-{suffix:02d}".format(cluster_id=self._cluster_info['cluster_id'], suffix=index + 1, role=role)
    #
    # def __make_worker_hostname(self):
    #     return "kube-worker-{cluster_name}-{suffix}".format(cluster_name=self._cluster_info['cluster_name'], suffix=self.get_hostname_suffix())
    #
    # def __make_master_hostname(self, index):
    #     return "kube-master-{cluster_name}-{suffix:02d}".format(cluster_name=self._cluster_info['cluster_name'], suffix=index + 1)
    #
    # def __write_user_data(self, vm_info):
    #     ud_filename = "{buttdir}/{hostname}.user_data.yaml".format(buttdir=self._cluster_info['buttdir'], hostname=vm_info['hostname'])
    #     with open(ud_filename, "w") as file:
    #         file.write(vm_info['UserData'])
    #
    # def get_master_hosts(self):
    #     return [
    #         "kube-master-{cluster_id}-{suffix:02d}".format(
    #             cluster_id=self._cluster_info['cluster_id'], suffix=i + 1)
    #         for i in range(self._env_info['masters']['nodes'])
    #     ]
    #
    # def get_aws_master_hosts(self, ips):
    #     return [
    #         "ip-{}".format(re.sub(r"\.", "-", ip))
    #         for ip in ips
    #     ]
    #
    # def get_etcd_hosts(self):
    #     return ",".join(["http://{}:2379".format(ip) for ip in self.get_master_ips()])
    #
    # def get_initial_cluster(self):
    #     ips = self.get_master_ips()
    #     # hosts = self.get_master_hosts()
    #     hosts = self.get_aws_master_hosts(ips)
    #     return ",".join(["{}=http://{}:2380".format(hosts[i], ips[i]) for i in range(len(hosts))])

    # def get_master_ips(self):
    #     return [str(ipaddress.IPv4Network(self._env_info['externalNet'])[i + 10]) for i in range(self._env_info['masters']['nodes'])]
    #
    # def get_vm_config(self, index, zone, role):
    #     """gather up vm specific crap
    #     :returns: dict - info for one vm
    #     """
    #     vm_info = {}
    #     # vm_info['hostname'] = self.__make_hostname(index, re.sub("s$", "", role))
    #     vm_info['ip'] = str(
    #         ipaddress.IPv4Network(self._env_info['externalNet'])[
    #             index + self.__ip_offset[role]])
    #     vm_info['hostname'] = self.__make_aws_hostname(vm_info['ip'])
    #     vm_info['Placement'] = {"AvailabilityZone": zone}
    #     vm_info['InstanceType'] = self._env_info[role]['InstanceType']
    #     vm_info['BlockDeviceMappings'] = [self.__get_disk_map(
    #         role, vm_info['hostname'])]
    #     vm_info[
    #         'additionalLabels'] = ",failure-domain.beta.kubernetes.io/region={},failure-domain.beta.kubernetes.io/zone={}".format(
    #             self._env_info['Region'], zone)
    #     vm_info['TagSpecifications'] = [{'ResourceType': 'instance', 'Tags':[{"Key": "Name", "Value": vm_info['hostname']}, {"Key": "cluster-role", "Value": re.sub(r"s$", "", role)}]}]
    #     vm_info['NetworkInterfaces'] = [{
    #         "SubnetId": self._env_info['SubnetId'],
    #         "PrivateIpAddress": vm_info['ip'],
    #         "DeviceIndex": 0,
    #         "Groups": self._env_info[role]['SecurityGroupIds']
    #     }]
    #     vm_info['UserData'] = self.get_user_data(
    #         re.sub(r"s$", "", role), vm_info)
    #     return vm_info

    def __provider_additional(self, index, ip, hostname, role):
        zone = self._env_info['Zone'] if 'Zone' in self._env_info else self.__availability_zones[index % len(self.__availability_zones)]['ZoneName']
        temp = {
            "InstanceType": self._env_info[role]['InstanceType'],
            "Placement": {"AvailabilityZone": zone},
            "NetworkInterfaces": [{
                "SubnetId": self._env_info['SubnetId'],
                "PrivateIpAddress": ip,
                "DeviceIndex": 0,
                "Groups": self._env_info[role]['SecurityGroupIds']
            }],
            "BlockDeviceMappings": [self.__get_disk_map(role, hostname)],
            "TagSpecifications": [
                {
                    'ResourceType': 'instance', 'Tags': [
                        {"Key": "Name", "Value": hostname},
                        {"Key": "cluster-role", "Value": re.sub(r"s$", "", role)},
                        {"Key": "kubernetes.io/cluster/{}".format(self._cluster_info['cluster_id']), "Value": "owned"}
                    ]
                }
            ],
            "IamInstanceProfile": {
                'Arn': self._env_info['IAMARN']
                # 'Name': self._env_info['IAMName']
            }
        }
        return temp

    def __ign_replace_config(self, bic):
        replace_ign = {
            "ignition": {
                "version": "2.2.0",
                "config": {
                    "replace": {
                        "source": "{}://{}/{}/{}.ign".format(self.__s3_schema, self.__s3_url, self.__bucket_name, bic.instance_config['hostname']),
                        "verification": {
                            "hash": "sha512-{}".format(bic.ign_sha512)
                            }
                        }
                    }
                }
            }
        return json.dumps(replace_ign)

    def upload_ign(self, filepath, hostname):
        filename = "{}.ign".format(hostname)
        extra_args = {
            'ACL': 'public-read'
        }
        self.__s3_client.upload_file(filepath, self.__bucket_name, filename, ExtraArgs=extra_args)

    def __create_vm(self, bic):
        replace_ign = self.__ign_replace_config(bic)
        cmd = "instances.append(self.__aws_resource.create_instances "
        cmd += "DryRun={}, ".format(self._args.dryrun)
        cmd += "MinCount=1, MaxCount=1, "
        cmd += "ImageId={}, ".format(self.__ami)
        cmd += "UserData={}, ".format(replace_ign)
        cmd += "InstanceType={}, ".format(bic.instance_config['InstanceType'])
        cmd += "Placement={}, ".format(bic.instance_config['Placement'])
        cmd += "NetworkInterfaces={}, ".format(bic.instance_config['NetworkInterfaces'])
        cmd += "BlockDeviceMappings={}, ".format(bic.instance_config['BlockDeviceMappings'])
        cmd += "TagSpecifications={}, ".format(bic.instance_config['TagSpecifications'])
        cmd += "IamInstanceProfile={}".format(bic.instance_config['IamInstanceProfile'])
        cmd += ")"
        print(cmd)
        instance = self.__aws_resource.create_instances(
            DryRun=self._args.dryrun,
            MinCount=1,
            MaxCount=1,
            ImageId=self.__ami,
            UserData=replace_ign,
            InstanceType=bic.instance_config['InstanceType'],
            Placement=bic.instance_config['Placement'],
            NetworkInterfaces=bic.instance_config['NetworkInterfaces'],
            BlockDeviceMappings=bic.instance_config['BlockDeviceMappings'],
            TagSpecifications=bic.instance_config['TagSpecifications'],
            IamInstanceProfile=bic.instance_config['IamInstanceProfile']
        )
        return instance

    def build(self):
        """build a k8s butt in aws"""
        print("Building aws cluster")
        self.__pre_build()
        instances = []
        index = 0
        for hostname, ip in self._kube_masters.masters:
            provider_additional = self.__provider_additional(index, ip, hostname, 'masters')
            bic = buttlib.common.ButtInstanceConfig(
                hostname,
                ip,
                'masters',
                self._ssl_helper,
                self._env_info,
                self._cluster_info,
                platform="ec2",
                provider_additional=provider_additional
            )
            # write out the config
            bic.write_ign()
            self.upload_ign(bic.instance_config['filename'], hostname)
            instances.append(self.__create_vm(bic))
            index += 1
        index = 0
        for hostname, ip in self._kube_workers.workers:
            provider_additional = self.__provider_additional(index, ip, hostname, 'workers')
            bic = buttlib.common.ButtInstanceConfig(
                hostname,
                ip,
                'workers',
                self._ssl_helper,
                self._env_info,
                self._cluster_info,
                platform="ec2",
                provider_additional=provider_additional
            )
            bic.write_ign()
            self.upload_ign(bic.instance_config['filename'], hostname)
            instances.append(self.__create_vm(bic))
            index += 1
        for instance in instances:
            print(instance)
