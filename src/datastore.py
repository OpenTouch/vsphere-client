import urllib, urllib2
from tabulate import tabulate
from pyVmomi import vim
from tasks import WaitForTasks
from misc import sizeof_fmt, esx_objects
from config import EsxConfig

###########
# HELPERS #
###########

def ds_get(service, name):
    stores = esx_objects(service, vim.Datastore)
    for ds in stores:
        if ds.info.name == name:
            return EsxDataStore(service, ds)

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
    headers = [ "Name", "Type", "Capacity", "Free Space", "Local", "SSD", "Remote Host", "Remote Path" ]

    for d in ds:
        d.info()
        local = "False"
        if d.local: local = "True"
        ssd = "False"
        if d.ssd: ssd = "True"

        vals = [ d.name, d.type, sizeof_fmt(d.capacity), sizeof_fmt(d.free_space),
                 local, ssd, d.host, d.path ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def get_service_url(cfg):
    return "https://{0}:443".format(cfg.vs_host)

def get_url(cfg, ds_name, resource):
    if not resource.startswith("/"):
        resource = "/" + resource

    params = { "dsName" : ds_name }
    params["dcPath"] = cfg.vs_dc
    params = urllib.urlencode(params)
    return "%s%s?%s" % (get_service_url(cfg), resource, params)

def build_auth_handler(cfg):
    service_url = get_service_url(cfg)
    user = cfg.vs_user
    password = cfg.vs_password
    auth_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    auth_manager.add_password(None, service_url, user, password)
    return urllib2.HTTPBasicAuthHandler(auth_manager)

def do_request(cfg, url, data=None):
    handler = build_auth_handler(cfg)
    opener = urllib2.build_opener(handler)
    request = urllib2.Request(url, data = data)
    if data:
        request.get_method = lambda: 'PUT'
    return opener.open(request)

def datastore_list(s, opt):
    ds = ds_get_all(s)
    ds_print_details(ds)

def datastore_browse(s, opt):
    ds_name = opt['<name>']
    ds_path = opt['<path>']

    ds = ds_get(s, ds_name)
    if not ds:
        return

    files = ds.browse(ds_path)
    if not files:
        return

    tabs = []
    headers = [ "Name", "Size", "Owner", "Modification Time" ]

    for f in files:
        vals = [ f.fullpath, sizeof_fmt(f.size), f.owner, f.modification ]
        tabs.append(vals)

    print tabulate(tabs, headers)

def datastore_download(s, opt):
    ds_name = opt['<name>']
    ds_path = opt['<path>']

    cfg = EsxConfig()

    resource = "/folder/%s" % ds_path.lstrip("/")
    url = get_url(cfg, ds_name, resource)
    local_file = ds_path.split('/')[-1]
    print "Saving remote {0} to local file {1}".format(ds_path, local_file)

    resp = do_request(cfg, url)
    CHUNK = 16 * 1024
    fd = open(local_file, "wb")
    while True:
        chunk = resp.read(CHUNK)
        if not chunk: break
        fd.write(chunk)
    fd.close()

def datastore_upload(s, opt):
    ds_name = opt['<name>']
    ds_file = opt['<file>']
    ds_path = opt['<path>']

    print "Uploading local file {0} to remote {1}".format(ds_file, ds_path)

    try:
        fd = open(ds_file, "rb")
        data = fd.read()
        fd.close()
        resource = "/folder/%s" % ds_path.lstrip("/")
        cfg = EsxConfig()
        url = get_url(cfg, ds_name, resource)
        resp = do_request(cfg, url, data)
        fd.close()
    except:
        print "ERROR uploading file"

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

    def __str__(self):
        r  = "Name: {0}\n".format(self.name)
        r += "Type: {0}\n".format(self.type)
        r += "Capacity: {0}\n".format(sizeof_fmt(self.capacity))
        r += "Free Space: {0}\n".format(sizeof_fmt(self.free_space))
        return r
