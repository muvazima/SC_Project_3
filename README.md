# SC_Project_3
Implementation of P2P networking protocol in vehicular mobility context

## To run

### For network 1 on Pi 1
Open a terminal for Index server: 

$ python3 index_server.py -p 33001

Open a terminal for peer(s): 

$ python3 peer.py -s 33001 -p 33002

### For network 2 on Pi 2
Open a terminal for Index server:

$ python3 index_server.py -p 33003

Open a terminal for peer(s): 

$ python3 peer.py -s 33003 -p 33004 -n '10.35.70.7:33001'

## Shell Script

sh shell.sh