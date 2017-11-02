"""
storage pool volume functions

volume upload function figured out/partial copy from this -
    https://www.redhat.com/archives/libvir-list/2012-December/msg01369.html
"""

import libvirt


vol_xml_tmplt = """
<volume>
  <allocation>0</allocation>
  <capacity>{size}</capacity>
  <name>{name}</name>
  <target>
    <path>{full_path}</path>
  </target>
</volume>"""


def get(client, pool, name):
    try:
        vol = pool.storageVolLookupByName(name)
    except libvirt.libvirtError as exc:
        print(exc)
        vol = None
    return vol


def list(client, pool):
    try:
        volumes = pool.listAllVolumes()
    except libvirt.libvirtError as exc:
        print(exc)
        volumes = []
    return volumes


def create(client, pool, volume_config):
    try:
        handle_exists(client, pool, volume_config['name'])
        vol_xml = vol_xml_tmplt.format(**volume_config)
        vol = pool.createXML(vol_xml, 0)
    except libvirt.libvirtError as exc:
        print(exc)
        vol = None
    return vol


def delete(client, pool, name):
    retval = False
    try:
        vol = get(client, pool, name)
        if vol:
            vol.delete(0)
        retval = True
    except libvirt.libvirtError as exc:
        print(exc)
    return retval


def handler(stream, data, file_):
    return file_.read(data)


def import_image(client, pool, image, volume_config):
    try:
        handle_exists(client, pool, volume_config['name'])
        vol_xml = vol_xml_tmplt.format(**volume_config)
        vol = pool.createXML(vol_xml, 0)
        with open(image, 'rb') as file:
            st = client.connection.newStream(0)
            vol.upload(st, 0, volume_config['size'], libvirt.VIR_STORAGE_VOL_UPLOAD_SPARSE_STREAM)
            st.sendAll(handler, file)
            st.finish()
    except libvirt.libvirtError as exc:
        print(exc)
        vol = None
    return vol


def resize_image(client, pool, volume_config):
    try:
        vol = get(client, pool, volume_config['name'])
        vol.resize(volume_config['size'])
        retval = True
    except libvirt.libvirtError as exc:
        print(exc)
        retval = False
    return retval


def handle_exists(client, pool, name):
    overwrite = 'n'
    for volume in list(client, pool):
        if volume.name() == name:
            overwrite = input("{} exists, overwrite? (y|n) ".format(name))
            break
    if overwrite == 'y':
        delete(client, pool, name)
