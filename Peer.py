#!/usr/bin/python
import socket
import time
import threading
import json
import os
import argparse
import sys
import random
sys.path.append('..')
from multiprocessing import Queue
from concurrent import futures
import sensor
#socket.gethostbyname('localhost')
#SHARED_DIR = "./Active-Files"


def get_args():
    """
    Get command line args from the user.
    """
    parser = argparse.ArgumentParser(
        description='Standard Arguments for talking to Central Index Server')
    parser.add_argument('-s', '--server',
                        type=int,
                        required=True,
                        action='store',
                        help='Index Server Port Number')
    parser.add_argument('-n','--network', type=str,required=False,action='store',help='IP address of network to connect to')
    args = parser.parse_args()
    return args

class PeerOperations(threading.Thread):
    def __init__(self, threadid, name, p):
        """
        Constructor used to initialize class object.

        @param threadid:    Thread ID.
        @param name:        Name of the thread.
        @param p:           Class Peer Object.
        """
        threading.Thread.__init__(self)
        self.threadID = threadid
        self.name = name
        self.peer = p
        self.peer_server_listener_queue = Queue()
        
    def secure(self, data):

    # Define XOR key 
       xorKey = 'P';  
  
    # perform XOR operation of key with every character in string 
       
       for i in range(len(data)):
            try:
                data = data[:i] + chr(ord(data[i]) ^ ord(xorKey)) +data[i + 1:]
            except:
                continue
           
    #print "Encrypted message = ",data
       return data

    def peer_server_listener(self):
        """
        Peer Server Listener Method is used Peer Server to listen on
        port: assigned by Index Server for incoming connections.
        """
        try:
            peer_server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            peer_server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_server_host = socket.gethostbyname('localhost')
            
            peer_server_port = self.peer.hosting_port
            peer_server_socket.bind(
                (peer_server_host, peer_server_port))
            peer_server_socket.listen(10)
            while True:
                conn, addr = peer_server_socket.accept()
                #print "Got connection from %s on port %s" \
                #          % (addr[0], addr[1])
                self.peer_server_listener_queue.put((conn,addr))
        except Exception as e:
            print ("Peer Server Listener on port Failed: %s" % e)
            sys.exit(1)

    # def peer_server_upload(self, conn, data_received):
    #     """
    #     This method is used to enable file transfer between peers.

    #     @param conn:              Connection object.
    #     @param data_received:     Received data containing file name.
    #     """
    #     try:
    #         #f = open(SHARED_DIR+'/'+data_received['file_name'], 'rb')
    #         print ("Hosting File: %s for download" % data_received)
    #         #data = f.read()
    #         data =self.secure(data_received)
    #         #f.close()
    #         #conn.sendall(data.encode('utf-8'))
    #         conn.sendall(data)
    #         conn.close()
    #     except Exception as e:
    #         print ("File Upload Error, %s" % e)

    def peer_server_host(self):
        """
        This method is used process client download request and file
        """
        try:
            while True:
                while not self.peer_server_listener_queue.empty():
                    with futures.ThreadPoolExecutor(max_workers=8) as executor:
                        conn, addr = self.peer_server_listener_queue.get()
                        data_received = json.loads(conn.recv(1024).decode('utf-8'))
                        #data_received=data_received.decode('utf-8')

                        # if data_received['command'] == 'obtain_active':
                        #     fut = executor.submit(
                        #         self.peer_server_upload, conn, data_received)
                        if data_received['command']== 'message' or data_received['command']=='connect':
                            print("Message Recieved from: "+data_received['peer_id'])
                            print(data_received['message'])

        except Exception as e:
            print ("Peer Server Hosting Error, %s" % e)

    def peer_server(self):
        """
        This method is used start peer server listener and peer server 
        download deamon thread.
        """
        try:
            listener_thread = threading.Thread(target=self.peer_server_listener)
            listener_thread.setDaemon(True)

            operations_thread = threading.Thread(target=self.peer_server_host)
            operations_thread.setDaemon(True)

            listener_thread.start()
            operations_thread.start()

            threads = []
            threads.append(listener_thread)
            threads.append(operations_thread)

            for t in threads:
                t.join()
        except Exception as e:
            print ("Peer Server Error, %s" % e)
            sys.exit(1)
    
    def run(self):
        """
        Deamon thread for Peer Server and Sensor Updater.
        """
        if self.name == "PeerServer":
            self.peer_server()
        elif self.name == "SensorUpdater":
            self.generate_data_continuosly()

class Peer():
    def __init__(self, server_port, network):
        """
        Constructor used to initialize class object.
        """
        self.peer_hostname = socket.gethostbyname('localhost')
        self.server_port = server_port
        self.data = {}
        self.network=network
    
    def generate_sensor_data(self):
        self.data['light']= sensor.Light()
        self.data['proximity']=sensor.ProximitySensor()
        self.data['location']=sensor.LocationSensor()
        self.data['speed']=sensor.SpeedSensor()
        self.data['obstacle']=sensor.Obstacle()
        self.data['fuel']=sensor.FuelSensor()
        self.data['lane_change']=sensor.LaneChangeSensor()
        return self.data

    def broadcast_peers(self, message):
        nodes=self.list_nodes()
        for node in nodes:
            if(node==self.peer_hostname+':'+self.peer_id):
                continue
            peer_request_addr, peer_request_port = node.split(':')
            peer_request_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_request_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_request_socket.connect(
                (socket.gethostbyname('localhost'), int(peer_request_port)))

            cmd_issue = {
                'command' : 'message',
                'message': message,
                'peer_id':self.peer_id
            }
    
            peer_request_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
            rcv_data = peer_request_socket.recv(1024000)
            print(rcv_data)
            peer_request_socket.close()

    def connect_network_leader(self,addr):
        hostname,port=addr.split(':')
        leader_addr=self.get_leader(hostname,port)
        peer_request_addr, peer_request_port = leader_addr.split(':')
        peer_request_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_request_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer_request_socket.connect(
                (peer_request_addr, int(peer_request_port)))
        message='Connection established between Leader '+str(leader_addr) +' and Leader '+str(self.peer_id)

        cmd_issue = {
                'command' : 'connect',
                'message': message,
                'peer_id':self.peer_id
            }
    
        peer_request_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
        rcv_data = peer_request_socket.recv(1024000)
        print(rcv_data)
        peer_request_socket.close()


    def generate_data_continuously(self):
        #try:
        message=''
        while True:
            time.sleep(15)
            data=self.generate_sensor_data()

            print(self.data)
            self.update_server(data)

            if(self.network):
                if(self.peer_id==self.get_leader(self.peer_hostname,self.server_port)):
                    self.connect_network_leader(self.network)
            if(self.data['fuel']<2):
                message='Fuel low: Shutting off Device '+str(self.peer_id)
                print(message)
                self.broadcast_peers(message)
                self.deregister_peer(message)
                break
            if(self.data['obstacle']<20):
                message='Obstacle found at Latitude:'+str(self.data['location']['Latitude'])+', Longitude:'+str(self.data['location']['Longitude'])
                print(message)
                self.broadcast_peers(message)
              
    def update_server(self,data):
        #free_socket = self.get_free_socket()
        cmd_issue = {'command' : 'update','peer_id' : self.peer_id,'data' : data}
        peer_to_server_socket = \
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_to_server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer_to_server_socket.connect((self.peer_hostname, self.server_port))
        peer_to_server_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
        rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
        print(rcv_data)
        peer_to_server_socket.close()
        if rcv_data:
            print ("Data Update of Peer: %s on server successful" \
                % (self.peer_hostname))
        else:
            print ("Data Update of Peer: %s on server unsuccessful" \
                % (self.peer_hostname))


    def get_free_socket(self):
        """
        This method is used to obtain free socket port for the registring peer 
        where the peer can use this port for hosting file as a server.

        @return free_socket:    Socket port to be used as a Peer Server.
        """
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_socket.bind(('', 0))
            free_socket = peer_socket.getsockname()[1]
            peer_socket.close()
            return free_socket
        except Exception as e:
            print ("Obtaining free sockets failed: %s" % e)
            sys.exit(1)

    def register_peer(self):
        """
        Registering peer with Central Index Server.
        """
        #try:
        data=self.generate_sensor_data()
        free_socket = self.get_free_socket()
        print ("Registring Peer with Server...")

        peer_to_server_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_to_server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        peer_to_server_socket.connect(
                (self.peer_hostname, self.server_port))

        cmd_issue = {
                'command' : 'register',
                'peer_port' : free_socket,
                'data' : self.data,
            }
        peer_to_server_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
        rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
        print(rcv_data)
        #rcv_data=rcv_data.decode('utf-8')
        peer_to_server_socket.close()
        if rcv_data[1]:
            self.hosting_port = free_socket
            self.peer_id = rcv_data[0] + ":" + str(free_socket)
            print ("registration successfull, Peer ID: %s:%s" \
                              % (rcv_data[0], free_socket))
        else:
            print ("registration unsuccessfull, Peer ID: %s:%s" \
                              % (rcv_data[0], free_socket))
            #sys.exit(1)
        #except Exception as e:
        #print ("Registering Peer Error, %s" % e)
        #sys.exit(1)

    def list_nodes(self):
        """
        Obtain files present in Index Server.
        """
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
            peer_to_server_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            #rcv_data=rcv_data.decode('utf-8')
            peer_to_server_socket.close()
            print ("Node List in Server:")
            for f in rcv_data:
                print (f)
            return rcv_data
        except Exception as e:
            print ("Listing Nodes from Index Server Error, %s" % e)
        
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
            peer_to_server_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            #rcv_data=rcv_data.decode('utf-8')
            peer_to_server_socket.close()
            print ("leader:",rcv_data)
            
            return rcv_data
        except Exception as e:
            print ("Listing leader from Index Server Error, %s" % e)

    def secure(self, data):

    # Define XOR key 
        xorKey = 'P';  
  
    # perform XOR operation of key with every character in string 

        for i in range(len(data)):
            try:
              data = data[:i] + chr(ord(data[i]) ^ ord(xorKey)) +data[i + 1:]
            except:
              continue
    #print "Encrypted message = ",data
        return data

    def deregister_peer(self,message=''):
        """
        Deregister peer from Central Index Server.
        """
        try:
            print ("Deregistring Peer with Server...")

            peer_to_server_socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_to_server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_to_server_socket.connect(
                (self.peer_hostname, self.server_port))

            cmd_issue = {
                'command' : 'deregister',
                'peer_id' : self.peer_id,
                #'files' : self.file_list,
                'message':message,
                'hosting_port' : self.hosting_port
            }
            peer_to_server_socket.sendall(json.dumps(cmd_issue).encode('utf-8'))
            rcv_data = json.loads(peer_to_server_socket.recv(1024).decode('utf-8'))
            #rcv_data=rcv_data.decode('utf-8')
            peer_to_server_socket.close()
            if rcv_data:
                print ("deregistration of Peer: %s on server successful" \
                      % (self.peer_id))
            else:
                print ("deregistration of Peer: %s on server unsuccessful" \
                      % (self.peer_id))
        except Exception as e:
            print ("Deregistering Peer Error, %s" % e)

if __name__ == '__main__':
    """
    Main method starting deamon threads and peer operations.
    """
    try:
        args = get_args()
        print ("Starting Peer...")
        print(args.network)
        p=Peer(args.server,args.network)
            
        p.register_peer()

        print ("Stating Peer Server Deamon Thread...")
        server_thread = PeerOperations(1, "PeerServer", p)
        server_thread.setDaemon(True)
        server_thread.start()
        p.generate_data_continuously()
        
    except Exception as e:
        print (e)
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        p.deregister_peer()
        print ("Peer Shutting down...")
        time.sleep(1)
        sys.exit(1)

__author__ = 'arihant'
