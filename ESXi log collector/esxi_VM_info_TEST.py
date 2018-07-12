import os
os.chdir("C:/Users/joshia2/Desktop/")

from os import path
import ssl
import argparse
import atexit
import re
from time import clock
from pyVim.connect import SmartConnect , Disconnect
from datetime import datetime ,timedelta
from pyVmomi import vim
from elasticsearch import helpers, Elasticsearch
import logging
import csv
import time
collection_time = datetime.utcnow()

# flags to get information ( use 1 or 0 as per requirement)
printVM ,printDatastore,printHost  = 1,1,1


# date time for every execution (keeping same date time for one batch)
#x = datetime.now().strftime('%Y-%m-%d %H:%M:%S').split()
#date = x[0]
#time = x[1]


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

VMLogger = setup_logger('vm_logger', 'vmlog.log')

# creating empty logfiles
from pathlib import Path
Path('vmlog.log').touch()

if os.stat("vmlog.log").st_size == 0 :
    VMLogger.info("Date,Time,vmName, vmTemplate, vmPath , vmDSlocation , vmGuest , vmInstanceUUID,vmBioUUID, vmIP , VMwareTools , vmGuest1 , vmNumCPU , vmMemory , vmStatus , vmState , vmCPUready , vmCPUusage , vmMEMactive , vmMEMshared , vmMEMballoon , vmDS_readIO , vmDS_writeIO, vmDS_finalIO , vmDS_readLatency, vmDS_writeLatency , vmDS_totalLatency , vm_NetUsageRx , vm_NetUsageTx , vm_NetUsageTotal")



vmName =[]
vmTemplate =[]
vmPath = []
vmDSlocation = []
vmGuest= []
vmInstanceUUID = []
vmBioUUID = []
vmIP = []


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


def create_perf_dictionary(content):
    """
    Checks whether the connection is to an ESXi host or vCenter and calls the write_perf_dictionary
    function with the relevant file name.

    :param content: ServiceInstance Managed Object
    """
    if content.about.name == 'VMware vCenter Server':
        print("Connected to VMware vCenter Server !")
        perf_dict = write_perf_dictionary(content,'C:/Users/joshia2/Desktop/pyvinga/vcenter_perfdic.txt')
    elif content.about.name == 'VMware ESXi':
        print("Connected to VMware ESXi ")
        perf_dict = write_perf_dictionary(content,'C:/Users/joshia2/Desktop/pyvinga/host_perfdic.txt')
    return perf_dict


def write_perf_dictionary(content, file_perf_dic):
    """
    Checks whether the performance dictionary is older that 30 seconds.  If it is it creates a new one.
    This dictionary is read into the array and used in the functions that require perf_dict.
    NOTE: This is faster than doing a lookup live with a ServiceInstance Managed Object for every performance query.

    :param content: ServiceInstance Managed Object
    :param file_perf_dic: file name supplied by calling function (based on ESXi or vCenter connection)
    :return:
    """
    if not path.exists(file_perf_dic) or datetime.fromtimestamp(path.getmtime(file_perf_dic)) < (datetime.now() - timedelta(seconds=30)):
        # Get all the vCenter performance counters
        perf_dict = {}
        perfList = content.perfManager.perfCounter
        f = open(file_perf_dic, mode='w')
        for counter in perfList:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
            perf_dict[counter_full] = counter.key
            f.write(counter_full + ',' + str(perf_dict[counter_full]) + '\n')
        f.close()
    else:
        perf_dict = {}
        f = open(file_perf_dic, mode='r')
        for line in f:
            perf_dict[line.split(',')[0]] = int(line.split(',')[1])
        f.close()
    return perf_dict



START = clock()

def endit():
    """
    times how long it took for this script to run.
    :return:
    """
    end = clock()
    total = end - START
    print("Completion time: {0} seconds.".format(round(total,4)))


#vmInfovariables
vmName =[]
vmTemplate =[]
vmPath = []
vmDSlocation = []
vmGuest= []
vmInstanceUUID = []
vmBioUUID = []
vmIP = []
VMwareTools = []
poweredOff_VM = []
poweredOff_VMpath = []

cccc = 0

def print_vm_info(virtual_machine):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    summary = virtual_machine.summary

    if summary.runtime.powerState != "poweredOff" :

        global cccc
        cccc += 1
        '''
        print("Name       : ", summary.config.name) # name of the virtual machine
        print("Template   : ", summary.config.template) # true or false
        print("Path       : ", summary.config.vmPathName) # path where the vm belongs (data store information and its location)
        print("Guest      : ", summary.config.guestFullName)  # guest OS full name along with 32 or 64 bit info
        print("Instance UUID : ", summary.config.instanceUuid) 
        print("Bios UUID     : ", summary.config.uuid)
        '''
        vmName.append(summary.config.name)
        vmTemplate.append(summary.config.template)
        vmPath.append(summary.config.vmPathName)
        val = re.search(r'\[(.*)\]', summary.config.vmPathName)
        vmDSlocation.append(val.group(1))
        vmGuest.append(summary.config.guestFullName)
        vmInstanceUUID.append(summary.config.instanceUuid)
        vmBioUUID.append(summary.config.uuid)
        #vmState.append(summary.runtime.powerState)
        vmIP.append(summary.guest.ipAddress)
        VMwareTools.append(summary.guest.toolsStatus)

    else :
        poweredOff_VM.append(summary.config.name)
        poweredOff_VMpath.append(summary.config.vmPathName)



def get_properties(content, viewType, props, specType):
    """
    Obtains a list of specific properties for a particular Managed Object Reference data object.

    :param content: ServiceInstance Managed Object
    :param viewType: Type of Managed Object Reference that should populate the View
    :param props: A list of properties that should be retrieved for the entity
    :param specType: Type of Managed Object Reference that should be used for the Property Specification
    :return:
    """
    # Get the View based on the viewType
    objView = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
    # Build the Filter Specification
    tSpec = vim.PropertyCollector.TraversalSpec(name='tSpecName', path='view', skip=False, type=vim.view.ContainerView)
    pSpec = vim.PropertyCollector.PropertySpec(all=False, pathSet=props, type=specType)
    oSpec = vim.PropertyCollector.ObjectSpec(obj=objView, selectSet=[tSpec], skip=False)
    pfSpec = vim.PropertyCollector.FilterSpec(objectSet=[oSpec], propSet=[pSpec], reportMissingObjectsInResults=False)
    retOptions = vim.PropertyCollector.RetrieveOptions()
    # Retrieve the properties and look for a token coming back with each RetrievePropertiesEx call
    # If the token is present it indicates there are more items to be returned.
    totalProps = []
    retProps = content.propertyCollector.RetrievePropertiesEx(specSet=[pfSpec], options=retOptions)
    totalProps += retProps.objects
    while retProps.token:
        retProps = content.propertyCollector.ContinueRetrievePropertiesEx(token=retProps.token)
        totalProps += retProps.objects
    objView.Destroy()
    # Turn the output in totalProps into a usable dictionary of values
    gpOutput = []
    for eachProp in totalProps:
        propDic = {}
        for prop in eachProp.propSet:
            propDic[prop.name] = prop.val
        propDic['moref'] = eachProp.obj
        gpOutput.append(propDic)
    return gpOutput


vmGuest1 =[]
vmNumCPU = []
vmMemory =[]

def vm_core(vm_moref):
    """
    Obtains the core information for Virtual Machine (Notes, Guest, vCPU, Memory)

    :param vm_moref: Managed Object Reference for the Virtual Machine
    """
    vmconfig = vm_moref.summary.config
    if (float(vmconfig.memorySizeMB) / 1024).is_integer():
        vm_memory = str(vmconfig.memorySizeMB / 1024) + ' GB'
    else:
        vm_memory = str(vmconfig.memorySizeMB) + ' MB'
    #print("{}, {}, {} vCPU(s), {} Memory".format(vmconfig.annotation, vmconfig.guestFullName,vm_moref.summary.config.numCpu, vm_memory))

    #if vmconfig.annotation != "" :
    #    print("Annotation :", vmconfig.annotation)
    #print("Guest Name :", vmconfig.guestFullName)
    #print("numCpu :", vm_moref.summary.config.numCpu)
    #print("VM memory :", vm_memory)

    return vmconfig.guestFullName, vm_moref.summary.config.numCpu , vm_memory

    #exit(STATE_OK)

vmStatus = []
vmState = []

def vm_status(vm_moref):
    """
    Obtains the overall status from the Virtual Machine

    :param vm_moref: Managed Object Reference for the Virtual Machine
    """
    finalOutput = str(vm_moref.overallStatus)
    extraOutput = vm_moref.summary.runtime.powerState
    
    #print("Status :", finalOutput)
    #print("State :", extraOutput )
    return finalOutput, extraOutput


def stat_lookup(perf_dict, counter_name):
    """
    Performance the lookup of the supplied counter name against the dictionary and returns a counter Id

    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param counter_name: The counter name in the correct format for the dictionary
    """
    counter_key = perf_dict[counter_name]
    return counter_key


def build_query(content, vchtime, counterId, instance, vm_moref):
    """
    Creates the query for performance stats in the correct format

    :param content: ServiceInstance Managed Object
    :param counterId: The returned integer counter Id assigned to the named performance counter
    :param instance: instance of the performance counter to return (typically empty but it may need to contain a value
    for example - with VM virtual disk queries)
    :param vm_moref: Managed Object Reference for the Virtual Machine
    """
    perfManager = content.perfManager
    metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)
    startTime = vchtime - timedelta(seconds=60)
    endTime = vchtime - timedelta(seconds=40)
    query = vim.PerformanceManager.QuerySpec(intervalId=20, entity=vm_moref, metricId=[metricId], startTime=startTime,
                                             endTime=endTime)
    perfResults = perfManager.QueryPerf(querySpec=[query])
    if perfResults:
        statdata = float(sum(perfResults[0].value[0].value))
        return statdata
    else:
        print('ERROR: Performance results empty.  Check time drift on source and vCenter server')
        #exit(STATE_WARNING)

vmCPUready =[]

def vm_cpu_ready(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the CPU Ready value for the Virtual Machine

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether CPU Ready is warning
    :param critical: The value to use for the print_output function to calculate whether CPU Ready is critical

    How Much CPU Ready is “Normal”?
    While it is easy to look at CPU usage and understand that you are using 25% of 100% total capacity, it is a little more
    difficult to understand what is normal versus bad when looking at CPU Ready.
    For starters, CPU Ready is measured in the vSphere Client is measure in milliseconds (ms). This needs to be
    reconciled with VMware’s best practice guidelines that indicate it is best to keep your VMs below 5% CPU Ready per
    vCPU. When trying to make this reconciliation, it’s important to note that vSphere performance graphs are based
    upon 20-second data points. Using Figure 7 as an example, to convert this to a percentage value, you have to take
    what is reported (2173 ms) and divide by 20 seconds (20000 ms) to arrive at a CPU Ready value as a %. In the case
    of this graph, 2173/20000 = 0.10865, or 10.865%, which is twice the 5% guideline.

    """
    counter_key = stat_lookup(perf_dict, 'cpu.ready.summation')
    statdata = build_query(content, vchtime, counter_key, "", vm_moref)
    final_output = (statdata / 20000 * 100) #  divide by 20 seconds (20000 ms) to arrive at a CPU Ready value as a %.
    #print_output_float(final_output, 'CPU Ready', warning, critical, '%')
    #print("CPU Ready value for the Virtual Machine :",final_output,  "%")
    return final_output


vmCPUusage =[]

def vm_cpu_usage(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the CPU Usage value for the Virtual Machine

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether CPU Usage is warning
    :param critical: The value to use for the print_output function to calculate whether CPU Usage is critical
    """
    counter_key = stat_lookup(perf_dict, 'cpu.usage.average')
    statdata = build_query(content, vchtime, counter_key, "", vm_moref)
    final_output = (statdata / 100)
    #print_output_float(final_output, 'CPU Usage', warning, critical, '%')
    #print("VM CPU Usage Average :",final_output , "%")
    return final_output

vmMEMactive =[]

def vm_mem_active(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the Active Memory value for the Virtual Machine

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether Active Memory is warning
    :param critical: The value to use for the print_output function to calculate whether Active Memory is critical
    """
    counter_key = stat_lookup(perf_dict, 'mem.active.average')
    statdata = build_query(content, vchtime, counter_key, "", vm_moref)
    final_output = (statdata / 1024)
#    print_output_float(final_output, 'Memory Active', (warning * vm_moref.summary.config.memorySizeMB / 100),
#                      (critical * vm_moref.summary.config.memorySizeMB / 100), 'MB', '', 0, vm_moref.summary.config.memorySizeMB)
    #print("VM Active Memory :",final_output)
    return final_output

vmMEMshared =[]
def vm_mem_shared(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the Shared Memory value for the Virtual Machine

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether Shared Memory is warning
    :param critical: The value to use for the print_output function to calculate whether Shared Memory is critical
    """
    counter_key = stat_lookup(perf_dict, 'mem.shared.average')
    statdata = build_query(content, vchtime, counter_key, "", vm_moref)
    final_output = (statdata / 1024)
#    print_output_float(final_output, 'Memory Shared', (warning * vm_moref.summary.config.memorySizeMB / 100),
#                      (critical * vm_moref.summary.config.memorySizeMB / 100), 'MB', '', 0, vm_moref.summary.config.memorySizeMB)
    
    #print("VM Shared Memory :",final_output)
    return final_output

vmMEMballoon =[]

def vm_mem_balloon(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the Ballooned Memory value for the Virtual Machine

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether Ballooned Memory is warning
    :param critical: The value to use for the print_output function to calculate whether Ballooned Memory is critical
    """
    counter_key = stat_lookup(perf_dict, 'mem.vmmemctl.average')
    statdata = build_query(content, vchtime, counter_key, "", vm_moref)
    final_output = (statdata / 1024)
    #print_output_float(final_output, 'Memory Balloon', (warning * vm_moref.summary.config.memorySizeMB / 100),
    #                  (critical * vm_moref.summary.config.memorySizeMB / 100), 'MB', '', 0, vm_moref.summary.config.memorySizeMB)
    #print("VM Ballooned Memory :", final_output)
    return final_output

vmDS_readIO =[]
vmDS_writeIO =[]
vmDS_finalIO =[]

def vm_ds_io(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the Read, Write and Total Virtual Machine Datastore IOPS values.
    Uses the Total IOPS value to calculate status.

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether IOPS are warning
    :param critical: The value to use for the print_output function to calculate whether IOPS are critical
    """
    counter_key_read = stat_lookup(perf_dict, 'datastore.numberReadAveraged.average')
    counter_key_write = stat_lookup(perf_dict, 'datastore.numberWriteAveraged.average')
    statdata_read = build_query(content, vchtime, counter_key_read, "*", vm_moref)
    statdata_write = build_query(content, vchtime, counter_key_write, "*", vm_moref)
    statdata_total = statdata_read + statdata_write
    
    #print_output_float(statdata_total, 'Datastore IOPS', warning, critical, 'IOPS', '', 0, 5000)
    #print("VM Read IOPS :",statdata_read )
    #print("VM Write IOPS :",statdata_write )
    #print("VM Total IOPS :",statdata_total )

    return statdata_read,statdata_write,statdata_total

vmDS_readLatency =[]
vmDS_writeLatency =[]
vmDS_totalLatency =[]

def vm_ds_latency(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the Read, Write and Total Virtual Machine Datastore Latency values.
    Uses the Total IOPS value to calculate status.

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether Latency is warning
    :param critical: The value to use for the print_output function to calculate whether Latency is critical
    """
    counter_key_read = stat_lookup(perf_dict, 'datastore.totalReadLatency.average')
    counter_key_write = stat_lookup(perf_dict, 'datastore.totalWriteLatency.average')
    statdata_read = build_query(content, vchtime, counter_key_read, "*", vm_moref)
    statdata_write = build_query(content, vchtime, counter_key_write, "*", vm_moref)
    statdata_total = statdata_read + statdata_write
    #print_output_float(statdata_total, 'Datastore Latency', warning, critical, 'ms', '', 0, 100)
    
    #print("VM Read Datastore Latency :",statdata_read )
    #print("VM Write Datastore Latency :",statdata_write )
    #print("VM Total Datastore Latency :",statdata_total )

    return statdata_read,statdata_write,statdata_total

vm_NetUsageRx = [] #Recieved Mbps
vm_NetUsageTx = [] #Transmitted Mbps
vm_NetUsageTotal = []

def vm_net_usage(vm_moref, content, vchtime, perf_dict):
    """
    Obtains the Tx and Rx Virtual Machine Network Usage values.
    Uses the Total Network Usage value to calculate status.

    :param vm_moref: Managed Object Reference for the Virtual Machine
    :param content: ServiceInstance Managed Object
    :param perf_dict: The array containing the performance dictionary (with counters and IDs)
    :param warning: The value to use for the print_output function to calculate whether Network Usage is warning
    :param critical: The value to use for the print_output function to calculate whether Network Usage is critical
    """
    counter_key_read = stat_lookup(perf_dict, 'net.received.average')
    counter_key_write = stat_lookup(perf_dict, 'net.transmitted.average')
    statdata_rx = build_query(content, vchtime, counter_key_read, "", vm_moref)
    statdata_tx = build_query(content, vchtime, counter_key_write, "", vm_moref)
    statdata_total = (statdata_rx + statdata_tx) * 8 / 1024
    #print_output_float(statdata_total, 'Network Usage', warning, critical, 'Mbps', '', 0, 1000)
    #print("VM Rx Network Usage :",statdata_rx * 8 / 1024 )
    #print("VM Tx Network Usage :",statdata_tx * 8 / 1024 )
    #print("VM Total Network Usage :",statdata_total )

    return statdata_rx,statdata_tx,statdata_total


def collect_esxi_data(host,user,pwd,ssl, es):

    #now = datetime.datetime.now()
    es = es
    try:
        si= SmartConnect(host=host,user=user,pwd=pwd ,sslContext=ssl )
        print('Collecting Information')

        content = si.RetrieveContent()
        
        #disconnect the connection when program exists
        #atexit.register(Disconnect, si)
        #atexit.register(endit)
        
        # Get vCenter date and time for use as baseline when querying for counters
        vchtime = si.CurrentTime()

        perf_dict = create_perf_dictionary(content)

        container = content.rootFolder  # starting point to look into
        viewType = [vim.VirtualMachine]  # object types to look for
        recursive = True  # whether we should look into it recursively


        containerView  = content.viewManager.CreateContainerView(container, viewType, recursive)
        
        children = containerView.view
        c1 = 0
        for child in children:
            print_vm_info(child)
            c1 += 1

        c2 = 0
        if printVM :
            vmProps = get_properties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)
            for vm in vmProps:
                if vm['runtime.powerState'] == "poweredOn":

                    #print("VM Name : ",vm["name"])
                    
                    vm_moref = vm['moref']
                    guest , cpu, mem =vm_core(vm_moref) #core information
                    vmGuest1.append(guest)
                    vmNumCPU.append(cpu)
                    
                    s = re.findall(r"[-+]?\d*\.\d+|\d+", mem)

                    if "GB" in mem :
                         memKBytes = float(s[0])*131072
                    elif "MB" in mem :
                        memKBytes = float(s[0])*1024
                    elif "KB" in mem :
                        memKBytes = float(s[0])
                    else :
                        memKBytes = float(s[0]) * 0.00097656

                    vmMemory.append(memKBytes)


                    status, state  = vm_status(vm_moref)  #status information
                    vmStatus.append(status)
                    vmState.append(state)

                    CPUready = vm_cpu_ready(vm_moref, content, vchtime, perf_dict)
                    vmCPUready.append(CPUready)


                    CPUusage = vm_cpu_usage(vm_moref, content, vchtime, perf_dict)
                    vmCPUusage.append(CPUusage)

                    MEMactive = vm_mem_active(vm_moref, content, vchtime, perf_dict)
                    vmMEMactive.append(MEMactive)

                    MEMshared = vm_mem_shared(vm_moref, content, vchtime, perf_dict)
                    vmMEMshared.append(MEMshared)

                    MEMballoon = vm_mem_balloon(vm_moref, content, vchtime, perf_dict)
                    vmMEMballoon.append(MEMballoon)

                    DS_readIO , DS_writeIO, DS_finalIO = vm_ds_io(vm_moref, content, vchtime, perf_dict)

                    vmDS_readIO.append(DS_readIO)
                    vmDS_writeIO.append(DS_writeIO)
                    vmDS_finalIO.append(DS_finalIO)


                    DS_readLatency,DS_writeLatency, totalLatency = vm_ds_latency(vm_moref, content, vchtime, perf_dict)
                    vmDS_readLatency.append(DS_readLatency)
                    vmDS_writeLatency.append(DS_writeLatency)
                    vmDS_totalLatency.append(totalLatency)


                    NetUsageRx,NetUsageTx, NetUsageTotal = vm_net_usage(vm_moref, content, vchtime, perf_dict)
                    vm_NetUsageRx.append(NetUsageRx)
                    vm_NetUsageTx.append(NetUsageTx)
                    vm_NetUsageTotal.append(NetUsageTotal)
                    #break
                    c2 += 1


        for i in range(0,c2):
            VMLogger.info("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(collection_time,vmName[i], vmTemplate[i], vmPath[i] , vmDSlocation[i] , vmGuest[i] , vmInstanceUUID[i],vmBioUUID[i], vmIP[i] , VMwareTools[i] , vmGuest1[i] , vmNumCPU[i] , vmMemory[i] , vmStatus[i] , vmState[i] , vmCPUready[i] , vmCPUusage[i] , vmMEMactive[i] , vmMEMshared[i] , vmMEMballoon[i], vmDS_readIO[i] , vmDS_writeIO[i], vmDS_finalIO[i] , vmDS_readLatency[i], vmDS_writeLatency[i] , vmDS_totalLatency[i] , vm_NetUsageRx[i] , vm_NetUsageTx[i] , vm_NetUsageTotal[i]))

        with open('vmlog.log') as f:
            reader = csv.DictReader(f)
            helpers.bulk(es, reader, index='vm-index', doc_type='log')

        Disconnect(si)
        endit()

    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))




def main() :
    
    opts=validate_options()
        
    # # Disabling SSL certificate verification
    s=ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    s.verify_mode=ssl.CERT_NONE

    #es = Elasticsearch([{'host': '100.80.96.7', 'port': 9200 , 'user':"elastic", "password": "dna"}])
    es = Elasticsearch([{'host': 'localhost', 'port': 9200 }])
    
    while True:
        collect_esxi_data(opts.shost,opts.username,opts.password ,s , es)
        time.sleep(60)






if __name__ == '__main__':
    main()

