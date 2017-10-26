"""Goofy imports so all libraries do not have to be installed on whatever system
    - osx is horrendous garbage
    - windows is just plain shit"""

import os

import buttlib.common

if 'provider' in os.environ:
    if os.environ['provider'] == 'aws':
        from buttlib.aws import Builder
    if os.environ['provider'] == 'libvirt':
        from buttlib.libvirt import Builder
    if os.environ['provider'] == 'vbox':
        from buttlib.vbox import Builder
    if os.environ['provider'] == 'proxmox':
        from buttlib.proxmox import Builder
    if os.environ['provider'] == 'gce':
        from buttlib.gce import Builder
