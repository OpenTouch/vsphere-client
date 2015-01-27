from pyVmomi import vim
from tabulate import tabulate
from network import EsxNetwork, net_print_details
from datastore import EsxDataStore, ds_print_details
from host import EsxHost, host_print_details
from pool import EsxResourcePool, pool_print_details
from misc import esx_object_find, esx_objects, esx_name, esx_object_get_items, sizeof_fmt

###########
# HELPERS #
###########

def cluster_get(service, name):
    x = esx_object_find(service, vim.ClusterComputeResource, name)
    if x: return EsxCluster(service, x)
    return None

def cluster_get_all(service):
    l = []
    cls = esx_objects(service, vim.ClusterComputeResource)
    for cl in cls:
        c = EsxCluster(service, cl)
        l.append(c)
    return l

def cluster_net(s, opt):
    cluster = cluster_get(s, opt['<name>'])
    if not cluster:
        return

    networks = cluster.net()
    net_print_details(networks)

def cluster_ds(s, opt):
    cluster = cluster_get(s, opt['<name>'])
    if not cluster:
        return

    datastores = cluster.ds()
    ds_print_details(datastores)

def cluster_host(s, opt):
    cluster = cluster_get(s, opt['<name>'])
    if not cluster:
        return

    hosts = cluster.host()
    host_print_details(hosts)

def cluster_pool(s, opt):
    cluster = cluster_get(s, opt['<name>'])
    if not cluster:
        return

    pools = cluster.pool()
    pool_print_details(pools)

def cluster_print_details(clusters):
    headers = [ "Key", "Name", "Status", "Hosts", "Cores", "Threads", "Memory" ]
    tabs = []
    for cl in clusters:
        info = cl.info()
        vals = [ cl.key, cl.name, cl.status,
                 info.hosts, info.cores, info.threads, sizeof_fmt(info.mem) ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def cluster_list(s, opt):
    clusters = cluster_get_all(s)
    cluster_print_details(clusters)

def cluster_parser(service, opt):
    if   opt['list']  == True: cluster_list(service, opt)
    elif opt['net']   == True: cluster_net(service, opt)
    elif opt['ds']    == True: cluster_ds(service, opt)
    elif opt['hosts'] == True: cluster_host(service, opt)
    elif opt['pools'] == True: cluster_pool(service, opt)

###########
# CLASSES #
###########

class EsxClusterInfo:
    def __init__(self, c):
        summary = c.summary
        self.name = esx_name(c)
        self.cores = summary.numCpuCores
        self.threads = summary.numCpuThreads
        self.mem = summary.totalMemory
        self.hosts = summary.numHosts

class EsxCluster:
    def __init__(self, service, cluster):
        self.service = service
        self.cluster = cluster
        self.key = esx_name(cluster)
        self.name = cluster.name
        self.status = cluster.overallStatus

    def info(self):
        return EsxClusterInfo(self.cluster)

    def pool(self):
        return esx_object_get_items(self.service, self.cluster.resourcePool, EsxResourcePool)

    def net(self):
        return esx_object_get_items(self.service, self.cluster.network, EsxNetwork)

    def ds(self):
        return esx_object_get_items(self.service, self.cluster.datastore, EsxDataStore)

    def host(self):
        return esx_object_get_items(self.service, self.cluster.host, EsxHost)

    def __str__(self):
        return self.name
