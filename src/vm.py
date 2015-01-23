from pyVmomi import vim
from tasks import WaitForTasks
from tabulate import tabulate
from misc import sizeof_fmt, humanize_time, esx_get_obj

###########
# HELPERS #
###########

def vm_get_children(x, node):
    children = node.childEntity
    for c in children:
        if type(c) == vim.Folder:
            vm_get_children(x, c)
        elif type(c) == vim.VirtualMachine:
            x.append(c)

def vm_guess_folder(vm):
    if vm.parent.name != "vm":
        return vm_guess_folder(vm.parent) + vm.parent.name
    else:
        return "/"

def vm_list(s, opt):
    pool = VirtualMachinePool(s)
    vms = pool.list()

    tabs = []
    headers = [ "Name", "Status", "Pool", "Host", "Folder", "HA", "OS", "IP", "CPUs", "Mem (MB)", "NIC", "HDD (GB)", "Uptime" ]

    for vm in vms:
        # retrieve infos
        hd_size = "{0} / {1}".format(vm.hd_committed, vm.hd_uncommitted)
        vals = [ vm.name, vm.status, vm.pool, vm.host, vm.folder, vm.ha,
                 vm.os, vm.ip, vm.cpu, vm.mem, vm.nic, hd_size, vm.uptime ]
        tabs.append(vals)
        tabs.sort(reverse=False)

    hd_total = "{0} / {1}".format(pool.hd_committed, pool.hd_uncommitted)
    vals = [ "TOTAL", "", "", "", "", "", "", "", pool.cpu, pool.mem, "", hd_total, "" ]
    tabs.append(vals)

    print tabulate(tabs, headers)

def vm_details(s, opt):
    vm = VirtualMachine(s, name=opt['<name>'])
    vm.print_details()

def vm_create(s, opt):
    vm_name = opt['<name>']
    template = opt['<template>']
    net_name = opt['--network']
    memory = int(opt['--mem'])
    if memory is None:
        memory = 1024 # MB
    cpus = int(opt['--cpu'])
    if cpus is None:
        cpus = 1
    folder = opt['--folder']

    print 'Trying to clone %s to VM %s' % (template, vm_name)
    if esx_get_obj(s.RetrieveContent(), vm_name, vim.VirtualMachine) != None:
        print 'ERROR: %s already exists' % vm_name
    else:
        VirtualMachineCreation(s, vm_name, "Cluster1", template, memory, cpus, net_name, folder)

def vm_delete(s, opt):
    vm = VirtualMachine(s, name=opt['name'])
    vm.stop()
    vm.destroy()

def vm_start(s, opt):
    vm = VirtualMachine(s, name=opt['name'])
    vm.start()

def vm_stop(s, opt):
    vm = VirtualMachine(s, name=opt['name'])
    vm.stop()

def vm_reset(s, opt):
    vm = VirtualMachine(s, name=opt['name'])
    vm.reset()

def vm_reboot(s, opt):
    vm = VirtualMachine(s, name=opt['name'])
    vm.reboot()

def vm_suspend(s, opt):
    vm = VirtualMachine(s, name=opt['name'])
    vm.suspend()

def vm_parser(service, opt):
    if   opt['list']    == True: vm_list(service, opt)
    elif opt['details'] == True: vm_details(service, opt)
    elif opt['create']  == True: vm_create(service, opt)
    elif opt['delete']  == True: vm_delete(service, opt)
    elif opt['start']   == True: vm_start(service, opt)
    elif opt['stop']    == True: vm_stop(service, opt)
    elif opt['reset']   == True: vm_reset(service, opt)
    elif opt['reboot']  == True: vm_reboot(service, opt)
    elif opt['suspend'] == True: vm_suspend(service, opt)

###########
# CLASSES #
###########

class VirtualMachineInfo:
    def __init__(self, vm):
        summary = vm.summary
        config = summary.config
        runtime = summary.runtime
        guest = summary.guest
        storage = summary.storage
        stats = summary.quickStats

        self.vm = vm
        self.name = config.name
        self.status = runtime.powerState
        self.pool = config.vmPathName.split(' ')[0].strip('[').strip(']')
        self.host = str(runtime.host).split(':')[1].strip("'")
        self.folder = vm_guess_folder(vm)
        _ha = runtime.faultToleranceState
        if _ha == "notConfigured":
            self.ha = False
        else:
            self.ha = True
        self.os = config.guestFullName
        self.hostname = guest.hostName
        self.ip = guest.ipAddress
        self.cpu = config.numCpu
        self.mem = config.memorySizeMB
        self.nic = config.numEthernetCards
        self.hd_committed = storage.committed / 1024 / 1024 / 1024
        self.hd_uncommitted = storage.uncommitted / 1024 / 1024 / 1024
        self.uptime = humanize_time(stats.uptimeSeconds)
    def __str__(self):
        str  = "Name: {0}\n".format(self.name)
        str += "Status: {0}\n".format(self.status)
        str += "Pool: {0}\n".format(self.pool)
        str += "Host: {0}\n".format(self.host)
        str += "Folder: {0}\n".format(self.folder)
        str += "HA: {0}\n".format(self.ha)
        str += "OS: {0}\n".format(self.os)
        str += "Hostname: {0}\n".format(self.hostname)
        str += "IP: {0}\n".format(self.ip)
        str += "CPU: {0}\n".format(self.cpu)
        str += "Memory (MB): {0}\n".format(self.mem)
        str += "NIC: {0}\n".format(self.nic)
        str += "HDD (committed): {0}\n".format(self.hd_committed)
        str += "HDD (uncommitted): {0}\n".format(self.hd_uncommitted)
        str += "Uptime: {0}\n".format(self.uptime)
        return str

class VirtualMachine:
    def __init__(self, service, name=None, uuid=None, ip=None):
        self.service = service
        self.vm = None

        if name:
            self.vm = self.service.content.searchIndex.FindByDnsName(None, name, True)
        elif uuid:
            self.vm = self.service.content.searchIndex.FindByUuid(None, uuid, True, True)
        elif ip:
            self.vm = self.service.content.searchIndex.FindByIp(None, ip, True)

        self.name = self.vm.name

    def print_details(self):
        details = {'Name': self.vm.summary.config.name,
                   'Instance UUID': self.vm.summary.config.instanceUuid,
                   'Bios UUID': self.vm.summary.config.uuid,
                   'Path to VM': self.vm.summary.config.vmPathName,
                   'Guest OS id': self.vm.summary.config.guestId,
                   'Guest OS name': self.vm.summary.config.guestFullName,
                   'Host': self.vm.runtime.host.name,
                   'Last booted timestamp': self.vm.runtime.bootTime }

        for name, value in details.items():
            print("  {0:{width}{base}}: {1}".format(name, value, width=25, base='s'))

        print("  Devices:")
        print("  --------")
        for device in self.vm.config.hardware.device:
            # diving into each device, we pull out a few interesting bits
            dev_details = {'summary': device.deviceInfo.summary,
                           'device type': type(device).__name__ }

            print("  label: {0}".format(device.deviceInfo.label))
            print("  ------------------")
            for name, value in dev_details.items():
                print("    {0:{width}{base}}: {1}".format(name, value, width=15, base='s'))

            if device.backing is None:
                continue

            # the following is a bit of a hack, but it lets us build a summary
            # without making many assumptions about the backing type, if the
            # backing type has a file name we *know* it's sitting on a datastore
            # and will have to have all of the following attributes.
            if hasattr(device.backing, 'fileName'):
                datastore = device.backing.datastore
                if datastore:
                    print("    datastore")
                    print("        name: {0}".format(datastore.name))
                    # there may be multiple hosts, the host property
                    # is a host mount info type not a host system type
                    # but we can navigate to the host system from there
                    for host_mount in datastore.host:
                        host_system = host_mount.key
                        print("        host: {0}".format(host_system.name))
                    print("        summary")
                    summary = {'capacity': sizeof_fmt(datastore.summary.capacity),
                               'freeSpace': sizeof_fmt(datastore.summary.freeSpace),
                               'file system': datastore.summary.type,
                               'url': datastore.summary.url }
                    for key, val in summary.items():
                        print("            {0}: {1}".format(key, val))
                print("    fileName: {0}".format(device.backing.fileName))
            print("  ------------------")

    def destroy(self):
        print 'Destroying VM %s' % self.name
        task = self.vm.Destroy_Task()
        WaitForTasks(self.service, [task])

    def create(self):
        print 'Creating VM %s' % self.name

    def start(self):
        print 'Starting VM %s' % self.name
        task = self.vm.PowerOnVM_Task()
        WaitForTasks(self.service, [task])

    def stop(self):
        print 'Stopping VM %s' % self.name
        task = self.vm.PowerOffVM_Task()
        WaitForTasks(self.service, [task])

    def reset(self):
        print 'Hard Reseting VM %s' % self.name
        task = self.vm.ResetVM_Task()
        WaitForTasks(self.service, [task])

    def reboot(self):
        print 'Soft Rebooting VM %s' % self.name
        self.vm.RebootGuest()

    def suspend(self):
        print 'Suspending VM %s' % self.name
        task = self.vm.SuspendVM_Task()
        WaitForTasks(self.service, [task])

class VirtualMachinePool:
    def __init__(self, service):
        self.vms = []
        self.cpu = 0
        self.mem = 0
        self.hd_committed = 0
        self.hd_uncommitted = 0

        content = service.RetrieveContent()
        children = content.rootFolder.childEntity
        for child in children:
            if not hasattr(child, 'vmFolder'): # some other non-datacenter type object
                continue

            datacenter = child
            vm_folder = datacenter.vmFolder
            vm_list = []
            vm_get_children(vm_list, vm_folder)

            for vm in vm_list:
                # discard templates
                if vm.summary.config.template:
                    continue

                vminfo = VirtualMachineInfo(vm)
                self.vms.append(vminfo)
                if vminfo.status == "poweredOn":
                    self.cpu += vminfo.cpu
                    self.mem += vminfo.mem
                    self.hd_committed += vminfo.hd_committed
                    self.hd_uncommitted += vminfo.hd_uncommitted

    def list(self):
        return self.vms

    def get(self, name):
        for vm in self.vms:
            if vm.name == name:
                return vm
        return None

class VirtualMachineCreation:
    def __init__(self, service, vm_name, cluster_name, template_name, memory, cpus, net_name, folder_name):

        content = service.RetrieveContent()
        children = content.rootFolder.childEntity
        for child in children:
            if hasattr(child, 'vmFolder'):
                datacenter = child
            else:
                # some other non-datacenter type object
                continue
            vm_folder = datacenter.vmFolder

        if folder_name != None:
            obj_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.Folder],True)
            folder_list = obj_view.view

            for folder in folder_list:
                if folder.name == folder_name:
                    vm_folder = folder

        template_vm = esx_get_obj(content, template_name, vim.VirtualMachine)

        devices = []

        if net_name != None:

            pg_obj = esx_get_obj(content, net_name, vim.dvs.DistributedVirtualPortgroup)
            dvs_port_connection = vim.dvs.PortConnection()
            dvs_port_connection.portgroupKey= pg_obj.key
            dvs_port_connection.switchUuid= pg_obj.config.distributedVirtualSwitch.uuid

            for device in template_vm.config.hardware.device:

                if isinstance(device, vim.vm.device.VirtualEthernetCard):

                    nicspec = vim.vm.device.VirtualDeviceSpec()

                    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                    nicspec.device = device
                    nicspec.device.deviceInfo.label = net_name
                    nicspec.device.deviceInfo.summary = net_name
                    nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                    nicspec.device.backing.port = dvs_port_connection

                    devices.append(nicspec)

        cluster = esx_get_obj(content, cluster_name, vim.ClusterComputeResource)
        resource_pool = cluster.resourcePool #

        # vm configuration
        vmconf = vim.vm.ConfigSpec()
        vmconf.numCPUs = cpus
        vmconf.memoryMB = memory
        vmconf.cpuHotAddEnabled = True
        vmconf.memoryHotAddEnabled = True
        if net_name != None:
            vmconf.deviceChange = devices

        relospec = vim.vm.RelocateSpec()
        relospec.pool = resource_pool

        clonespec = vim.vm.CloneSpec()
        clonespec.config = vmconf
        clonespec.location = relospec
        clonespec.powerOn = True

        try:
            clone = template_vm.Clone(folder= vm_folder, name=vm_name, spec=clonespec)
            WaitForTasks(service, [clone])
            print "vm %s successfully created" % vm_name
        except err:
            print err
