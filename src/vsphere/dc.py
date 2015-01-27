from pyVmomi import vim
from tabulate import tabulate
from network import EsxNetwork, net_print_details
from datastore import EsxDataStore, ds_print_details
from misc import esx_objects, esx_name, esx_object_find, esx_object_get_items

###########
# HELPERS #
###########

def dc_get(service, name):
    x = esx_object_find(service, vim.Datacenter, name)
    if x: return EsxDataCenter(service, x)
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

def dc_print_details(dcs):
    headers = [ "Key", "Name", "Status" ]
    tabs = []
    for dc in dcs:
        vals = [ dc.key, dc.name, dc.status ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def dc_list(s, opt):
    dcs = dc_get_all(s)
    dc_print_details(dcs)

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
        return esx_object_get_items(self.service, self.dc.network, EsxNetwork)

    def ds(self):
        return esx_object_get_items(self.service, self.dc.datastore, EsxDataStore)

    def __str__(self):
        return self.name
