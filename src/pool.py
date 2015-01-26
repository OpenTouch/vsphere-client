from pyVmomi import vim
from tabulate import tabulate
from vm import EsxVirtualMachine, vm_print_details
from misc import esx_objects, esx_name

###########
# HELPERS #
###########

def pool_get(service, name):
    pool = esx_objects(service, vim.ResourcePool)
    for pl in pool:
        # try to lookup by key first
        ckey = esx_name(pl)
        if ckey == name:
            return EsxResourcePool(service, pl)

        # fallback to name lookup
        cname = pl.name
        if cname == name:
            return EsxResourcePool(service, pl)

    return None

def pool_get_all(service):
    l = []
    pool = esx_objects(service, vim.ResourcePool)
    for pl in pool:
        p = EsxResourcePool(service, pl)
        l.append(p)
    return l

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
    pools = pool_get_all(s)
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
        l = []
        vms = self.pool.vm
        for vm in vms:
            v = EsxVirtualMachine(self.service, vm)
            l.append(v)
        return l

    def __str__(self):
        return self.name
