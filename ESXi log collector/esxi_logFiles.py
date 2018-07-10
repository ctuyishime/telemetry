import os
os.chdir("C:/Users/joshia2/Desktop/")

import csv
import ssl
import argparse
import atexit
import logging
import json
from pyVim.connect import SmartConnect , Disconnect
from datetime import datetime
from pyVmomi import vim
from elasticsearch import helpers, Elasticsearch


#data store variables
ds_name= []
ds_capacity = []
ds_provisionedSpace =[]
ds_freeSpace = []
ds_freeSpacePercentage = []


#data store variables
host_name= []
host_CPUusage = []
host_memoryCapacity =[]
host_memoryUsage = []
host_freeMemoryPercentage = []

# dictonary for about information
d= {}


# date time for every execution (keeping same date time for one batch)
x = datetime.now().strftime('%Y-%m-%d %H:%M:%S').split()
date = x[0]
time = x[1]


#for MB conversion
MBFACTOR = float(1 << 20)

# flags to get information ( use 1 or 0 as per requirement)
printVM ,printDatastore,printHost  = 1,1,1



# logging
formatter = logging.Formatter('%(message)s')


def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


# log handlers to capture different information
HostLogger = setup_logger('host_logger', 'hostlog.log')
DSLogger = setup_logger('ds_logger', 'dslog.log')
VMLogger = setup_logger('vm_logger', 'vmlog.log')

# creating empty logfiles
from pathlib import Path
Path('hostlog.log').touch()
Path('dslog.log').touch()
Path('vmlog.log').touch()


# putting the column headers in empty log files ( adhereing to CSV format )
if os.stat("hostlog.log").st_size == 0 :
    HostLogger.info("Date,Time,host_name,host_CPUusage,host_memoryCapacity,host_memoryUsage,host_freeMemoryPercentage")

if os.stat("dslog.log").st_size == 0 :
    DSLogger.info("Date,Time,ds_name, ds_capacity, ds_provisionedSpace,ds_freeSpace,ds_freeSpacePercentage")

if os.stat("vmlog.log").st_size == 0 :
    VMLogger.info("Date,Time,hostVMname, hostVMip, hostVMstate")



# taking in arguments from commandline
def validate_options():
    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('-s', '--source_host',dest='shost',
                         help='The ESXi source host IP')
    parser.add_argument('-u', '--username',dest='username',
                         help='The ESXi username')
    parser.add_argument('-p', '--password',dest='password',
                         help='The ESXi host password')
    args=parser.parse_args()
    return args


# get the host information
def about_information(aboutInfo) :
    d["productName"] = aboutInfo.fullName
    d["productbuild"] = aboutInfo.build
    d["productuniqueID"] = aboutInfo.instanceUuid
    d["productVersion"] = aboutInfo.version
    d["productVersion"] = aboutInfo.licenseProductName
    d["productBaseOS"] = aboutInfo.osType
    d["productVendor"]= aboutInfo.vendor




# get more in dept host infomation
def printHostInformation(host):
    
    try:
        summary = host.summary
        stats = summary.quickStats
        hardware = host.hardware
        cpuUsage = stats.overallCpuUsage
        memoryCapacity = hardware.memorySize
        memoryCapacityInMB = hardware.memorySize/MBFACTOR
        memoryUsage = stats.overallMemoryUsage
        freeMemoryPercentage = 100 - (
            (float(memoryUsage) / memoryCapacityInMB) * 100
        )
        #print("Host name: ", host.name)
        host_name.append(host.name)
        #print("Host CPU usage: ", cpuUsage)
        host_CPUusage.append(cpuUsage)
        #print("Host memory capacity: ", humanize.naturalsize(memoryCapacity, binary=True))
        host_memoryCapacity.append(memoryCapacity)
        #print("Host memory usage: ", memoryUsage / 1024, "GiB")
        host_memoryUsage.append(memoryUsage)
        #print("Free memory percentage: " + str(freeMemoryPercentage) + "%")
        host_freeMemoryPercentage.append(round(freeMemoryPercentage,2))
        #print("--------------------------------------------------")
    except Exception as error:
        print("Unable to access information for host: ", host.name)
        print(error)
        pass


def printComputeResourceInformation(computeResource):
    try:
        hostList = computeResource.host
        for host in hostList:
            printHostInformation(host)
    except Exception as error:
        print("Unable to access information for compute resource: ", end=' ')
        computeResource.name
        print(error)
        pass


# get datastore information
def printDatastoreInformation(datastore):
    
    try:
        summary = datastore.summary
        capacity = summary.capacity
        freeSpace = summary.freeSpace
        uncommittedSpace = summary.uncommitted
        freeSpacePercentage = (float(freeSpace) / capacity) * 100
        
        ds_name.append(summary.name)
        ds_capacity.append( capacity )
        
        if uncommittedSpace is not None:
            provisionedSpace = (capacity - freeSpace) + uncommittedSpace
            ds_provisionedSpace.append(provisionedSpace)

        ds_freeSpace.append(freeSpace)
        
        ds_freeSpacePercentage.append(round(freeSpacePercentage,2))
        

    except Exception as error:
        print("Unable to access summary for datastore: ", datastore.name)
        print(error)
        pass

#get VM information
def getVmInformation(esxi_hosts):
    
    hostVmsNames = [[(host.name) for host in eh.vm] for eh in esxi_hosts]

    hostVmsIps = [[(host.guest.ipAddress) for host in eh.vm] for eh in esxi_hosts]

    hostVmsState = [[(host.runtime.powerState) for host in eh.vm] for eh in esxi_hosts]

    return hostVmsNames,hostVmsIps,hostVmsState


def main() :
    
    opts=validate_options()
        
    # # Disabling SSL certificate verification
    s=ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    s.verify_mode=ssl.CERT_NONE
    

    try:
        si= SmartConnect(host=opts.shost,user=opts.username,pwd=opts.password ,sslContext=s )
        print('Collecting Information ! Please Wait ... ')

        content = si.RetrieveContent()
        
        #print about information : function call
        about_information(si.content.about )

        with open('about.json', 'w') as fp:
            json.dump(d, fp, indent=4)

        #disconnect the connection when program exists
        atexit.register(Disconnect, si)

        objview = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        esxi_hosts = objview.view
        
        for datacenter in content.rootFolder.childEntity:
            #print("Data Center Name : ", datacenter.name )

            if printVM:
                hostVmsNames,hostVmsIps,hostVmsState = getVmInformation(esxi_hosts)
                hostVmsNames,hostVmsIps,hostVmsState = hostVmsNames[0],hostVmsIps[0],hostVmsState[0]
        
                if printDatastore:
                    datastores = datacenter.datastore
                    for ds in datastores:
                        printDatastoreInformation(ds)

                if printHost:
                    if hasattr(datacenter.vmFolder, 'childEntity'):
                        hostFolder = datacenter.hostFolder
                        computeResourceList = hostFolder.childEntity
                        for computeResource in computeResourceList:
                            printComputeResourceInformation(computeResource)  

        for i in range(0,len(ds_name)):
            DSLogger.info("{},{},{},{},{},{},{}".format(date,time,ds_name[i], ds_capacity[i], ds_provisionedSpace[i],ds_freeSpace[i],ds_freeSpacePercentage[i]))

        for i in range(0,len(host_name)):
            HostLogger.info("{},{},{},{},{},{},{}".format(date,time,host_name[i], host_CPUusage[i], host_memoryCapacity[i],host_memoryUsage[i],host_freeMemoryPercentage[i]))

        hostVmsIps = ['None' if v is None else v for v in hostVmsIps]

        for i in range(0,len(hostVmsNames)):
            VMLogger.info("{},{},{},{},{}".format(date,time,hostVmsNames[i], hostVmsIps[i], hostVmsState[i]))
        
        es = Elasticsearch([{'host': '100.80.96.7', 'port': 9200 , 'user':"elastic", "password": "dna"}])

        with open('vmlog.log') as f:
            reader = csv.DictReader(f)
            helpers.bulk(es, reader, index='vm-index', doc_type='log')

    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))




if __name__ == '__main__':
    main()

