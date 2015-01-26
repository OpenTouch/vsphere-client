from pyVmomi import vim
from tabulate import tabulate
from misc import esx_objects, esx_name

###########
# HELPERS #
###########

def folders_get(service, name):
    folders = esx_objects(service, vim.Folder)
    for fd in folders:
        # try to lookup by key first
        ckey = esx_name(fd)
        if ckey == name:
            return EsxFolder(service, fd)

        # fallback to name lookup
        cname = fd.name
        if cname == name:
            return EsxFolder(service, fd)

    return None

def folder_get_all(service):
    l = []
    folders = esx_objects(service, vim.Folder)
    for fd in folders:
        f = EsxFolder(service, fd)
        l.append(f)
    return l

def folder_list(s, opt):
    pool = EsxFolderPool(s)
    headers = [ "Key", "Name", "Status" ]
    tabs = []
    for f in pool.folders:
       vals = [ f.key, f.name, f.status ]
       tabs.append(vals)

    print tabulate(tabs, headers)

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

class EsxFolderPool:
    def __init__(self, service):
        self.folders = folder_get_all(service)

    def list(self):
        return self.folders

    def get(self, name):
        for f in self.folders:
            if f.name == name:
                return f
        return None

    def __str__(self):
        r  = "ESXi Folders:\n"
        for f in self.folders:
            r += str(f)
        r += "\n"
        return r
