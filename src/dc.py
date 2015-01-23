from pyVmomi import vim
from tabulate import tabulate
from network import EsxNetwork, net_print_details
from datastore import EsxDataStore, ds_print_details
from misc import esx_objects, esx_name

###########
# HELPERS #
###########

def dc_get(service, name):
    centers = esx_objects(service, vim.Datacenter)
    for dc in centers:
        # try to lookup by key first
        dc_key = esx_name(dc)
        if dc_key == name:
            return EsxDataCenter(service, dc)

        # fallback to name lookup
        dc_name = dc.name
        if dc_name == name:
            return EsxDataCenter(service, dc)

    return None

def dc_get_all(service):
    l = []
    hosts = esx_objects(service, vim.Datacenter)
    for hs in hosts:
        h = EsxDataCenter(service, hs)
        l.append(h)
    return l

def dc_net(s, opt):
    dc = dc_get(s, opt['<name>'])
    if not dc:
        return

    networks = dc.net()
    net_print_details(networks)

def dc_ds(s, opt):
    dc = dc_get(s, opt['<name>'])
    if not dc:
        return

    datastores = dc.ds()
    ds_print_details(datastores)

def dc_list(s, opt):
    pool = EsxDataCenterPool(s)
    headers = [ "Key", "Name", "Status" ]
    tabs = []
    for dc in pool.dc:
        vals = [ dc.key, dc.name, dc.status ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def dc_parser(service, opt):
    if   opt['list']  == True: dc_list(service, opt)
    elif opt['net']   == True: dc_net(service, opt)
    elif opt['ds']    == True: dc_ds(service, opt)

###########
# CLASSES #
###########

class EsxDataCenter:
    def __init__(self, service, dc):
        self.service = service
        self.dc = dc
        self.key = esx_name(dc)
        self.name = dc.name
        self.status = dc.overallStatus

    def net(self):
        l = []
        networks = self.dc.network
        for net in networks:
            n = EsxNetwork(net)
            l.append(n)
        return l

    def ds(self):
        l = []
        for s in self.dc.datastore:
            ds = EsxDataStore(self.service, s)
            l.append(ds)
        return l

    def __str__(self):
        return self.name

class EsxDataCenterPool:
    def __init__(self, service):
        self.dc = dc_get_all(service)

    def list(self):
        return self.dc

    def get(self, name):
        for d in self.dc:
            if d.name == name:
                return d
        return None

    def __str__(self):
        r  = "ESXi Datacenters:\n"
        for d in self.dc:
            r += str(d)
        r += "\n"
        return r
