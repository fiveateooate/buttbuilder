# libvrit specific


## libvirt client functions

~~~shell
client.allocPages()                     client.getInfo()                        client.listNetworks()                   client.nwfilterDefineXML()
client.baselineCPU()                    client.getLibVersion()                  client.listSecrets()                    client.nwfilterLookupByName()
client.c_pointer()                      client.getMaxVcpus()                    client.listStoragePools()               client.nwfilterLookupByUUID()
client.changeBegin()                    client.getMemoryParameters()            client.lookupByID()                     client.nwfilterLookupByUUIDString()
client.changeCommit()                   client.getMemoryStats()                 client.lookupByName()                   client.registerCloseCallback()
client.changeRollback()                 client.getSecurityModel()               client.lookupByUUID()                   client.restore()
client.close()                          client.getSysinfo()                     client.lookupByUUIDString()             client.restoreFlags()
client.compareCPU()                     client.getType()                        client.networkCreateXML()               client.saveImageDefineXML()
client.createLinux()                    client.getURI()                         client.networkDefineXML()               client.saveImageGetXMLDesc()
client.createXML()                      client.getVersion()                     client.networkEventDeregisterAny()      client.secretDefineXML()
client.createXMLWithFiles()             client.interfaceDefineXML()             client.networkEventRegisterAny()        client.secretEventDeregisterAny()
client.defineXML()                      client.interfaceLookupByMACString()     client.networkLookupByName()            client.secretEventRegisterAny()
client.defineXMLFlags()                 client.interfaceLookupByName()          client.networkLookupByUUID()            client.secretLookupByUUID()
client.domainEventDeregister()          client.isAlive()                        client.networkLookupByUUIDString()      client.secretLookupByUUIDString()
client.domainEventDeregisterAny()       client.isEncrypted()                    client.newStream()                      client.secretLookupByUsage()
client.domainEventRegister()            client.isSecure()                       client.nodeDeviceCreateXML()            client.setKeepAlive()
client.domainEventRegisterAny()         client.listAllDevices()                 client.nodeDeviceEventDeregisterAny()   client.setMemoryParameters()
client.domainListGetStats()             client.listAllDomains()                 client.nodeDeviceEventRegisterAny()     client.storagePoolCreateXML()
client.domainXMLFromNative()            client.listAllInterfaces()              client.nodeDeviceLookupByName()         client.storagePoolDefineXML()
client.domainXMLToNative()              client.listAllNWFilters()               client.nodeDeviceLookupSCSIHostByWWN()  client.storagePoolEventDeregisterAny()
client.findStoragePoolSources()         client.listAllNetworks()                client.numOfDefinedDomains()            client.storagePoolEventRegisterAny()
client.getAllDomainStats()              client.listAllSecrets()                 client.numOfDefinedInterfaces()         client.storagePoolLookupByName()
client.getCPUMap()                      client.listAllStoragePools()            client.numOfDefinedNetworks()           client.storagePoolLookupByUUID()
client.getCPUModelNames()               client.listDefinedDomains()             client.numOfDefinedStoragePools()       client.storagePoolLookupByUUIDString()
client.getCPUStats()                    client.listDefinedInterfaces()          client.numOfDevices()                   client.storageVolLookupByKey()
client.getCapabilities()                client.listDefinedNetworks()            client.numOfDomains()                   client.storageVolLookupByPath()
client.getCellsFreeMemory()             client.listDefinedStoragePools()        client.numOfInterfaces()                client.suspendForDuration()
client.getDomainCapabilities()          client.listDevices()                    client.numOfNWFilters()                 client.unregisterCloseCallback()
client.getFreeMemory()                  client.listDomainsID()                  client.numOfNetworks()                  client.virConnGetLastError()
client.getFreePages()                   client.listInterfaces()                 client.numOfSecrets()                   client.virConnResetLastError()
client.getHostname()                    client.listNWFilters()                  client.numOfStoragePools()   
~~~
