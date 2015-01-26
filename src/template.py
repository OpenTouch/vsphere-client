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

def template_print_details(templates):
    tabs = []
    headers = [ "Key", "Name", "Folder", "OS", "CPUs", "Mem (MB)", "NIC" ]

    for t in templates:
        info = t.info()
        vals = [ t.key, info.name, info.folder, info.os, info.cpu, info.mem, info.nic ]
        tabs.append(vals)
        tabs.sort(reverse=False)

    print tabulate(tabs, headers)

def template_list(s, opt):
    templates = template_get_all(s)
    template_print_details(templates)

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
        self.key = esx_name(template)
        self.name = template.name

    def info(self):
        return EsxTemplateInfo(self.template)

    def __str__(self):
        return self.name
