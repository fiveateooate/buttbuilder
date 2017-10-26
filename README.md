# Build a kubernetes cluster - you know you want to

Uses yaml configuration file to create and configure a kubernetes cluster. Available providers are libvirt, virtualbox, aws, and gce. Uses cloud-init/user-data to configure cluster on boot.


* switching to ignition is  work in progreess, see the ignitionswitch branch
* readme somewhat out of default-cluster

## Setup
### osx Dependencies
```sh
$ brew install python3 cdrtools
$ pip3 install pyyaml ipaddress requests
$ easy_install-3.6 PyOpenSSL PyCrypto
```
### Linux Dependencies
So awesome and easy no additional comment is needed
### m$ garbage whatever
you should be ashamed
### kubectl
Most likely you want kubectl

using curl - [Official Docs](https://kubernetes.io/docs/user-guide/prereqs/)

osx using brew - `brew install kubctl`

Arch Linux from AUR - `packer -S google-cloud-sdk`

## Cluster Configuration

Example:

```yaml
clusterenv:clusterid:
  clusterDomain: cluster.local
  kubeletVersion: v1.8.2_coreos.0
  externalNet: "192.168.69.0/24"
  clusterNet: "192.168.70.0/24"
  coreosChannel: alpha
  libvirtHost: "qemu:///system"
  masters:
    nodes: 1
    ram: 1024
    cpus: 1
    disk: 9
  workers:
    nodes: 2
    ram: 3192
    cpus: 2
    disk: 26
provider: libvirt
...
```
Notes:
*   top level key should be cluster_env:cluster_id
*   clusterDomain: Kube DNS is configured to use this domain
*   kubeletVersion: ~ kubernetes version
*   externalNet: nodes are assigned static ips from this range
  *   masters x.x.x.10-29
  *   workers x.x.x.30-253
*   clusterNet: kubernetes service network
* kube dns service set to x.x.x.5
*   masters: configuration parameters for master nodes
*   workers: configuration parameters for worker nodes
*   provider: libvirt, vbox, aws, or gce


## Usage:

```bash
./buttbuilder.py --cluster_env cluster_environment --cluster_id clusterid --cluster_config_path path/to/yaml build
```

### addons
Services automatically installed and managed by kube-addon-manager
*   kubernetes dashboard
*   kube-dns with horizontal autoscaler

### notes

* nodes will be assigned hostnames in the format cluster_env-cluster_id-(master|worker)0[1..x]
* A configmap is added to the `kube-system` namespace containing the cluster_env and cluster_id
* etcd
  * static discovery with every master as member
  * workers configured as etcd proxies
* ssl certs are created and set up on cluster creation
* image files and ssl certs are written to `~/cluster_env-cluster_id/`
* on [Arch Linux](https://www.archlinux.org/) clusterbuilder just works

[Video Tutorial](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

## kubectl configuration

copied from [here](https://coreos.com/kubernetes/docs/latest/configure-kubectl.html), adjust to match cluster and path to certs


```bash
kubectl config set-cluster my-cluster --server=https://${MASTER_HOST} --certificate-authority=${CA_CERT}
kubectl config set-credentials my-admin --certificate-authority=${CA_CERT} --client-key=${ADMIN_KEY} --client-certificate=${ADMIN_CERT}
kubectl config set-context my-system --cluster=default-cluster --user=my-admin
kubectl config use-context my-system
```

or edit `.kube/config`

```yaml
- cluster:
    certificate-authority: /cluster-dir/ssl/ca.pem
    server: https://192.168.69.10
  name: my-cluster
contexts:
- context:
    cluster: my-cluster
    user: my-admin
  name: my-system
current-context: my-system
kind: Config
preferences: {}
users:
- name: my-admin
  user:
    client-certificate: /cluster-dir/ssl/admin.pem
    client-key: /cluster-dir/ssl/admin-key.pem
```


## VirtualBox Notes
*   networking is odd so everything is listening on 127.0.0.1
*   ssh ports start at 10022 and increment by 1 for each node - `ssh core@127.0.0.1 -p 10022`
*   kubernetes api is listening on 127.0.0.1:10443
