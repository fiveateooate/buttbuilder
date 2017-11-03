"""libvirt instance/vm functions"""

import libvirt


# Guess I am just going with the stupid template xml shit and replacement dict
# the xmlns crap is for sure needed for the qemu command line stuff to work
# maybe some stuff could be dropped, but tried to delete what I knew I could
dom_xml_tmplt = """<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
  <name>{hostname}</name>
  <memory unit='MiB'>{ram}</memory>
  <vcpu placement='static'>{cpus}</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='hd'/>
  </os>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <features>
    <acpi/>
    <apic/>
  </features>
  <pm>
    <suspend-to-mem enabled='no'/>
    <suspend-to-disk enabled='no'/>
  </pm>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{buttdir}/{hostname}.{image_type}'/>
      <target dev='hda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <mac address='{mac}'/>
      <source network='{network_name}'/>
      <model type='virtio'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <channel type='spicevmc'>
      <target type='virtio' name='com.redhat.spice.0'/>
    </channel>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='spice' autoport='yes'>
      <listen type='address'/>
      <image compression='off'/>
    </graphics>
  </devices>
   <qemu:commandline>
     <qemu:arg value='-fw_cfg'/>
     <qemu:arg value='name=opt/com.coreos/config,file={buttdir}/{hostname}.ign'/>
   </qemu:commandline>
</domain>
"""


def get(client, name):
    pass


def list(client):
    pass


def create(client, instance_config):
    try:
        dom_xml = dom_xml_tmplt.format(**instance_config)
        domain = client.connection.defineXML(dom_xml)
        domain.start()
    except libvirt.libvirtError as exc:
        print(exc)
        dom = None
    return domain


def delete(client, name):
    pass
