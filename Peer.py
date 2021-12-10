#!/usr/bin/python
import sys
import argparse
import json
import socket
import time
import threading
from multiprocessing import Queue
from concurrent import futures
import sensor
sys.path.append('..')

#To obtain command line arguments.
def get_arguments():
    p = argparse.ArgumentParser(
        description='Arguments for connecting to index server')
    p.add_argument('-s', '--server',type=int,required=True,action='store',help='Index Server Port Number')
    p.add_argument('-p','--peer_port', type=str,required=True,action='store',help='Peer Port Number')
    p.add_argument('-n','--network', type=str,required=False,action='store',help='IP address of network to connect to')
    args = p.parse_args()
    return args

class PeerOperations(threading.Thread):

    #Initializing a thread for each peer object
    def __init__(self, idthread, name, peer):
        threading.Thread.__init__(self)
        self.threadID = idthread
        self.name = name
        self.p_s_listen_queue = Queue()
        self.peer = peer
    
    #Function for encrypting or decrypting string data
    def secure(self, str_data):
    # use XOR key to encode every character of a string
       Key = 'N';  
       for i in range(len(str_data)):
            try:
                str_data = str_data[:i] + chr(ord(str_data[i]) ^ ord(Key)) +str_data[i + 1:]
            except:
                continue
       return str_data
    
    #Function for encrypting dictionary commands sent
    def secure_dict(self,d):
        secured_dict={}
        for key,value in d.items():
            if(isinstance(value,dict)):
                secured_dict[self.secure(key)]=self.secure_dict(value)
            elif(isinstance(value,(int,float))):
                secured_dict[self.secure(key)]=self.secure(str(value))
            else:
                secured_dict[self.secure(key)]=self.secure(value)
        return secured_dict
    
    #Function to listen for incoming connections to the peer
    def p_s_listen(self):
        
        p_s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        p_s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        p_s_host = socket.gethostbyname(socket.gethostname())
        p_s_port = self.peer.hosting_port
        p_s_socket.bind((p_s_host, p_s_port))
        p_s_socket.listen(10)
        while True:
            connection, address = p_s_socket.accept()
            #The incoming connection is put in a queue to process the connections one by one
            self.p_s_listen_queue.put((connection,address))

    #Function to process requests from incoming connections to peer
    def p_s_host(self):
       
        try:
            while True:
                while not self.p_s_listen_queue.empty():
                    with futures.ThreadPoolExecutor(max_workers=8) as executor:
                        #Process the connections present in listener queue
                        connection, address = self.p_s_listen_queue.get()
                        secured_data_received = json.loads(connection.recv(1024).decode('utf-8'))
                        #Decrypt the incomming request message
                        data_rcv=self.secure_dict(secured_data_received)

                        #Display the message recieved
                        if data_rcv['command']== 'message' or data_rcv['command']=='connect':
                            print("Message Recieved from: "+data_rcv['peer_id'])
                            print(data_rcv['message'])
                            connection.send(json.dumps(True).encode('utf-8'))
                        else:
                            connection.send(json.dumps(False).encode('utf-8'))

        except Exception as e:
            print ("Server Peer Connection Processing Error, %s" % e)

    #Function that creates a thread for listening to connections and a thread for processing the connections
    def p_s(self):
        
        try:
            l_thread = threading.Thread(target=self.p_s_listen)
            l_thread.setDaemon(True)

            op_thread = threading.Thread(target=self.p_s_host)
            op_thread.setDaemon(True)

            l_thread.start()
            op_thread.start()

            list_threads = []
            list_threads.append(l_thread)
            list_threads.append(op_thread)

            for th in list_threads:
                th.join()
        except Exception as e:
            print ("Peer Thread Connection Error, %s" % e)
            sys.exit(1)
    
    #FUnction to run the thread creation function if PeerToServer name is given to PeerOperations object
    def run(self):
        if self.name == "PeerToServer":
            self.p_s()

class Peer():

    #Initialize peer object
    def __init__(self, server_port, peer_port,network):
        self.peer_hostname = socket.gethostbyname(socket.gethostname())  #peer host name
        self.peer_port=peer_port #peer port
        self.server_port = server_port #port of index server
        self.data = {} #contains sensor data generated every 15 seconds
        self.network=network #address of existing network to connect to
        self.leader=False #tracks if currect peer object is leader or not
    
    #function that gets sensor data from sensor.py module
    def generate_sensor_data(self):
        self.data['light']= sensor.Light()
        self.data['proximity']=sensor.ProximitySensor()
        self.data['location']=sensor.LocationSensor()
        self.data['speed']=sensor.SpeedSensor()
        self.data['obstacle']=sensor.Obstacle()
        self.data['fuel']=sensor.FuelSensor()
        self.data['lane_change']=sensor.LaneChangeSensor()
        return self.data

    #function to broadcast a message to all peers connected to a network
    def broadcast_peers(self, message):
        try:
            nodes=self.list_nodes()
            for node in nodes:
                if(node==self.peer_id):
                    #to not broadcast message to oneself
                    continue
                peer_request_addr, peer_request_port = node.split(':')
                peer_request_socket = \
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_request_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                peer_request_socket.connect(
                    (self.peer_hostname, int(peer_request_port)))

                cmd_issue = {
                    'command' : 'message',
                    'message': message,
                    'peer_id':self.peer_id
                }
                #encrypt the message to be sent to all peers
                secured_cmd_issue=self.secure_dict(cmd_issue)
                peer_request_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))

                #Check if the message was recieved
                rcv_data = peer_request_socket.recv(1024000)
                if(rcv_data):
                    print('Message: ' +cmd_issue['message']+' Broadcasted successfully.')
                peer_request_socket.close()
        except Exception as e:
            print ("Broadcast Peer Error, %s" % e)
        

    #to connect leaders of two networks and update the same on the respective index servers
    def connect_network_leader(self,addr):
        try:
            hostname,port=addr.split(':')
            message=''
            #get address of leader present in network with server with addr
            leader_addr=self.get_leader(hostname,port)
            peer_request_addr, peer_request_port = leader_addr.split(':')
            peer_request_socket = \
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_request_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            #connect leader of joining network with leader of existing network
            peer_request_socket.connect(
                    (peer_request_addr, int(peer_request_port)))
            message='Connection established between Leader '+leader_addr +' and Leader '+str(self.peer_id)
            cmd_issue = {
                    'command' : 'connect',
                    'message': message,
                    'peer_id':self.peer_id }
            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_request_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = peer_request_socket.recv(1024000)
            if(rcv_data):
                print('Leaders connected successfully.')
            peer_request_socket.close()

            #update incoming network's server 
            peer_request_socket = \
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_request_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_request_socket.connect((hostname,int(port)))
            cmd_issue = {
                    'command' : 'connect_update',
                    'peer_id':self.peer_id }
            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_request_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = peer_request_socket.recv(1024000)
            if(rcv_data):
                print('Index Server: '+addr+ ' updated with network leaders connection')
            peer_request_socket.close()
            
            #update the current network's server
            peer_request_socket = \
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_request_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_request_socket.connect((self.peer_hostname,int(self.server_port)))
            cmd_issue = {
                    'command' : 'connect_update',
                    'peer_id':leader_addr }

            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_request_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = peer_request_socket.recv(1024000)
            if(rcv_data):
                print('Index Server:'+self.peer_hostname+':'+str(self.server_port)+' updated with network leaders connection')
            peer_request_socket.close()
        except Exception as e:
            print ("Leader Connection Error, %s" % e)

    #Function that collects sensor data every 15 seconds 
    def generate_data_continuously(self):
        try:
            #Elect a leader every 15 seconds
            self.elect_leader()

            #if a network arg was specified, connect to the leader of that network
            if(self.network):
                    if(self.leader==True):
                        self.connect_network_leader(self.network)
            
            message=''
            while True:

                time.sleep(15) 
                data=self.generate_sensor_data()
                print(self.data)
                #update the index server with the newly generated sensor data
                self.update_server(data)
                
                #if enough fuel isnt available, switch off car
                if(not sensor.isEnoughFuelAvailable(self.data['fuel'])):
                
                    message='Fuel low: Shutting off Device '+str(self.peer_id)
                    print(message)
                    #send a message to all peers that car is switched off
                    self.broadcast_peers(message)
                    #deregister the car from the index server
                    self.deregister(message)
                    #start leader election again
                    self.elect_leader()
                    break
                
                #alert the other peers if an obstacle is found
                if(sensor.isObstacleFound(self.data['obstacle'])):
                    message='Obstacle found at Latitude:'+str(self.data['location']['Latitude'])+', Longitude:'+str(self.data['location']['Longitude'])
                    print(message)
                    self.broadcast_peers(message)
                    continue
        except Exception as e:
            print ("Continuous Data Generation Error, %s" % e)
    #function to update the index server with newly generated sensor data          
    def update_server(self,data):
        try:
            cmd_issue = {'command' : 'update','peer_id' : self.peer_id,'data' : data}
            peer_to_server_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_to_server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_to_server_socket.connect((self.peer_hostname, self.server_port))
            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_to_server_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            
            peer_to_server_socket.close()
            if rcv_data:
                print ("Data Update of Peer: %s on server successful" \
                    % (self.peer_id))
            else:
                print ("Data Update of Peer: %s on server unsuccessful" \
                    % (self.peer_id))
        except Exception as e:
            print ("Update Index Server Error, %s" % e)


    #FUnction to register peer with index server
    def register(self):
        try:
            self.data=self.generate_sensor_data()
            print ("Peer is registering with Index Server...")

            p_s_socket = \
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            p_s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            p_s_socket.connect((self.peer_hostname, self.server_port))

            command = {'command' : 'register','peer_port' : self.peer_port,'data' : self.data,}
            #encrypt the message to be sent
            secured_cmd_issue=self.secure_dict(command)
            p_s_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            data_rcv = json.loads(p_s_socket.recv(1024).decode('utf-8'))
            p_s_socket.close()
            p_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            p_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            p_host = socket.gethostbyname(socket.gethostname())
            p_socket.bind((p_host, int(self.peer_port)))
            if data_rcv[1]:
                self.hosting_port = int(self.peer_port)
                self.peer_id = data_rcv[0] + ":" + self.peer_port
                print ("Peer ID: %s:%s registered" % (data_rcv[0], self.peer_port))
            else:
                print ("Peer ID: %s:%s did not register" % (data_rcv[0], self.peer_port))
        except Exception as e:
            print ("Peer register error, %s" % e)
            sys.exit(1)

    #Function to elect leader
    def elect_leader(self):
        try:
            ip_nodes=self.list_nodes()
            #elect leader only when there are peers connected to the network
            if(ip_nodes):
                nodes=[int(x.split(':')[1]) for x in ip_nodes]
                if(int(self.peer_port)==max(nodes) and self.leader==False):
                    self.leader=True
                    self.update_leader_in_server()
                    self.broadcast_peers('I am the leader!!')
                else:
                    self.leader==False
        except Exception as e:
            print ("Leader Election Error, %s" % e)
            
    #function to update elected leader in the server
    def update_leader_in_server(self):
        try:
            cmd_issue = {'command' : 'update_leader','peer_id' : self.peer_id}
            peer_to_server_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_to_server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_to_server_socket.connect((self.peer_hostname, self.server_port))
            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_to_server_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            #print(rcv_data)
            peer_to_server_socket.close()
            if rcv_data:
                print ("Leader Update: %s on server successful" \
                    % (self.peer_id))
            else:
                print ("Leader Update: %s on server unsuccessful" \
                    % (self.peer_id))
        except Exception as e:
            print ("Updating Leader in Index Server Error, %s" % e)



    #function to list all nodes present in the network
    def list_nodes(self):
        try:
            peer_to_server_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_to_server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_to_server_socket.connect(
                (self.peer_hostname, self.server_port))

            cmd_issue = {
                'command' : 'list'
            }
            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_to_server_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            peer_to_server_socket.close()
            return rcv_data
        except Exception as e:
            print ("Listing Nodes from Index Server Error, %s" % e)
    
    #function to get the leader of the network
    def get_leader(self,hostname,server_port):
        try:
        
            peer_to_server_socket = \
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_to_server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_to_server_socket.connect(
            (hostname, int(server_port)))

            cmd_issue = {
            'command' : 'leader'
            }
            secured_cmd_issue=self.secure_dict(cmd_issue)
            peer_to_server_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            peer_to_server_socket.close()
            #print ("leader:",rcv_data)
        
            return rcv_data
        except Exception as e:
            print ("Listing leader from Index Server Error, %s" % e)

    #function for encrypting and decrypting string of data
    def secure(self, data):
        try:
            xorKey = 'N';  
            for i in range(len(data)):
                try:
                    data = data[:i] + chr(ord(data[i]) ^ ord(xorKey)) +data[i + 1:]
                except:
                    continue
            return data
        except Exception as e:
            print ("Encrypt/Decrypt error, %s" % e)

    
    #function for encrypting and decrypting dict commands
    def secure_dict(self,d):
        try:
            secured_dict={}
            for key,value in d.items():
                if(isinstance(value,dict)):
                    secured_dict[self.secure(key)]=self.secure_dict(value)
                elif(isinstance(value,(int,float))):
                    secured_dict[self.secure(key)]=self.secure(str(value))
                else:
                    secured_dict[self.secure(key)]=self.secure(value)
                
            return secured_dict
        except Exception as e:
            print ("dict Encrypt/Decrypt error, %s" % e)

    #function to deregister peer from the index server
    def deregister(self,message=''):
        try:
            print ("Peer deregistering with Index Server..")
            p_s_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            p_s_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            p_s_socket.connect(
                (self.peer_hostname, self.server_port))

            cmd_issue = {
                'command' : 'deregister',
                'message':message,
                'peer_id' : self.peer_id,
                'hosting_port' : self.hosting_port
            }
            secured_cmd_issue=self.secure_dict(cmd_issue)
            p_s_socket.sendall(json.dumps(secured_cmd_issue).encode('utf-8'))
            data_rcv = json.loads(p_s_socket.recv(1024).decode('utf-8'))
            p_s_socket.close()
            if data_rcv:
                print ("Peer: %s deregistered with index server" \
                      % (self.peer_id))
            else:
                print ("Peer: %s did not deregister with index server" \
                      % (self.peer_id))
        except Exception as e:
            print ("Peer Deregister Error, %s" % e)

if __name__ == '__main__':
    try:
        args = get_arguments()
        print ("Peer is Starting...")
        p=Peer(args.server,args.peer_port,args.network) 
        p.register()
        server_thread = PeerOperations(1, "PeerToServer", p)
        server_thread.setDaemon(True)
        server_thread.start()
        p.generate_data_continuously()
        
    except Exception as e:
        print(e)
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        p.deregister()
        p.elect_leader()
        print ("Peer is switching off..")
        time.sleep(1)
        sys.exit(1)
