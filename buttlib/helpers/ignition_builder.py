import os
import glob
import re
import tempfile
import yaml
# import time
from io import StringIO
# import copy
# import json
from sh import ct


class IgnitionBuilder:
    def __init__(self, basedir="ignition", replacements_dict={}, exclude_modules=[]):
        self.__exclude_modules = exclude_modules
        self.__config = self.__build_config(basedir, basedir, {}, replacements_dict)

    def __build_config(self, confdir, basepath, config, replacements_dict):
        dir_contents = glob.glob("{}/*".format(confdir))
        for dir_item in dir_contents:
            (head, tail) = os.path.split(dir_item)
            if os.path.isdir(dir_item):
                config[tail] = self.__build_config(dir_item, basepath, {}, replacements_dict)
                if config[tail] == {}:
                    del(config[tail])
            elif re.search("\.yaml$", dir_item):
                # print("processing {}".format(dir_item))
                # skip ignored modules - used for master/worker diffs
                if tail.replace(".yaml", "") in self.__exclude_modules:
                    continue
                if config != {}:
                    config.append(self.__yaml_read(dir_item, replacements_dict)[0])
                else:
                    config = self.__yaml_read(dir_item, replacements_dict)
        return config

    @classmethod
    def __yaml_read(cls, filename, replacements_dict):
        with open(filename, 'r') as file:
            return yaml.load(file.read().format(**replacements_dict))

    @property
    def ign(self):
        return self.__config

    @ign.setter
    def ign(self, config):
        self.__config = config

    def get_ignition(self, pretty=False):
        # yamlfile = "/tmp/bb-config-{}.yaml".format(int(time.time()))
        buf = StringIO()
        with tempfile.NamedTemporaryFile() as fp:
            fp.write((yaml.dump(self.__config, default_flow_style=False)).encode())
            fp.seek(0)
            args = ["-in-file", fp.name]
            if pretty:
                args.append("-pretty")
            ct(args, _out=buf)
        return buf.getvalue()
