from pyVmomi import vim
from tabulate import tabulate
from vm import vm_get_children, vm_guess_folder

###########
# HELPERS #
###########

def template_display_properties(templates):
    tabs = []
    headers = [ "Name", "Pool", "Folder", "OS", "CPUs", "Mem (MB)", "NIC" ]

    for t in templates:
        vals = [ t.name, t.pool, t.folder, t.os, t.cpu, t.mem, t.nic ]
        tabs.append(vals)
        tabs.sort(reverse=False)

    print tabulate(tabs, headers)

def template_list(s, opt):
    pool = TemplatePool(s)
    template_name = opt['<name>']
    if template_name:
        t = pool.get(template_name)
        template_display_properties([t])
    else:
        tmpls = pool.list()
        template_display_properties(tmpls)

def template_parser(service, opt):
    if opt['list'] == True: template_list(service, opt)

###########
# CLASSES #
###########

class TemplateInfo:
    def __init__(self, vm):
        summary = vm.summary
        config = summary.config

        self.name = config.name
        self.pool = config.vmPathName.split(' ')[0].strip('[').strip(']')
        self.folder = vm_guess_folder(vm)
        self.os = config.guestFullName
        self.cpu = config.numCpu
        self.mem = config.memorySizeMB
        self.nic = config.numEthernetCards
    def __str__(self):
        str  = "Name: {0}\n".format(self.name)
        str += "Pool: {0}\n".format(self.pool)
        str += "Folder: {0}\n".format(self.folder)
        str += "OS: {0}\n".format(self.os)
        str += "CPU: {0}\n".format(self.cpu)
        str += "Memory (MB): {0}\n".format(self.mem)
        str += "NIC: {0}\n".format(self.nic)
        return str

class TemplatePool:
    def __init__(self, service):
        self.templates = []

        content = service.RetrieveContent()
        children = content.rootFolder.childEntity
        for child in children:
            if not hasattr(child, 'vmFolder'): # some other non-datacenter type object
                continue

            datacenter = child
            vm_folder = datacenter.vmFolder
            tmpl_list = []
            vm_get_children(tmpl_list, vm_folder)

            for t in tmpl_list:
                # this one collapses everything, dunno why:
                if t.name.startswith("pfsense"):
                    continue

                # discard VMs
                if not t.summary.config.template:
                    continue

                info = TemplateInfo(t)
                self.templates.append(info)

    def list(self):
        return self.templates

    def get(self, name):
        for t in self.templates:
            if t.name == name:
                return t
        return None
