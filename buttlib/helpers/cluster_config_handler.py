"""
Read a yaml file to get luster config
* pulling from github is dumb, should remove
"""

import requests
import os
import yaml
import base64
import buttlib


class ClusterConfigHandler(object):
    __github_org = "weave-lab"
    __github_url = "https://api.github.com"
    __cluster_config_repo = "ops-cluster_config"
    # repo owner/repo name/file path
    __github_get_file_tmpl = "/repos/%s/%s/contents/%s"

    def __init__(self, cluster_env, cluster_id, cluster_config_path=None):
        self.__cluster_config_yaml = "{}/{}.yaml".format(cluster_env, cluster_id)
        if cluster_config_path:
            self.__cluster_config_path = cluster_config_path
            self.env_info = (self.loadcluster_config())["{}:{}".format(cluster_env, cluster_id)]
        else:
            if ('GITHUBUSER' not in os.environ) or ('GITHUBPASS' not in os.environ):
                raise buttlib.common.MissingEnvVarsError("GITHUBUSER and GITHUBPASS must be exported to env")
            self.__github_username = os.environ['GITHUBUSER']
            self.__github_password = os.environ['GITHUBPASS']
            self.env_info = (self.fetchClusterInfo())["{}:{}".format(cluster_env, cluster_id)]

    def fetchClusterInfo(self):
        retval = None
        request_url = ClusterConfigHandler.__github_url + ClusterConfigHandler.__github_get_file_tmpl % (
            ClusterConfigHandler.__github_org, ClusterConfigHandler.__cluster_config_repo, self.__cluster_config_yaml)
        r = requests.get(request_url, auth=(self.__github_username, self.__github_password))
        if r.status_code == 200:
            file_contents = yaml.load(base64.b64decode(r.son()['content']).decode('utf-8'))
            retval = file_contents
        else:
            print(r.text)
        return retval

    def loadcluster_config(self):
        with open(self.__cluster_config_path + "/" + self.__cluster_config_yaml) as file:
            file_contents = yaml.load(file.read())
        return file_contents
