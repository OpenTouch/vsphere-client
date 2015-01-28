import sys
from os import path
from ConfigParser import ConfigParser

VSPHERE_CFG_FILE = "vsphere.conf"

unix_platforms = [
    "darwin",
    "Linux"
]

class EsxConfig:
    def __init__(self):
        ok = False

        # specific configuration
        local_cfg = VSPHERE_CFG_FILE

        # user-global configuration
        user_cfg = ""
        if sys.platform in unix_platforms:
            user_cfg = path.join(path.expanduser("~"), '.{0}'.format(VSPHERE_CFG_FILE))

        # system-wide configuration
        system_cfg = ""
        if sys.platform in unix_platforms:
            system_cfg = path.join(path.expanduser("/etc/vsphere"), VSPHERE_CFG_FILE)

        files = [ local_cfg, user_cfg, system_cfg ]

        for f in files:
            if path.exists(f):
                parser = ConfigParser()
                parser.read(f)
                ok = True
                break

        if ok:
            self.vs_host = parser.get('server', 'host')
            self.vs_user = parser.get('server', 'user')
            self.vs_password = parser.get('server', 'password')
