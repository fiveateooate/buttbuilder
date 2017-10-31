"""libvirt network functions"""

import libvirt


xmlDesc_tmplt = """<network>
  <name>{name}</name>
  <forward mode='nat'/>
  <bridge name='%sbr0' stp='on' delay='0'/>
  <mac address='{mac}'/>
  <ip address='{gateway_ip}' netmask='{netmask}'>
    <dhcp>
      <range start='{ip_range_start}' end='{ip_range_end}/>
      %s</dhcp>
  </ip>
</network>"""


def get(client, name):
    network = None
    try:
        network = client.connection.networkLookupByName(name)
    except libvirt.libvirtError as exc:
        network = []
    return network


def list(client):
    networks = []
    try:
        networks = client.connection.listNetworks()
    except libvirt.libvirtError as exc:
        pools = None
    return networks


def create(client, network_config):
    pass


def delete(client, network_name):
    pass
