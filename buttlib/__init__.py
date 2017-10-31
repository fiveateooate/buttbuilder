"""Goofy imports so all libraries do not have to be installed on whatever system
    - osx is horrendous garbage
    - windows is just plain shit"""

import sys
import buttlib.common
import buttlib.helpers
import buttlib.exceptions

# if 'provider' in os.environ:
#     if os.environ['provider'] == 'aws':
#         from buttlib.aws import Builder
#     if os.environ['provider'] == 'libvirt':
#         from buttlib.libvirt import Builder
#     if os.environ['provider'] == 'vbox':
#         from buttlib.vbox import Builder
#     if os.environ['provider'] == 'proxmox':
#         from buttlib.proxmox import Builder
#     if os.environ['provider'] == 'gce':
#         from buttlib.gce import Builder


from buttlib.aws import Builder
from buttlib.vbox import Builder
# proxmox WIP - converting to not shit api library
# from buttlib.proxmox import Builder
from buttlib.gce import Builder
# only import libvirt on linux systems
if sys.platform == 'linux':
    from buttlib.libvirt import Builder
