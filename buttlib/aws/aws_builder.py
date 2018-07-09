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
        self._cluster_info['ip'] = "$private_ipv4"
        self._cluster_info['kube_master_lb_ip'] = self._env_info['masterLBName']
        self._cluster_info['buttProvider'] = "aws"
        self.__s3_url = self._env_info['s3URL']
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
