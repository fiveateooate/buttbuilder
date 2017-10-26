# pull the cluster_config nad load args

import requests
import pprint
import os
import yaml
import base64
#import buttlib.buttbuild_exceptions
class MissingEnvVarsError(KeyError):
    """ Raise if required env vars are not set """

    def __init__(self, value):
        KeyError.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class ClusterConfigHandler(object):
    __github_org = "weave-lab"
    __github_url = "https://api.github.com"
    __cluster_config_repo = "ops-cluster_config"
    __github_get_file_tmpl = "/repos/%s/%s/contents/%s" # repo owner/repo name/file path
    def __init__(self,cluster_env,cluster_id,cluster_config_path=None):
        self.__cluster_config_yaml = "%s/%s.yaml"%(cluster_env,cluster_id)
        if cluster_config_path:
            self.__cluster_config_path = cluster_config_path
            self.env_info = (self.loadcluster_config())["%s:%s"%(cluster_env,cluster_id)]
        else:
            if ('GITHUBUSER' not in os.environ) or ('GITHUBPASS' not in os.environ):
                raise MissingEnvVarsError("GITHUBUSER and GITHUBPASS must be exported to env")
            self.__github_username = os.environ['GITHUBUSER']
            self.__github_password = os.environ['GITHUBPASS']
            self.env_info = (self.fetchClusterInfo())["%s:%s"%(cluster_env,cluster_id)]

    def fetchClusterInfo(self):
        retval = None
        request_url = cluster_configHandler.__github_url+cluster_configHandler.__github_get_file_tmpl%(cluster_configHandler.__github_org,cluster_configHandler.__cluster_config_repo,self.__cluster_config_yaml)
        r = requests.get(request_url,auth=(self.__github_username, self.__github_password))
        if r.status_code == 200:
            file_contents = yaml.load(base64.b64decode(r.json()['content']).decode('utf-8'))
            retval = file_contents
        else:
            print(r.text)
        return retval

    def loadcluster_config(self):
        with open(self.__cluster_config_path+"/"+self.__cluster_config_yaml) as file:
            file_contents = yaml.load(file.read())
        return file_contents
