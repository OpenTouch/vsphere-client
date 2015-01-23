from pyVmomi import vim
from tabulate import tabulate
from vm import vm_guess_folder
from misc import esx_name, esx_objects

###########
# HELPERS #
###########

def template_get_all(service):
    l = []
    vms = esx_objects(service, vim.VirtualMachine)
    for v in vms:
        if not v.summary.config.template:
            continue
        vm = EsxTemplate(service, v)
        l.append(vm)
    return l

def template_list(s, opt):
    pool = EsxTemplatePool(s)
    tmpls = pool.list()

    tabs = []
    headers = [ "Name", "Folder", "OS", "CPUs", "Mem (MB)", "NIC" ]

    for t in tmpls:
        info = t.info()

        vals = [ info.name, info.folder, info.os, info.cpu, info.mem, info.nic ]
        tabs.append(vals)
        tabs.sort(reverse=False)

    print tabulate(tabs, headers)

def template_parser(service, opt):
    if opt['list'] == True: template_list(service, opt)

###########
# CLASSES #
###########

class EsxTemplateInfo:
    def __init__(self, t):
        summary = t.summary
        config = summary.config

        self.name   = config.name
        self.folder = vm_guess_folder(t)
        self.os     = config.guestFullName
        self.cpu    = config.numCpu
        self.mem    = config.memorySizeMB
        self.nic    = config.numEthernetCards

class EsxTemplate:
    def __init__(self, service, template):
        self.service = service
        self.template = template
        self.name = template.name

    def info(self):
        return EsxTemplateInfo(self.template)

    def __str__(self):
        return self.name

class EsxTemplatePool:
    def __init__(self, service):
        self.templates = template_get_all(service)

    def list(self):
        return self.templates

    def get(self, name):
        for t in self.templates:
            if t.name == name:
                return t
        return None

    def __str__(self):
        r  = "ESXi Templates:\n"
        for t in self.templates:
            r += str(t)
        r += "\n"
        return r
