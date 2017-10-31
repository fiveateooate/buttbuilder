"""libvirt storage functions"""

import libvirt


xmlDesc_tmptl = """
<pool type='dir'>
  <name>{name}</name>
  <source>
  </source>
  <target>
    <path>{path}</path>
    <permissions>
      <mode>0775</mode>
    </permissions>
  </target>
</pool>"""


def get(client, name):
    pool = None
    try:
        pool = client.connection.storagePoolLookupByName(name)
    except libvirt.libvirtError as exc:
        pool = []
    return pool


def list(client):
    pools = []
    try:
        pools = client.connection.listAllStoragePools()
    except libvirt.libvirtError as exc:
        pools = None
    return pools


def create(client, storage_config):
    pool = get(client, storage_config['name'])
    if not pool:
        try:
            poolXML = xmlDesc_tmptl.format(**storage_config)
            pool = client.connection.storagePoolDefineXML(poolXML, 0)
            pool.create()
            if 'autostart' in storage_config and storage_config['autostart']:
                pool.setAutostart(1)
        except libvirt.libvirtError as exc:
            pool = None
    return pool


def delete(client, name):
    pool = {"name": name}
    try:
        pool = get(client, name)
        if pool:
            pool.destroy()
            pool.undefine()
            pool = get(client, name)
    except libvirt.libvirtError as exc:
        print(exc)
        pool = None
    return pool
