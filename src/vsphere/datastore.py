import urllib, urllib2
from tabulate import tabulate
from pyVmomi import vim
from tasks import WaitForTasks
from misc import sizeof_fmt, esx_object_find, esx_objects, esx_name
from config import EsxConfig

###########
# HELPERS #
###########

def ds_get(service, name):
    x = esx_object_find(service, vim.Datastore, name)
    if x: return EsxDataStore(service, x)
    return None

def ds_get_all(service):
    l = []
    stores = esx_objects(service, vim.Datastore)
    for s in stores:
        dc = EsxDataStore(service, s)
        l.append(dc)
    return l

def ds_print_details(ds):
    tabs = []
    headers = [ "Key", "Name", "Type", "Capacity", "Free Space", "Local", "SSD", "Remote Host", "Remote Path" ]

    for d in ds:
        d.info()
        local = "False"
        if d.local: local = "True"
        ssd = "False"
        if d.ssd: ssd = "True"

        vals = [ d.key, d.name, d.type, sizeof_fmt(d.capacity), sizeof_fmt(d.free_space),
                 local, ssd, d.host, d.path ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def datastore_list(s, opt):
    ds = ds_get_all(s)
    ds_print_details(ds)

def ds_print_content(files):
    tabs = []
    headers = [ "Name", "Size", "Owner", "Modification Time" ]

    for f in files:
        vals = [ f.fullpath, sizeof_fmt(f.size), f.owner, f.modification ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def datastore_browse(s, opt):
    ds_name = opt['<name>']
    ds_path = opt['<path>']

    ds = ds_get(s, ds_name)
    if not ds:
        return

    files = ds.browse(ds_path)
    ds_print_content(files)

def datastore_download(s, opt):
    ds = ds_get(s, opt['<name>'])
    if not ds:
        return

    remote = opt['<path>']
    local = remote.split('/')[-1]
    ds.download(remote, local)

def datastore_upload(s, opt):
    ds_name = opt['<name>']

    ds = ds_get(s, opt['<name>'])
    if not ds:
        return

    local = opt['<file>']
    remote = opt['<path>']
    ds.upload(local, remote)

def datastore_parser(service, opt):
    if   opt['list']     == True: datastore_list(service, opt)
    elif opt['browse']   == True: datastore_browse(service, opt)
    elif opt['download'] == True: datastore_download(service, opt)
    elif opt['upload']   == True: datastore_upload(service, opt)

###########
# CLASSES #
###########

class EsxDataStoreFile:
    def __init__(self, dc, f, folder):
        dc_name = "[{0}] ".format(dc)

        self.file = f.path
        self.folder = folder.split(dc_name)[1]
        self.fullpath = "{0}{1}".format(self.folder, self.file)
        self.size = f.fileSize
        self.owner = f.owner
        self.modification = f.modification

    def __str__(self):
        return self.fullpath

class EsxDataStore:
    def __init__(self, service, ds):
        self.service     = service
        self.ds          = ds
        self.key         = esx_name(ds)
        self.name        = ds.name

    def info(self):
        self.info        = self.ds.info
        self.name        = self.info.name
        self.free_space  = self.info.freeSpace

        if type(self.info) == vim.host.NasDatastoreInfo:
            self.type        = self.info.nas.type
            self.capacity    = self.info.nas.capacity
            self.local       = None
            self.ssd         = None
            self.host        = self.info.nas.remoteHost
            self.path        = self.info.nas.remotePath
        elif type(self.info) == vim.host.VmfsDatastoreInfo:
            self.type        = self.info.vmfs.type
            self.capacity    = self.info.vmfs.capacity
            self.local       = self.info.vmfs.local
            self.ssd         = self.info.vmfs.ssd
            self.host        = ""
            self.path        = ""

    def browse(self, p, recurse=True):
        path = "[{0}] {1}".format(self.ds.name, p)
        files = []
        try:
            # define search criterias
            search = vim.host.DatastoreBrowser.SearchSpec()
            search.sortFoldersFirst = True
            details = vim.host.DatastoreBrowser.FileInfo.Details()
            details.fileType = True
            details.fileSize = True
            details.fileOwner = True
            details.modification = True
            search.details = details

            # start browsing
            if recurse:
                task = self.ds.browser.SearchSubFolders(path, search)
            else:
                task = self.ds.browser.SearchSub(path, search)

            WaitForTasks(self.service, [task])
            results = task.info.result
            for r in results:
                for f in r.file:
                    # discard folders
                    if r.folderPath == "[" + self.ds.name + "]":
                        continue
                    dsf = EsxDataStoreFile(self.ds.name, f, r.folderPath)
                    files.append(dsf)
        except:
           print "No such directory: {0}".format(p)

        files.sort(key=lambda x: x.fullpath)
        return files

    def config(self):
        cfg = EsxConfig()
        self.cfg_url = "https://{0}:443".format(cfg.vs_host)
        self.cfg_user = cfg.vs_user
        self.cfg_password = cfg.vs_password

        # find the datacenter name the datastore belongs to
        dc = self.ds.parent
        while not isinstance(dc, vim.Datacenter):
            dc = dc.parent
        self.cfg_dc = dc.name

    def get_url(self, resource):
        if not resource.startswith("/"):
            resource = "/" + resource

        params = { "dsName" : self.name }
        params["dcPath"] = self.cfg_dc
        params = urllib.urlencode(params)
        return "%s%s?%s" % (self.cfg_url, resource, params)

    def build_auth_handler(self):
        auth_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        auth_manager.add_password(None, self.cfg_url, self.cfg_user, self.cfg_password)
        return urllib2.HTTPBasicAuthHandler(auth_manager)

    def do_request(self, url, data=None):
        handler = self.build_auth_handler()
        opener = urllib2.build_opener(handler)
        request = urllib2.Request(url, data = data)
        if data:
            request.get_method = lambda: 'PUT'
        return opener.open(request)

    def download(self, remote, local):
        print "Saving remote {0} to local file {1}".format(remote, local)
        self.config()
        resource = "/folder/%s" % remote.lstrip("/")
        url = self.get_url(resource)
        resp = self.do_request(url)
        CHUNK = 16 * 1024
        fd = open(local, "wb")
        while True:
            chunk = resp.read(CHUNK)
            if not chunk: break
            fd.write(chunk)
        fd.close()

    def upload(self, local, remote):
        print "Uploading local file {0} to remote {1}".format(local, remote)
        self.config()
        fd = open(local, "rb")
        data = fd.read()
        fd.close()
        resource = "/folder/%s" % remote.lstrip("/")
        url = self.get_url(resource)
        resp = self.do_request(url, data)
        fd.close()

    def __str__(self):
        return self.name
