#!/usr/bin/env python2.7

"""
Interactive CLI for VMware vSphere orchestration.

Usage:
    vsphere.py dc list
    vsphere.py dc net <name>
    vsphere.py dc ds <name>
    vsphere.py host list
    vsphere.py host hw <name>
    vsphere.py host net <name>
    vsphere.py host ds <name>
    vsphere.py host perf <name>
    vsphere.py vm list [<name>]
    vsphere.py vm details <name>
    vsphere.py vm create <name> <template> [--mem=<memory>] [--cpu=<cpu>] [--network=<network_name>] [--folder=<Where_the_vm_is_stored>]
    vsphere.py vm delete <name>
    vsphere.py vm start <name>
    vsphere.py vm stop <name>
    vsphere.py vm reset <name>
    vsphere.py vm reboot <name>
    vsphere.py vm suspend <name>
    vsphere.py template list [<name>]
    vsphere.py pool list
    vsphere.py datastore list
    vsphere.py datastore browse <name> <path>
    vsphere.py datastore download <name> <path>
    vsphere.py datastore upload <name> <file> <path>

Options:
    -h, --help         Show this screen and exit.
    -v, --version      Show this program version number.
"""

import os, sys, stat, cmd, re, time
from docopt import docopt, DocoptExit
from pyVim import connect
from pyVmomi import vmodl, vim
import atexit
from config import EsxConfig
from dc import dc_parser
from host import host_parser
from vm import vm_parser
from pool import pool_parser
from template import template_parser
from datastore import datastore_parser

VERSION = "1.0"

def opt_parser(opt):
    if   opt['vm']        == True: vm_parser(service, opt)
    elif opt['template']  == True: template_parser(service, opt)
    elif opt['pool']      == True: pool_parser(service, opt)
    elif opt['host']      == True: host_parser(service, opt)
    elif opt['dc']        == True: dc_parser(service, opt)
    elif opt['datastore'] == True: datastore_parser(service, opt)

########
# MAIN #
########

# use UTF-8 encoding instead of unicode to support more characters
reload(sys)
sys.setdefaultencoding("utf-8")

# disable SSL/TLS warnings
#import requests
#requests.packages.urllib3.disable_warnings()

cfg = EsxConfig()

# Connect to vSphere
service = connect.SmartConnect(host=cfg.vs_host, user=cfg.vs_user, pwd=cfg.vs_password, compress=False)
atexit.register(connect.Disconnect, service)

#from misc import esx_objects
#objs = esx_objects(service)
#print objs

# Parse command-line
opt = docopt(__doc__, version=VERSION, argv=sys.argv[1:])
opt_parser(opt)
