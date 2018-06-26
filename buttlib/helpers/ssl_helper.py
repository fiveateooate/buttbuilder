import os
import textwrap

import OpenSSL


class SSLHelper():
    def __init__(self, domain, ssl_dir, bits=4096):
        self.__domain = domain
        self.__bits = bits
        self.__ssl_dir = ssl_dir
        self.__ssl_info = {}
        self.__indent_string = "{:8}".format("")
        self.load_or_create_ca()

    def load_key_from_file(self, filename):
        with open(filename, 'rt') as file:
            __tmp = file.read()
        __key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, __tmp)
        return __key

    def load_cert_from_file(self, filename):
        with open(filename, 'rt') as file:
            __tmp = file.read()
        __cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, __tmp)
        return __cert

    def load_or_create_ca(self):
        ca_key_file = self.__ssl_dir + "/ca-key.pem"
        ca_cert_file = self.__ssl_dir + "/ca.pem"
        if os.path.isfile(ca_key_file) and os.path.isfile(ca_cert_file):
            self.__ca_key = self.load_key_from_file(ca_key_file)
            self.__ca_cert = self.load_cert_from_file(ca_cert_file)
            self.add_formatted_cert_to_ssl_dict('ca_pem', self.__ca_cert)
            self.add_formatted_key_to_ssl_dict('ca_key', self.__ca_key)
        else:
            self.__ca_key = self.generateKey()
            self.__ca_cert = OpenSSL.crypto.X509()
            self.generate_ca()

    def add_formatted_key_to_ssl_dict(self, name, key):
        self.__ssl_info[name] = textwrap.indent(
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key).decode(), self.__indent_string)

    def add_formatted_cert_to_ssl_dict(self, name, cert):
        self.__ssl_info[name] = textwrap.indent(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert).decode(),
            self.__indent_string
        )

    def getInfo(self):
        return self.__ssl_info

    def create_or_load_certs(self, master_ips, cluster_ip, additional_names=None):
        api_key_file = self.__ssl_dir + "/apiserver-key.pem"
        api_cert_file = self.__ssl_dir + "/apiserver.pem"
        admin_key_file = self.__ssl_dir + "/admin-key.pem"
        admin_cert_file = self.__ssl_dir + "/admin.pem"
        if os.path.isfile(api_key_file) and os.path.isfile(api_cert_file):
            self.__api_key = self.load_key_from_file(api_key_file)
            self.__api_cert = self.load_cert_from_file(api_cert_file)
            self.add_formatted_cert_to_ssl_dict('api_pem', self.__api_cert)
            self.add_formatted_key_to_ssl_dict('api_key', self.__api_key)
        else:
            self.generateAPIServer(master_ips, cluster_ip, additional_names)
        if os.path.isfile(admin_key_file) and os.path.isfile(admin_cert_file):
            self.__admin_key = self.load_key_from_file(admin_key_file)
            self.__admin_cert = self.load_cert_from_file(admin_cert_file)
            self.add_formatted_cert_to_ssl_dict('admin_pem', self.__admin_cert)
            self.add_formatted_key_to_ssl_dict('admin_key', self.__admin_key)
        else:
            self.generateAdmin()

    def setCertDefaults(self, cert, subject):
        cert.get_subject().CN = subject
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)

    def signCert(self, cert, key):
        cert.set_issuer(self.__ca_cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(self.__ca_key, 'sha256')

    def generateKey(self):
        key = OpenSSL.crypto.PKey()
        key.generate_key(OpenSSL.crypto.TYPE_RSA, self.__bits)
        return key

    def writeFiles(self, cert, key, name):
        if not os.path.exists(self.__ssl_dir):
            os.makedirs(self.__ssl_dir)
        with open("{}/{}.pem".format(self.__ssl_dir, name), "w") as file:
            file.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert).decode())
        with open("{}/{}-key.pem".format(self.__ssl_dir, name), "w") as file:
            file.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key).decode())

    def generateAPIServer(self, master_ips, cluster_ip, additional_names=None):
        san_list = "DNS.1:kubernetes, DNS.2:kubernetes.default, DNS.3:kubernetes.default.svc, DNS.4:kubernetes.default.svc.{}, IP.1:{}".format(self.__domain, cluster_ip)
        i = 5
        for name in additional_names:
            san_list += ",DNS.{}:{}".format(i, name)
            i += 1
        i = 2
        for ip in master_ips:
            san_list += ",IP.{}:{}".format(i, ip)
            i += 1
        api_cert = OpenSSL.crypto.X509()
        api_key = self.generateKey()
        self.setCertDefaults(api_cert, "kube-apiserver")
        api_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE')
        ])
        api_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'subjectAltName', False, san_list.encode('utf-8'))
        ])
        self.signCert(api_cert, api_key)
        self.add_formatted_cert_to_ssl_dict("api_pem", api_cert)
        self.add_formatted_key_to_ssl_dict("api_key", api_key)
        self.writeFiles(api_cert, api_key, "apiserver")

    def generateHost(self, hostname, hostip):
        san_list = "IP.1:{}".format(hostip)
        host_cert = OpenSSL.crypto.X509()
        host_key = self.generateKey()
        self.setCertDefaults(host_cert, "system:node:{}".format(hostname))
        host_cert.get_subject().O = "system:nodes"
        host_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE')
        ])
        host_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'subjectAltName', False, san_list.encode('utf-8'))
        ])
        self.signCert(host_cert, host_key)
        self.add_formatted_cert_to_ssl_dict("{}_pem".format(hostname), host_cert)
        self.add_formatted_key_to_ssl_dict("{}_key".format(hostname), host_key)
        self.writeFiles(host_cert, host_key, hostname)

    def generateHostName(self, hostname):
        san_list = "DNS.1:{}".format(hostname)
        host_cert = OpenSSL.crypto.X509()
        host_key = self.generateKey()
        self.setCertDefaults(host_cert, "system:node:{}".format(hostname))
        host_cert.get_subject().O = "system:nodes"
        host_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'basicConstraints', False,
                                         b'CA:FALSE')
        ])
        host_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'subjectAltName', False,
                                         san_list.encode('utf-8'))
        ])
        self.signCert(host_cert, host_key)
        self.add_formatted_cert_to_ssl_dict("{}_pem".format(hostname), host_cert)
        self.add_formatted_key_to_ssl_dict("{}_key".format(hostname), host_key)
        self.writeFiles(host_cert, host_key, hostname)

    def generateAdmin(self):
        admin_cert = OpenSSL.crypto.X509()
        admin_key = self.generateKey()
        self.setCertDefaults(admin_cert, "cluster-admin")
        admin_cert.get_subject().O = "system:masters"
        admin_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE')
        ])
        self.signCert(admin_cert, admin_key)
        self.add_formatted_cert_to_ssl_dict('admin_pem', admin_cert)
        self.add_formatted_key_to_ssl_dict('admin_key', admin_key)
        self.writeFiles(admin_cert, admin_key, "admin")

    def generate_ca(self):
        self.setCertDefaults(self.__ca_cert, "kube-ca")
        self.__ca_cert.add_extensions([
            OpenSSL.crypto.X509Extension(b'basicConstraints', False, b'CA:TRUE')
        ])
        self.signCert(self.__ca_cert, self.__ca_key)
        self.add_formatted_cert_to_ssl_dict('ca_pem', self.__ca_cert)
        self.add_formatted_key_to_ssl_dict('ca_key', self.__ca_key)
        self.writeFiles(self.__ca_cert, self.__ca_key, "ca")
