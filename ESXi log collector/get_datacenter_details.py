
from pyVmomi import vim
import ssl
import warnings
warnings.filterwarnings("ignore")
import argparse
from pyVim.connect import SmartConnect , Disconnect

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


def main () :
    
    opts=validate_options()
    #Disabling SSL certificate verification
    s=ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    s.verify_mode=ssl.CERT_NONE

    try : 

        service_instance = SmartConnect(host=opts.shost,user=opts.username,pwd=opts.password ,sslContext=s )

        # Retrieve content

        content = service_instance.RetrieveContent()
        objview = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
        # https://github.com/vmware/pyvmomi/blob/master/docs/vim/view/ContainerView.rst
        esxi_hosts = objview.view

        # Bunch of list comprehensions

        hostState = [esxi_host.runtime.powerState for esxi_host in esxi_hosts]

        print ("Host State : ")
        print("".join(str(v) for v in hostState))
        print("--------------------------------------------------------------")

        hostName = [esxi_host.name for esxi_host in esxi_hosts]
        print ("Host Name")
        print("".join(str(v) for v in hostName))
        print("--------------------------------------------------------------")


        hostStatus = [esxi_host.overallStatus for esxi_host in esxi_hosts]
        print ("Host Status")
        print("".join(str(v) for v in hostStatus))
        print("--------------------------------------------------------------")

        hostIp = [esxi_host.summary.managementServerIp for esxi_host in esxi_hosts]
        
        if hostIp is None :
            print ("Host IP")
            print("".join(str(v) for v in hostIp))

        # Nested list comprehension

        hostVms = [[(host.name) for host in eh.vm] for eh in esxi_hosts]
        print ("Host VMs")
        print("".join(str(v) for v in hostVms))
        print("--------------------------------------------------------------")

        hostVmsIps = [[(host.guest.ipAddress) for host in eh.vm] for eh in esxi_hosts]
        print ("Host VM IPs")
        print("".join(str(v) for v in hostVmsIps))
        print("--------------------------------------------------------------")

        hostVmsState = [[(host.runtime.powerState) for host in eh.vm]
                        for eh in esxi_hosts]

        print ("Host VM State")
        print(" ".join(str(v) for v in hostVmsState))
        print("--------------------------------------------------------------")


    except IOError as e:
        print("I/O error({0}): {1}".format(e.errno, e.strerror))


if __name__ == '__main__':
    main()
