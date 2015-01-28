from pyVmomi import vim
from tabulate import tabulate
from misc import esx_objects_retrieve, esx_name, esx_object_find

###########
# HELPERS #
###########

def folder_get(service, name=None):
    return esx_objects_retrieve(service, vim.Folder, EsxFolder, name)

def folder_print_details(folders):
    headers = [ "Key", "Name", "Status" ]
    tabs = []
    for f in folders:
       vals = [ f.key, f.name, f.status ]
       tabs.append(vals)

    print tabulate(tabs, headers)

def folder_list(s, opt):
    folders = folder_get(s)
    folder_print_details(folders)

def folder_parser(service, opt):
    if   opt['list']  == True: folder_list(service, opt)

###########
# CLASSES #
###########

class EsxFolder:
    def __init__(self, service, folder):
        self.service = service
        self.folder = folder
        self.key = esx_name(folder)
        self.name = folder.name
        self.status = folder.overallStatus

    def __str__(self):
        return self.name
