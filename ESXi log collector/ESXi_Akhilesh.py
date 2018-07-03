# VMware vSphere Python SDK, pyvmomi
 
import ssl
import argparse
import atexit
import humanize
import pandas as pd
from termcolor import cprint
from pyvim.connect import SmartConnect , Disconnect


print_red = lambda x: cprint(x, 'red', attrs=['bold'])
print_green = lambda x: cprint(x, 'green' , attrs=['bold'])



MBFACTOR = float(1 << 20)

printVM ,printDatastore,printHost  = 1,1,1



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



def about_information(aboutInfo,hostid) :
    
    print("--------------------------------------------------")
    print("About Information")
    print("--------------------------------------------------")
    print("Product Name:",aboutInfo.fullName)
    print("Product Build:",aboutInfo.build)
    print("Product Unique Id:",aboutInfo.instanceUuid)
    print("Product Version:",aboutInfo.version)
    print("Product Name:",aboutInfo.licenseProductName)
    print("Product Base OS:",aboutInfo.osType)
    print("Product vendor:",aboutInfo.vendor)
        
    hardware=hostid.hardware
    cpuobj=hardware.cpuPkg[0]
        
    print ('The CPU vendor is %s and the model is %s'  %(cpuobj.vendor,cpuobj.description))
    systemInfo=hardware.systemInfo
    print ('The server hardware is %s %s' %(systemInfo.vendor,systemInfo.model))
    memoryInfo=hardware.memorySize
    print ('The memory size is %d GB' %((memoryInfo)/(1024*1024*1024)))




host_name= []
host_CPUusage = []
host_memoryCapacity =[]
host_memoryUsage = []
host_freeMemoryPercentage = []

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
        #print("--------------------------------------------------")
        #print("Host name: ", host.name)
        host_name.append(host.name)
        #print("Host CPU usage: ", cpuUsage)
        host_CPUusage.append(cpuUsage)
        #print("Host memory capacity: ", humanize.naturalsize(memoryCapacity, binary=True))
        host_memoryCapacity.append(humanize.naturalsize(memoryCapacity, binary=True))
        #print("Host memory usage: ", memoryUsage / 1024, "GiB")
        host_memoryUsage.append(round(memoryUsage/1024.0 , 2))
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
        print("--------------------------------------------------")
        print("Compute resource name: ", computeResource.name)
        print("--------------------------------------------------")
        for host in hostList:
            printHostInformation(host)
    except Exception as error:
        print("Unable to access information for compute resource: ", end=' ')
        computeResource.name
        print(error)
        pass


ds_name= []
ds_capacity = []
ds_provisionedSpace =[]
ds_freeSpace = []
ds_freeSpacePercentage = []

def printDatastoreInformation(datastore):
    
    try:
        summary = datastore.summary
        capacity = summary.capacity
        freeSpace = summary.freeSpace
        uncommittedSpace = summary.uncommitted
        freeSpacePercentage = (float(freeSpace) / capacity) * 100
        
        

        #print("Datastore name: ", summary.name)
        ds_name.append(summary.name)
        
        #print("Capacity: ", humanize.naturalsize(capacity, binary=True))
        ds_capacity.append( humanize.naturalsize(capacity, binary=True))
        
        if uncommittedSpace is not None:
            provisionedSpace = (capacity - freeSpace) + uncommittedSpace
            #print("Provisioned space: ", humanize.naturalsize(provisionedSpace, binary=True))
            ds_provisionedSpace.append(humanize.naturalsize(provisionedSpace, binary=True))
        
        #print("Free space: ", humanize.naturalsize(freeSpace, binary=True))
        ds_freeSpace.append(humanize.naturalsize(freeSpace, binary=True))
        
        #print("Free space percentage: " + str(freeSpacePercentage) + "%")
        ds_freeSpacePercentage.append(round(freeSpacePercentage,2))
        

    except Exception as error:
        #print("Unable to access summary for datastore: ", datastore.name)
        #print(error)
        pass


notAccessibleVM =[]
error_notAccessibleVM =[]

vmSummaryName =[]
vmSummaryMoRef = []
vmSummaryPowerState = []



def printVmInformation(virtual_machine, depth=1):
    
    maxdepth = 10
    if hasattr(virtual_machine, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = virtual_machine.childEntity
        for c in vmList:
            printVmInformation(c, depth + 1)
        return

    try:
        summary = virtual_machine.summary
        #print("Name : ", summary.name)
        vmSummaryName.append(summary.name)
        #print("MoRef : ", summary.vm)
        vmSummaryMoRef.append(summary.vm)
        #print("State : ", summary.runtime.powerState)
        vmSummaryPowerState.append(summary.runtime.powerState)

    except Exception as error:
        #print("Unable to access summary for VM: ", virtual_machine.name)
        notAccessibleVM.append(virtual_machine.name)
        #print(error)
        error_notAccessibleVM.append(error)
        pass

def main() :
    
    opts=validate_options()
    
    hostDataFrame = pd.DataFrame()
    dsDataFrame = pd.DataFrame()
    vmSummaryDataFrame = pd.DataFrame()
    vmSummaryErrorDataFrame = pd.DataFrame()

    
    # check SSL certificates
    s=ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    s.verify_mode=ssl.CERT_NONE
    

    try:
        si= SmartConnect(host=opts.shost,user=opts.username,pwd=opts.password ,sslContext=s )
        print_green('Valid certificate')

        content = si.RetrieveContent()
        
        #print about information : function call
        about_information(si.content.about ,si.content.rootFolder.childEntity[0].hostFolder.childEntity[0].host[0] )

        #disconnect the connection when program exists
        atexit.register(Disconnect, si)

        ds_count = 0
        
        for datacenter in content.rootFolder.childEntity:
            print("Data Center Name : ", datacenter.name )
            #print(type(datacenter))
            ds_count += 1
            if printVM:
                if hasattr(datacenter.vmFolder, 'childEntity'):
                    vmFolder = datacenter.vmFolder
                    vmList = vmFolder.childEntity
                    for vm in vmList:
                        printVmInformation(vm)
        
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

        
        print("Total Data Center(s) : ", ds_count )   

        dsDataFrame = pd.DataFrame(list(zip(ds_name, ds_capacity, ds_provisionedSpace,ds_freeSpace,ds_freeSpacePercentage)),
              columns=["ds_name", "ds_capacity", "ds_provisionedSpace","ds_freeSpace","ds_freeSpacePercentage"])

        dsDataFrame.to_csv("C:/Users/joshia2/Desktop/esxi_akhilesh/output_files/DataStore_Data.csv",index=False)


        hostDataFrame = pd.DataFrame(list(zip(host_name, host_CPUusage, host_memoryCapacity,host_memoryUsage,host_freeMemoryPercentage)),
              columns=["host_name", "host_CPUusage", "host_memoryCapacity","host_memoryUsage","host_freeMemoryPercentage"])

        #print(hostDataFrame)
        hostDataFrame.to_csv("C:/Users/joshia2/Desktop/esxi_akhilesh/output_files/hostData.csv",index=False)

        vmSummaryDataFrame = pd.DataFrame(list(zip(vmSummaryName, vmSummaryMoRef, vmSummaryPowerState)), columns=["vmSummaryName", "vmSummaryMoRef", "vmSummaryPowerState"])

        vmSummaryDataFrame.to_csv("C:/Users/joshia2/Desktop/esxi_akhilesh/output_files/vmSummary.csv",index=False)


        vmSummaryErrorDataFrame = pd.DataFrame(list(zip(notAccessibleVM, error_notAccessibleVM)), columns=["notAccessibleVM", "error_notAccessibleVM"])

        vmSummaryErrorDataFrame.to_csv("C:/Users/joshia2/Desktop/esxi_akhilesh/output_files/vmSummaryError.csv",index=False)

        
    except:
        print_red('Unable to connect to host : invalid credentials or invalid/untrusted certificate')
        print_red("Please try connecting again")





if __name__ == '__main__':
    main()

