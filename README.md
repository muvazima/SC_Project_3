# SC_Project_3
Implementation of P2P networking protocol in vehicular mobility context

## To run

### For network 1 on Pi 1
Open a terminal for Index server: 

$ python3 index_server.py -p 33001

-p here specifies the index server port

Open a terminal for peer(s): 

$ python3 peer.py -s 33001 -p 33002

-s here specifies index server port
-p here specifies peer port

### For network 2 on Pi 2
Open a terminal for Index server:

$ python3 index_server.py -p 33003

Open a terminal for peer(s): 

$ python3 peer.py -s 33003 -p 33004 -n '10.35.70.7:33001'

-n argument here specifies the index server address of the network we wish to connect to. 

## Shell Script
For network 1 on pi 1
$ sh shell_n1.sh

For network 2 on pi 2
$ sh shell_n2.sh

## Contributions
System architecture and message broadcasting - Muvazima Mansoor <br />
Leader Election - Archit Jhingan <br />
Sensors - Yigao Xie <br />
Actuators - Vishnu Priya <br />