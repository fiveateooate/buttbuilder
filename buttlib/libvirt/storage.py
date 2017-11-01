"""libvirt storage functions"""

import libvirt


xmldesc_tmplt = """
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
        print(exc)
    return pool


def list(client):
    try:
        pools = client.connection.listAllStoragePools()
    except libvirt.libvirtError as exc:
        print(exc)
        pools = []
    return pools


def create(client, storage_config):
    pool = []
    if not get(client, storage_config['name']):
        try:
            poolXML = xmldesc_tmplt.format(**storage_config)
            pool = client.connection.storagePoolDefineXML(poolXML, 0)
            pool.create()
            if 'autostart' in storage_config and storage_config['autostart']:
                pool.setAutostart(1)
        except libvirt.libvirtError as exc:
            print(exc)
    return pool


def delete(client, name):
    retval = False
    try:
        pool = get(client, name)
        if pool:
            pool.destroy()
            pool.undefine()
            retval = True
    except libvirt.libvirtError as exc:
        print(exc)
        retval = False
    return retval
