from pyVmomi import vim
from tabulate import tabulate
from vm import EsxVirtualMachine, vm_print_details
from misc import esx_objects_retrieve, esx_name, esx_object_get_items

###########
# HELPERS #
###########

def pool_get(service, name=None):
    return esx_objects_retrieve(service, vim.ResourcePool, EsxResourcePool, name)

def pool_vm(s, opt):
    pool = pool_get(s, opt['<name>'])
    if not pool:
        return

    vms = pool.vm()
    vm_print_details(vms)

def pool_print_details(pools):
    headers = [ "Key", "Name", "Status" ]
    tabs = []
    for pl in pools:
       vals = [ pl.key, pl.name, pl.status ]
       tabs.append(vals)

    print tabulate(tabs, headers)

def pool_list(s, opt):
    pools = pool_get(s)
    pool_print_details(pools)

def pool_parser(service, opt):
    if   opt['list']  == True: pool_list(service, opt)
    elif opt['vms']   == True: pool_vm(service, opt)

###########
# CLASSES #
###########

class EsxResourcePool:
    def __init__(self, service, pool):
        self.service = service
        self.pool = pool
        self.key = esx_name(pool)
        self.name = pool.name
        self.status = pool.overallStatus

    def vm(self):
        return esx_object_get_items(self.service, self.pool.vm, EsxVirtualMachine)

    def __str__(self):
        return self.name
