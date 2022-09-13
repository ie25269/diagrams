import os, sys, getopt, time, csv, pprint
from netmiko import ( ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)
from pyvis.network import Network
from datetime import date
#
# DESCRIPTION:
# This script collects lldp neighbor information to create diagram.html file using networkx.
#
# USAGE:
# python3 <scriptname> -i <hostsFile>
#
#   <scriptname>   : name of python script
#   <hostsFile>    : text file list of ip addresses, one per line
#
# LOGIN CREDENTIALS:
# Set as env variables or can be set manually below.
#
# VIS Reference:
# https://visjs.github.io/vis-network/docs/network/

sshUser = "JohnDoe"
sshPass = "JohnDoePassword"
sshSecret = "JohnDoeEnablePassword"

def printhelp():
    print(f'\nDESCRIPTION:\n This script collects lldp neighbor information to create diagram.html file using networkx.')
    print(f'\nUSAGE:\n python3 <scriptname> -i <hostsFile>')
    print(f'  <scriptname>   : name of python script')
    print(f'  <hostsFile>    : text file list of ip addresses, one per line')
    print(f'\nLOGIN CREDENTIALS:\n Set as env variables or can be set manually on line 21\n') 

startTime = time.time()
env1 = "TACACS_USER"
env2 = "TACACS_PASS"
env3 = "TACACS_SECRET"
if env1 in os.environ:
    sshUser = os.environ.get(env1)
if env2 in os.environ:
    sshPass = os.environ.get(env2)
if env3 in os.environ:
    sshSecret = os.environ.get(env3)

# Parse arguments
argList = sys.argv[1:]
if len(argList) < 1:
    print(f'\n    ***ERROR: must supply at least one argument*** \n')
    printhelp()
    sys.exit()
options = "hv:i:"
try:
    args, value = getopt.getopt(argList, options)
    for arg, val in args:
        if arg in ("-h"):
            printhelp()
            sys.exit()
        elif arg in ("-i"):
            inFile = val
except getopt.error as err:
    print("\nError: " , str(err) , "\n")
    sys.exit()


def getNeighHostname(device, intf):
    neighName = ""
    try:
        with ConnectHandler(**device) as ssh:
            command = "show lldp neighbor " + intf + " detail | inc ^System Name"
            output = ssh.send_command(command)
            lines = output.splitlines()
            fline = lines[0].split()
            flineLen = len(fline) - 1
            neighName = fline[flineLen]
            dotChar = neighName.find(".")
            neighName = neighName[0:dotChar]
        return neighName
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        print(error)

def send_show_command(device, commands):
    result = {}
    try:
        with ConnectHandler(**device) as ssh:
            ssh.enable()
            for command in commands:
                output = ssh.send_command(command)
                result[command] = output
        return result
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        print(error)

def input2List(inputFile):
    # Convert csv input file to list
    inList = list()
    with open(inputFile) as data:
        csv_list = csv.reader(data)
        for row in csv_list:
            ipAddr = row[0]
            inList.append(ipAddr)
    return inList


# -----------------------------------------
netDate = date.today()
netDate = netDate.strftime("%m/%d/%Y")
netTitle = "LLDP Neighbor Network Diagram - " + str(netDate)
net = Network(height="95%", width="95%", notebook=True)
nodeDist = 600
springLength = 800
netSeed = '8'
# -----------------------------------------

ipList = input2List(inFile)
myResults = []
for ip in ipList:
    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": sshUser,
        "password": sshPass,
        "secret": sshSecret,
    }
    try:
        cmd1 = "show run | include hostname"
        cmd2 = "show lldp neighbors | begin ^Device"
        dev = {}
        dev['host'] = ip
        dev['interface'] = []
        neighCount = 0

        with ConnectHandler(**device) as ssh:
            ssh.enable()
            # Get hostname
            output1 = ssh.send_command(cmd1)
            result1 = output1.splitlines()
            fline = result1[0].split()
            localName= fline[1]
            nodeInfo= "IP: " + ip
            # UNCOMMENT below line to use custom images for nodes.  SVG recommended
            #net.add_node(localName, title=nodeInfo, shape='image', image='icons/router1.svg')
            net.add_node(localName, title=nodeInfo)

            # Get lldp neighbors 
            output2 = ssh.send_command(cmd2)
            result2 = output2.splitlines()
            for line in result2:
                lineLen = len(line)
                exp1 = line.startswith(('Device ID'))
                exp2 = line.startswith(('Total'))
                if exp1:
                    neighChar = line.find("Local")
                elif exp2:
                    something = 'null'
                elif lineLen < 1:
                    something = 'null'
                else:
                    item = line.split()
                    fword = item[0]
                    fwordLen = len(fword)
                    nameStop = fword.find(".")
                    neName = fword[0:neighChar]
                    neNameLen = len(neName)
                    itemLen = len(item)
                    
                    if fwordLen < neighChar:
                        neighName = item[0]
                        dotChar = neighName.find(".")
                        neighName = neighName[0:dotChar]
                        localIntf = item[1]
                        neighIntf = item[itemLen-1]
                    else:
                        localIntf = fword[neighChar:fwordLen]
                        neighIntf = item[itemLen-1]
                        neighName = fword[0:neighChar]
                        dotChar = neighName.find(".")
                        neighName = neighName[0:dotChar]
                        neighNameLen = len(neighName)
                        if len(neighName) < neighChar:
                            neighName = neighName
                        else:
                            neighName = getNeighHostname(device,localIntf)


                    intfDot = neighIntf.rfind(".")
                    if intfDot != -1:
                        something = 'null'
                    else:
                        # UNCOMMENT below line to use custom images for nodes.  SVG recommended.
                        #net.add_node(neighName, shape='image', image='icons/router1.svg')
                        net.add_node(neighName)
                        neighCount += 1

                        lName = localName.lower()
                        nName = neighName.lower() 
                        lIntf = localIntf.lower()
                        nIntf = neighIntf.lower()
                        edgeColor="#004dbd"
                        connLabel = lName + ":" + localIntf + "_to_" + neighIntf + ":" + nName

                        if lIntf.startswith("te") and nIntf.startswith("te"): 
                            edgeColor = "#00bd56"
                        elif lIntf.startswith("twe") and nIntf.startswith("te"):
                            edgeColor = "#00bd56"
                        elif lIntf.startswith("twe") and nIntf.startswith("twe"):
                            edgeColor = "#00ce5e"
                        elif lIntf.startswith("hu") and nIntf.startswith("hu"):
                            edgeColor = "#bd0067"
                        elif lIntf.startswith("gi") and nIntf.startswith("gi"):
                            edgeColor = "#0009bd"
                        elif lIntf.startswith("fa") or nIntf.startswith("fa"):
                            edgeColor = "#bdb400"
                        else:
                            edgeColor = "#0009bd"

                        # UNCOMMENT below line to apply weight and line color
                        #net.add_edge(localName,neighName,value="1",color=edgeColor,title=connLabel)
                        # UNCOMMENT below line to apply line color
                        #net.add_edge(localName,neighName,color=edgeColor,title=connLabel)
                        net.add_edge(localName,neighName,title=connLabel)

                        #Uncomment below line to display lldp neighbor output as rx'ed, useful for debugging.
                        #print(f'{localName:<15} {localIntf:<30} {neighName:<25} {neighIntf:<10}')
            print(f' {localName:<24}: found {neighCount:>3} lldp interface neighbors.')


    except NetmikoTimeoutException as error:
        print(f'Error: {error}')
    except NetmikoAuthenticationException as error:
        print(f'AuthenticationError: {error}')
        sys.exit()
    except KeyboardInterrupt as error:
        print(f'Error: Script ended by User')
        sys.exit()

# -----------------------------------------
net.toggle_physics(False)
net.repulsion(node_distance=nodeDist, spring_length=springLength)
net.set_options('{ "layout":{"randomSeed":' + netSeed + '},"interaction":{"dragNodes":true}}')
net.show("diagram.html")
# -----------------------------------------
titleString = "<body><center>" + netTitle + "</center>"

# READ IN diagram html file
with open('diagram.html', 'r') as file :
  filedata = file.read()

# ADD TITLE
filedata = filedata.replace("<body>",titleString)

# UNCOMMENT TWO LINES BELOW IF ...
# You don't want your diagram making web calls everytime you load it in your browser.
# You'll need to save the css and js files and reference them locally.
#filedata = filedata.replace("https://cdn.jsdelivr.net/npm/vis-network@latest/styles/vis-network.css", "files/vis-network.css")
#filedata = filedata.replace("https://cdn.jsdelivr.net/npm/vis-network@latest/dist/vis-network.min.js", "files/vis-network.min.js")

# WRITE OUT diagram html file with replaced text
with open('diagram.html', 'w') as file:
  file.write(filedata)
# -----------------------------------------
endTime = time.time()
runTime = round((endTime - startTime),2)
print(f'-----------------------')
print(f'RunTime: {runTime:<3} sec\n')



