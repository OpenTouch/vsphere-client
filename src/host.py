from pyVmomi import vim
from tabulate import tabulate
from misc import humanize_time, sizeof_fmt, esx_objects, esx_name, esx_object_find
from datastore import EsxDataStore, ds_print_details
from network import EsxNetwork, net_print_details
from perfs import EsxPerfCounter

###########
# HELPERS #
###########

def host_get(service, name):
    x = esx_object_find(service, vim.HostSystem, name)
    if x: return EsxHost(service, x)
    return None

def host_get_all(service):
    l = []
    hosts = esx_objects(service, vim.HostSystem)
    for hs in hosts:
        h = EsxHost(service, hs)
        l.append(h)
    return l

def host_net(s, opt):
    host = host_get(s, opt['<name>'])
    if not host:
        return

    networks = host.net()
    net_print_details(networks)

def host_ds(s, opt):
    host = host_get(s, opt['<name>'])
    if not host:
        return

    datastores = host.ds()
    ds_print_details(datastores)

def host_hw(s, opt):
    host = host_get(s, opt['<name>'])
    if not host:
        return

    hw = host.hw()
    print "Model: {0} {1}".format(hw.vendor, hw.model)
    print " - CPUs: {0}".format(hw.cpu)
    for p in hw.desc:
        print "  + {0}".format(p)
    print " - Cores: {0}".format(hw.cores)
    print " - Threads: {0}".format(hw.threads)
    print " - Memory: {0}".format(sizeof_fmt(hw.mem))
    print " - Devices:"
    for d in hw.devices:
        print "  + {0} {1}".format(d[0], d[1])

def host_print_details(hosts):
    headers = [ "Key", "Name", "Version", "IP", "Status", "Mem", "Mem Usage", "Mem Fairness",
                "CPUs", "Cores", "Threads", "CPU Usage", "CPU Fairness",
                "NICs", "VMs", "Uptime" ]
    tabs = []
    for host in hosts:
        info = host.info()

        mem = sizeof_fmt(info.mem_size)
        mem_usage = "{0} %".format(round(info.mem_usage * 100 / float(info.mem_size / 1024 / 1024), 2))
        cpu_usage = "{0} %".format(round(info.mean_core_usage_mhz * 100 / float(info.cpu_mhz), 2))

        vals = [ host.key, info.name, info.version, info.ip, info.status, mem, mem_usage, info.mem_fairness,
                 info.cpu, info.cores, info.threads, cpu_usage, info.cpu_fairness,
                 info.nics, info.vms, humanize_time(info.uptime) ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def host_list(s, opt):
    hosts = host_get_all(s)
    host_print_details(hosts)

def host_perf(s, opt):
    host = host_get(s, opt['<name>'])
    if not host:
        return

    headers = [ "CPU Usage", "Memory Usage", "Disk Input", "Disk Output", "Net Input", "Net Output" ]
    tabs = []

    pc = EsxPerfCounter(s)
    interval = 30

    values, samples, total, mean = pc.get('cpu.utilization.average', "", host.host, interval)
    cpu = "{0} %".format(round(mean, 2))

    values, samples, total, mean = pc.get('mem.usage.average', "", host.host, interval)
    mem = "{0} %".format(round(mean / 100, 2))

    values, samples, total, mean = pc.get('disk.write.average', "", host.host, interval)
    din = "{0} kB/s".format(round(mean, 2))
    values, samples, total, mean = pc.get('disk.read.average', "", host.host, interval)
    dout = "{0} kB/s".format(round(mean, 2))

    values, samples, total, mean = pc.get('net.received.average', "", host.host, interval)
    netin = "{0} kB/s".format(round(mean, 2))
    values, samples, total, mean = pc.get('net.transmitted.average', "", host.host, interval)
    netout = "{0} kB/s".format(round(mean, 2))

    vals = [ cpu, mem, din, dout, netin, netout ]
    tabs.append(vals)

    print tabulate(tabs, headers)

def host_parser(service, opt):
    if   opt['list']  == True: host_list(service, opt)
    elif opt['hw']    == True: host_hw(service, opt)
    elif opt['net']   == True: host_net(service, opt)
    elif opt['ds']    == True: host_ds(service, opt)
    elif opt['perf']  == True: host_perf(service, opt)

###########
# CLASSES #
###########

class EsxHostHardware:
    def __init__(self, hw):
        self.vendor = hw.systemInfo.vendor
        self.model = hw.systemInfo.model
        self.cpu = hw.cpuInfo.numCpuPackages
        self.desc = []
        for p in hw.cpuPkg:
            self.desc.append(p.description)
        self.cores = hw.cpuInfo.numCpuCores
        self.threads = hw.cpuInfo.numCpuThreads
        self.mem = hw.memorySize
        self.devices = []
        for d in hw.pciDevice:
            self.devices.append([d.vendorName, d.deviceName])

class EsxHostInfo:
    def __init__(self, h):
        self.name = esx_name(h)
        self.version = h.summary.config.product.version
        self.ip = h.name
        self.status = h.overallStatus

        self.mem_size = h.summary.hardware.memorySize
        self.mem_usage = h.summary.quickStats.overallMemoryUsage
        self.mem_fairness = round(float(h.summary.quickStats.distributedMemoryFairness) / 1000, 3)

        self.cpu = h.summary.hardware.numCpuPkgs
        self.cores =  h.summary.hardware.numCpuCores
        self.threads = h.summary.hardware.numCpuThreads
        self.cpu_mhz = h.summary.hardware.cpuMhz
        self.mean_core_usage_mhz = h.summary.quickStats.overallCpuUsage
        self.cpu_fairness = round(float(h.summary.quickStats.distributedCpuFairness) / 1000, 3)

        self.nics = h.summary.hardware.numNics
        self.vms = len(h.vm)
        self.uptime = h.summary.quickStats.uptime

class EsxHost:
    def __init__(self, service, host):
        self.service = service
        self.host = host
        self.key = esx_name(host)
        self.name = self.host.name

    def info(self):
        return EsxHostInfo(self.host)

    def hw(self):
        return EsxHostHardware(self.host.hardware)

    def net(self):
        l = []
        networks = self.host.network
        for net in networks:
            n = EsxNetwork(self.service, net)
            l.append(n)
        return l

    def ds(self):
        l = []
        for s in self.host.datastore:
            ds = EsxDataStore(self.service, s)
            l.append(ds)
        return l

    def __str__(self):
        return self.name
