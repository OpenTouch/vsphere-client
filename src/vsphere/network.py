from pyVmomi import vim
from tabulate import tabulate
from misc import esx_name

ESX_NET_NETWORK = "NETWORK"
ESX_NET_DVPG = "DV PORTGROUP"

EsxNetMap = {
    vim.Network: ESX_NET_NETWORK,
    vim.dvs.DistributedVirtualPortgroup: ESX_NET_DVPG
    }

###########
# HELPERS #
###########

def net_print_details(networks):
    headers = [ "Key", "Name", "Type", "Status", "IP Pool", "Key", "Ports", "Description" ]
    tabs = []

    for n in networks:
        key = ""
        desc = ""
        ports = 0
        if n.type == ESX_NET_DVPG:
            key = n.pg.key
            desc = n.pg.description
            ports = n.pg.ports

        vals = [ n.name, n.type, n.status, n.ip_pool, key, ports, desc ]
        tabs.append(vals)

    print tabulate(tabs, headers)

###########
# CLASSES #
###########

class EsxDVPortGroup:
    def __init__(self, cfg):
        self.name = cfg.name
        self.key = cfg.key
        self.description = cfg.description
        self.ports = cfg.numPorts

    def __str__(self):
        return self.name

class EsxNetwork:
    def __init__(self, service, net):
        self.net = net
        self.service = service
        self.key = esx_name(net)
        self.name = net.summary.name
        self.type = EsxNetMap[type(net)]
        self.status = net.overallStatus
        self.ip_pool = net.summary.ipPoolName

        self.pg = None
        if self.type == ESX_NET_DVPG:
            self.pg = EsxDVPortGroup(net.config)

    def __str__(self):
        return self.name
