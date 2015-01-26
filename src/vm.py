from pyVmomi import vim
from tasks import WaitForTasks
from tabulate import tabulate
from misc import sizeof_fmt, humanize_time, esx_get_obj, esx_name, esx_objects

VM_DEFAULT_MEMORY = 1024 # MB
VM_DEFAULT_CPU = 1

###########
# HELPERS #
###########

def vm_get(service, name):
    vms = esx_objects(service, vim.VirtualMachine)
    for v in vms:
        if v.name == name:
            return EsxVirtualMachine(service, v)
    return None

def vm_get_all(service):
    l = []
    vms = esx_objects(service, vim.VirtualMachine)
    for v in vms:
        if v.summary.config.template:
            continue
        vm = EsxVirtualMachine(service, v)
        l.append(vm)
    return l

def vm_guess_folder(vm):
    if vm.parent.name != "vm":
        return vm_guess_folder(vm.parent) + vm.parent.name
    return "/"

def vm_list(s, opt):
    pool = EsxVirtualMachinePool(s)
    vms = pool.list()

    tabs = []
    headers = [ "Name", "Status", "Host", "Folder", "OS", "IP", "CPUs", "Mem (MB)", "NIC", "HDD (GB)", "Uptime" ]

    for v in vms:
        # retrieve infos
        vm = v.info()
        vals = [ vm.name, vm.status, vm.host, vm.folder,
                 vm.os, vm.ip, vm.cpu, vm.mem, vm.nic, vm.hd_size, vm.uptime ]
        tabs.append(vals)
        tabs.sort(reverse=False)

    print tabulate(tabs, headers)

def vm_details(s, opt):
    vm = vm_get(s, opt['<name>'])
    if not vm:
        return

    d = vm.details()
    details = {
        'Name': d.name,
        'Instance UUID': d.instance_uuid[0],
        'Bios UUID': d.bios_uuid,
        'Path to VM': d.path,
        'Guest OS id': d.guest_id[0],
        'Guest OS name': d.guest_name,
        'Host': d.host[0],
        'Last booted timestamp': d.ts
    }

    for name, value in details.items():
        print("  {0:{width}{base}}: {1}".format(name, value, width=25, base='s'))

    print("  Devices:")
    print("  --------")
    for dev in d.devices:
        dev_details = {
            'summary': dev.summary,
            'device type': dev.type
        }

        print("  label: {0}".format(dev.label))
        print("  ------------------")
        for name, value in dev_details.items():
            print("    {0:{width}{base}}: {1}".format(name, value, width=15, base='s'))

            ds = dev.ds
            if ds is None:
                continue

            print("    datastore")
            print("        name: {0}".format(ds.ds_name))
            print("        summary")
            summary = {
                'capacity': sizeof_fmt(ds.ds_capacity),
                'freeSpace': sizeof_fmt(ds.ds_freespace),
                'file system': ds.ds_fs,
                'url': ds.ds_url
            }
            for key, val in summary.items():
                print("            {0}: {1}".format(key, val))
            print("    fileName: {0}".format(ds.filename))
            print("  ------------------")

def vm_spawn(service, name, cluster, template, memory, cpus, net, folder):

    print 'Trying to clone %s to VM %s' % (template, name)
    if esx_get_obj(s.RetrieveContent(), name, vim.VirtualMachine) != None:
        print 'ERROR: %s already exists' % name
        return

    content = service.RetrieveContent()
    children = content.rootFolder.childEntity
    for child in children:
        if hasattr(child, 'vmFolder'):
            datacenter = child
        else:
            # some other non-datacenter type object
            continue
        vm_folder = datacenter.vmFolder

    if folder != None:
        obj_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.Folder],True)
        folder_list = obj_view.view

        for f in folder_list:
            if f.name == folder:
                vm_folder = f

    template_vm = esx_get_obj(content, template, vim.VirtualMachine)
    devices = []

    if net != None:
        pg_obj = esx_get_obj(content, net, vim.dvs.DistributedVirtualPortgroup)
        dvs_port_connection = vim.dvs.PortConnection()
        dvs_port_connection.portgroupKey= pg_obj.key
        dvs_port_connection.switchUuid= pg_obj.config.distributedVirtualSwitch.uuid

        for device in template_vm.config.hardware.device:

            if isinstance(device, vim.vm.device.VirtualEthernetCard):

                nicspec = vim.vm.device.VirtualDeviceSpec()

                nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.deviceInfo.label = net
                nicspec.device.deviceInfo.summary = net
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nicspec.device.backing.port = dvs_port_connection

                devices.append(nicspec)

    cl = esx_get_obj(content, cluster, vim.ClusterComputeResource)
    resource_pool = cl.resourcePool #

    # vm configuration
    vmconf = vim.vm.ConfigSpec()
    vmconf.numCPUs = cpus
    vmconf.memoryMB = memory
    vmconf.cpuHotAddEnabled = True
    vmconf.memoryHotAddEnabled = True
    if net != None:
        vmconf.deviceChange = devices

    relospec = vim.vm.RelocateSpec()
    relospec.pool = resource_pool

    clonespec = vim.vm.CloneSpec()
    clonespec.config = vmconf
    clonespec.location = relospec
    clonespec.powerOn = True

    try:
        clone = template_vm.Clone(folder= vm_folder, name=name, spec=clonespec)
        WaitForTasks(service, [clone])
        print "vm %s successfully created" % name
    except err:
        print err

def vm_create(s, opt):
    vm_name = opt['<name>']
    template = opt['<template>']
    net_name = opt['--network']
    memory = int(opt['--mem'])
    if memory is None:
        memory = VM_DEFAULT_MEMORY
    cpus = int(opt['--cpu'])
    if cpus is None:
        cpus = VM_DEFAULT_CPU
    folder = opt['--folder']

    vm_spawn(s, vm_name, "Cluster1", template, memory, cpus, net_name, folder)

def vm_delete(s, opt):
    vm = vm_get(s, opt['<name>'])
    if vm:
        vm.stop()
        vm.destroy()

def vm_start(s, opt):
    vm = vm_get(s, opt['<name>'])
    if vm:
        vm.start()

def vm_stop(s, opt):
    vm = vm_get(s, opt['<name>'])
    if vm:
        vm.stop()

def vm_reset(s, opt):
    vm = vm_get(s, opt['<name>'])
    if vm:
        vm.reset()

def vm_reboot(s, opt):
    vm = vm_get(s, opt['<name>'])
    if vm:
        vm.reboot()

def vm_suspend(s, opt):
    vm = vm_get(s, opt['<name>'])
    if vm:
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

class EsxVirtualMachineInfo:
    def __init__(self, vm):
        summary = vm.summary
        config = summary.config
        runtime = summary.runtime
        guest = summary.guest
        storage = summary.storage
        stats = summary.quickStats

        self.name = config.name
        self.status = runtime.powerState
        self.host = esx_name(str(runtime.host))
        self.folder = vm_guess_folder(vm)
        self.os = config.guestFullName
        self.hostname = guest.hostName
        self.ip = guest.ipAddress
        self.cpu = config.numCpu
        self.mem = config.memorySizeMB
        self.nic = config.numEthernetCards
        self.hd_size = (storage.committed + storage.uncommitted) / 1024 / 1024 / 1024
        self.uptime = humanize_time(stats.uptimeSeconds)

class EsxVirtualMachineDeviceHDD:
    def __init__(self, ds, filename):
        self.ds_name = ds.name
        self.ds_capacity = ds.summary.capacity
        self.ds_freespace = ds.summary.freeSpace
        self.ds_fs = ds.summary.type
        self.ds_url = ds.summary.url
        self.filename = filename

class EsxVirtualMachineDevice:
    def __init__(self, d):
        self.summary = d.deviceInfo.summary
        self.type = type(d).__name__
        self.label = d.deviceInfo.label

        self.ds = None
        if d.backing:
            # the following is a bit of a hack, but it lets us build a summary
            # without making many assumptions about the backing type, if the
            # backing type has a file name we *know* it's sitting on a datastore
            # and will have to have all of the following attributes.
            if hasattr(d.backing, 'fileName'):
                datastore = d.backing.datastore
                if datastore:
                    self.ds = EsxVirtualMachineDeviceHDD(datastore, d.backing.fileName)

class EsxVirtualMachineDetails:
    def __init__(self, vm):
        self.name = vm.summary.config.name
        self.instance_uuid = vm.summary.config.instanceUuid,
        self.bios_uuid = vm.summary.config.uuid
        self.path = vm.summary.config.vmPathName
        self.guest_id = vm.summary.config.guestId,
        self.guest_name = vm.summary.config.guestFullName
        self.host = vm.runtime.host.name,
        self.ts = vm.runtime.bootTime

        self.devices = []
        for dev in vm.config.hardware.device:
            d = EsxVirtualMachineDevice(dev)
            self.devices.append(d)

class EsxVirtualMachine:
    def __init__(self, service, vm):
        self.service = service
        self.vm = vm
        self.name = self.vm.name

    def __str__(self):
        return self.name

    def info(self):
        return EsxVirtualMachineInfo(self.vm)

    def details(self):
        return EsxVirtualMachineDetails(self.vm)

    def _task(self, name, t):
        print '{0} VM {1}'.format(name, self.name)
        WaitForTasks(self.service, [t])

    def destroy(self):
        self._task('Destroying', self.vm.Destroy_Task())

    def start(self):
        self._task('Starting', self.vm.PowerOnVM_Task())

    def stop(self):
        self._task('Stopping', self.vm.PowerOffVM_Task())

    def reset(self):
        self._task('Hard Reseting', self.vm.ResetVM_Task())

    def reboot(self):
        print 'Soft Rebooting VM %s' % self.name
        self.vm.RebootGuest()

    def suspend(self):
        self._task('Suspending', self.vm.SuspendVM_Task())

class EsxVirtualMachinePool:
    def __init__(self, service):
        self.vms = vm_get_all(service)

    def list(self):
        return self.vms

    def get(self, name):
        for vm in self.vms:
            if vm.name == name:
                return vm
        return None

    def __str__(self):
        r  = "ESXi Virtual Machines:\n"
        for t in self.vms:
            r += str(t)
        r += "\n"
        return r
