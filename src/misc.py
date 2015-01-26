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
    obj = None
    vimtype = []
    if kind: vimtype = [kind]
    content = service.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

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
