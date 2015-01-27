def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)
    return '%02dd %02dh %02dm %02ds' % (days, hours, mins, secs)

def sizeof_fmt(num):
    for item in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

"""
 Get the vsphere object associated with a given text name
"""
def esx_get_obj(service, name, kind=None):
    objs = esx_objects(service, kind)
    for o in objs:
        if o.name == name:
            return o
    return None

def esx_objects(service, kind=None):
    objs = []
    vimtype = []
    if kind: vimtype = [kind]
    content = service.RetrieveContent()
    view = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for o in view.view:
        objs.append(o)
    view.Destroy()

    return objs

def esx_name(obj):
    return str(obj).split(':')[1].strip("'")

def esx_object_find(service, vim_type, name):
    objs = esx_objects(service, vim_type)
    for obj in objs:
        # try to lookup by key first
        ckey = esx_name(obj)
        if ckey == name:
            return obj

        # fallback to name lookup
        cname = obj.name
        if cname == name:
            return obj

    return None

def esx_object_get_items(service, items, obj):
    l = []
    for x in items:
        ds = obj(service, x)
        l.append(ds)
    return l
