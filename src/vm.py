from pyVmomi import vim
from tasks import WaitForTasks
from tabulate import tabulate
from misc import sizeof_fmt, humanize_time, esx_get_obj, esx_name, esx_objects

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

def vm_print_details(vms):
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

def vm_list(s, opt):
    vms = vm_get_all(s)
    vm_print_details(vms)

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

def vm_spawn(service, name, template, cluster=None, mem=None, cpu=None, net=None, folder=None):

    print 'Trying to clone %s to VM %s' % (template, name)

    # ensure no VM with the same name already exists
    if esx_get_obj(service, name, vim.VirtualMachine) != None:
        print 'ERROR: %s already exists' % name
        return

    # ensure the template exists
    template_vm = esx_get_obj(service, template, vim.VirtualMachine)
    if not template_vm:
        print "ERROR: Can't find requested template %s" % template
        return

    # find the right cluster and/or ressource pool
    if cluster:
        cl = esx_get_obj(service, cluster, vim.ClusterComputeResource)
    else:
        cls = esx_objects(service, vim.ClusterComputeResource)
        cl = cls[0]
    rs = vim.vm.RelocateSpec()
    rs.pool = cl.resourcePool

    # ensure we find an appropriate folder
    if not folder: folder = "vm"
    vm_folder = esx_get_obj(service, folder, kind=vim.Folder)
    if not vm_folder:
        print "ERROR: Can't find requested folder %s" % folder
        return

    # build custom devices (if necessary)
    devices = []

    if net:
        pg = esx_get_obj(service, net, vim.dvs.DistributedVirtualPortgroup)
        if not pg:
            print "ERROR: Can't find requested network %s" % net
            return

        pc = vim.dvs.PortConnection()
        pc.portgroupKey= pg.key
        pc.switchUuid = pg.config.distributedVirtualSwitch.uuid

        for device in template_vm.config.hardware.device:
            if not isinstance(device, vim.vm.device.VirtualEthernetCard):
                continue

            nic = vim.vm.device.VirtualDeviceSpec()
            nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            nic.device = device
            nic.device.deviceInfo.label = net
            nic.device.deviceInfo.summary = net
            nic.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
            nic.device.backing.port = pc
            devices.append(nic)

    # vm custom configuration (if necessary)
    if cpu and mem:
        cf = vim.vm.ConfigSpec()
        cf.numCPUs = int(cpu)
        cf.memoryMB = int(mem)
        cf.cpuHotAddEnabled = True
        cf.memoryHotAddEnabled = True
        if net:
            cf.deviceChange = devices

    cs = vim.vm.CloneSpec()
    if cpu and mem:
        cs.config = cf
    cs.location = rs
    cs.powerOn = True

    try:
        task = template_vm.Clone(folder=vm_folder, name=name, spec=cs)
        WaitForTasks(service, [task])
        print "VM %s successfully created" % name
    except err:
        print err

def vm_create(s, opt):
    name = opt['<name>']
    template = opt['<template>']
    net = opt['--network']
    mem = opt['--mem']
    cpu = opt['--cpu']
    folder = opt['--folder']

    vm_spawn(s, name, template, "Cluster1", mem, cpu, net, folder)

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
