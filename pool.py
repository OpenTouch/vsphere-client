from pysphere import VIServer, VITask, VIProperty, MORTypes, VIMor, VIException
from pysphere.resources import VimService_services as VI
from pysphere.vi_virtual_machine import VIVirtualMachine
from pysphere.vi_property import getmembers
from tabulate import tabulate

def pool_list(s, opt):
    rps = s.get_resource_pools()
    tabs = []
    headers = [ "MOR", "Name" ]
    for mor, path in rps.iteritems():
        vals = [ mor, path ]
        tabs.append(vals)
    print tabulate(tabs, headers)

def pool_parser(server, opt):
    if opt['list'] == True: pool_list(server, opt)
