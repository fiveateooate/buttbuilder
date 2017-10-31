"""various functions that might be helpful between  modules"""
import re
import os
import random
import string
import shutil
import subprocess
from sh import kubectl


def random_mac():
    """:returns: string - random mac starting 52:54:00"""
    mac = [
        0x52, 0x54, 0x00, random.randint(0x00, 0x7f), random.randint(
            0x00, 0xff), random.randint(0x00, 0xff)
    ]
    return ':'.join(map(lambda x: ":02x".format(x), mac))


def random_hostname_suffix(suffix_length=5):
    """:returns: string - random string of chars"""
    return ''.join(
        random.choice(string.ascii_lowercase + string.digits)
        for _ in range(suffix_length))


def fetch_coreos_image(save_location, channel="stable", image="coreos_production_qemu_image.img.bz2"):
    """downloads the CoreOS image"""
    coreos_image_url = "https://{channel}.release.core-os.net/amd64-usr/current/{image}".format(channel=channel, image=image)
    download = 'y'
    print("Fetching CoreOS image")
    # assuming there is bz2, gz, ... something on the end of the image
    full_filename = "{loc}/{file}".format(loc=save_location, file='.'.join(image.split('.')[:-1]))
    if os.path.isfile(full_filename):
        download = input("{} exists, download anyway? (y|n) ".format(full_filename))
    if download == 'y':
        cmd = "curl -sSL {coreos_url} | bzcat > {full_filename}".format(coreos_url=coreos_image_url, full_filename=full_filename)
        print(cmd)
        subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)


def update_kube_config(cluster_name, buttdir, master_string):
    """ Add new context into kube config"""
    user_dir = os.path.expanduser("~")
    update = 'n'
    update = input("Add {} cluster to kube config? (y|n) ".foramt(cluster_name))
    if update == 'y':
        if os.path.isfile("{}/.kube/config".format(user_dir)):
            shutil.copy("{}/.kube/config".format(user_dir), "{}/.kube/config.bak".format(user_dir))
        kubectl("config", "set-cluster", "{}-cluster".format(cluster_name), "--server={}".format(
            master_string), "--certificate-authority={}/ssl/ca.pem".format(buttdir))
        kubectl("config", "set-credentials", "{}-admin".format(cluster_name), "--certificate-authority={}/ssl/ca.pem".format(buttdir),
                "--client-key={}/ssl/admin-key.pem".format(buttdir), "--client-certificate={}/ssl/admin.pem".format(buttdir))
        kubectl("config", "set-context", "{}-system".format(cluster_name),
                "--cluster={}-cluster".format(cluster_name), "--user={}-admin".format(cluster_name))
        kubectl("config", "use-context", "{}-system".format(cluster_name))
