from ConfigParser import ConfigParser

class EsxConfig:
    def __init__(self):
        parser = ConfigParser()
        parser.read("vsphere.conf")

        self.vs_host = parser.get('server', 'host')
        self.vs_user = parser.get('server', 'user')
        self.vs_password = parser.get('server', 'password')
        self.vs_dc = parser.get('server', 'dc')
