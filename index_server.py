#!/usr/bin/python
import socket
import argparse
import json
from concurrent import futures
import time
import threading
from multiprocessing import Queue
import sys

#get arguments from command line
def get_arguments():
    p = argparse.ArgumentParser(
        description='Arguments for index server')
    p.add_argument('-p', '--port',action='store',required=True,type=int, help='Index Server Port Number')
    arguments = p.parse_args()
    return arguments

class IndexServerOperations(threading.Thread):
    #initialize serverOperations object
    def __init__(self, idthread, th_name, s_port):
        
        threading.Thread.__init__(self)
        self.listen_queue = Queue()
        self.hash_table_ports_peers = {}
        self.name = th_name
        self.threadID = idthread
        self.s_port = s_port
        self.hash_table_peer_data = {}
        self.leader=''
        self.leader_nodes_connected=[]
        

    #use index server port  to listen to incoming connections to index server
    def listen_server(self):
    
        try:
            s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s_host = socket.gethostbyname(socket.gethostname())
            s_socket.bind((s_host, self.s_port))
            s_socket.listen(10)
            while True:
                connection, address = s_socket.accept()
                self.listen_queue.put((connection,address))
        except Exception as e:
            print ("Listen on server error: %s" % e)
            sys.exit(1)

    #function invoked by peer trying to register to index server
    def register_peer(self, address, rcv_data, p_port):
    
        try:
            self.hash_table_ports_peers[p_port] = address[0]
            p_id = address[0] + ":" + str(p_port)
            #add peer to hash table
            self.hash_table_peer_data[p_id] = rcv_data
            return True
        except Exception as e:
            print ("Registeration of Peer Failed: %s" % e)
            return False

    #function invoked by peer trying to update sensor data to index server
    def update(self, p_update):
        try:
            self.hash_table_peer_data[p_update['peer_id']]=p_update['data']
            return True
        except Exception as e:
            print ("Peer Sensor Data Update failure: %s" % e)
            return False

    #function invoked by peer trying to update leader info to index server
    def update_leader(self,peer_id):
        try:
            self.leader=peer_id
            return True
        except Exception as e:
            print ("Peer Leader Update failure: %s" % e)
            return False

    #function invoked by peer trying to update connection of networks to index server
    def connect(self, node_id):
        try:
            self.leader_nodes_connected.append(node_id)
            return True
        except Exception as e:
            print ("Leader Nodes Connected Update failure: %s" % e)
            return False

    #function invoked by peer to list nodes present in network
    def list_peer_nodes(self):
        try:
            nodes_list = self.hash_table_peer_data.keys()
            return nodes_list

        except Exception as e:
            print ("Listing Peer Nodes Error, %s" % e)

    #function invoked by peer to get leader of a network
    def get_leader(self):
        return self.leader
    
    #function invoked by peer to deregister itself from index server
    def deregister_peer(self, p_data):
        try:
            if p_data['hosting_port'] in self.hash_table_ports_peers:
                self.hash_table_ports_peers.pop(p_data['hosting_port'], None)
            if p_data['peer_id'] in self.hash_table_peer_data:
                self.hash_table_peer_data.pop(p_data['peer_id'], None)
            return True
        except Exception as e:
            print ("Deregisteration of Peer failed: %s" % e)
            return False

    #function to encrypt and decrypt string data
    def secure(self, str_data):
        try:
            Key = 'N';  
            for i in range(len(str_data)):
                try:
                    str_data = str_data[:i] + chr(ord(str_data[i]) ^ ord(Key)) +str_data[i + 1:]
                except:
                    continue
            return str_data

        except Exception as e:
            print ("Encryption/decryption Failure: %s" % e)
            return False
    
    #function to encrypt and decrypt dict data
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
        except:
            print ("Encryption/decryption Failure: %s" % e)
            return False

    #function to start index xerver thread
    def run(self):
        try:

            l_thread = threading.Thread(target=self.listen_server)
            l_thread.setDaemon(True)
            l_thread.start()
            
            while True:
        
                while not self.listen_queue.empty():
                    with futures.ThreadPoolExecutor(max_workers=8) as executor:
                        connection, address = self.listen_queue.get()
                        secured_data_received = json.loads(connection.recv(1024).decode('utf-8'))
                        data_rcv=self.secure_dict(secured_data_received)
                        print ("Connection recieved from %s on port %s, asking " \
                                "for: %s" % (address[0], address[1], data_rcv['command']))

                        if data_rcv['command'] == 'register':
                            f = executor.submit(self.register_peer, address,data_rcv['data'],data_rcv['peer_port'])
                            s = f.result(timeout= None)
                            if s:
                                print ("Peer ID: %s:%s registered" % (address[0], data_rcv['peer_port']))
                                connection.send(json.dumps([address[0], s]).encode('utf-8'))
                            else:
                                print ("Peer ID: %s:%s did not register" % (address[0], data_rcv['peer_port']))
                                connection.send(json.dumps([address[0], s]).encode('utf-8'))

                        elif data_rcv['command'] == 'update':
                            f = executor.submit(self.update, data_rcv)
                            s = f.result(timeout= None)
                            if s:
                                print ("Data of Peer ID: %s updated" % (data_rcv['peer_id']))
                                connection.send(json.dumps(s).encode('utf-8'))
                            else:
                                print ("Data of Peer ID: %s did not update" % (data_rcv['peer_id']))
                                connection.send(json.dumps(s).encode('utf-8'))

                        elif data_rcv['command'] == 'list':
                            f = executor.submit(self.list_peer_nodes)
                            nodes_list = f.result(timeout= None)
                            print ("Node list generated, %s" % nodes_list)
                            connection.send(json.dumps(list(nodes_list)).encode('utf-8'))
                        
                        elif data_rcv['command']=='leader':
                            f = executor.submit(self.get_leader)
                            leader = f.result(timeout= None)
                            print ("Leader node: , %s" % leader)
                            connection.send(json.dumps(leader).encode('utf-8'))
                        
                        elif data_rcv['command']=='update_leader':
                            f = executor.submit(self.update_leader,data_rcv['peer_id'])
                            s = f.result(timeout= None)
                            print ("Updated Leader node: , %s" % data_rcv['peer_id'])
                            connection.send(json.dumps(s).encode('utf-8'))

                        elif data_rcv['command'] == 'connect_update':
                            f = executor.submit(self.connect,data_rcv['peer_id'])
                            s = fut.result(timeout= None)
                            if s:
                                print ("Update of leader nodes connected: %s successful" % (data_rcv['peer_id']))
                                connection.send(json.dumps(s).encode('utf-8'))
                            else:
                                print ("Update of leader nodes connected: %s unsuccessful" % (data_rcv['peer_id']))
                                connection.send(json.dumps(s).encode('utf-8'))

                        elif data_rcv['command'] == 'deregister':
                            f = executor.submit(self.deregister_peer, data_rcv)
                            s = f.result(timeout= None)
                            if s:
                                print ("Peer ID: %s deregistered" % (data_rcv['peer_id']))
                                print(data_rcv['message'])
                                connection.send(json.dumps(s).encode('utf-8'))
                            else:
                                print ("Peer ID: %s did not deregister" % (data_rcv['peer_id']))
                                connection.send(json.dumps(s).encode('utf-8'))

                        
                        print ("Peer ports : %s" % self.hash_table_ports_peers)
                        print ("Peer sensor data : %s" % self.hash_table_peer_data)
                        print ("Peer Leader:  %s" % self.leader)
                        print ("Leader nodes connected: %s" % self.leader_nodes_connected)
                        connection.close()
                        
        except Exception as e:
            print ("Server Run error, %s " % e)
            sys.exit(1)
        
if __name__ == '__main__':
    
    try:
        args = get_arguments()
        print ("Starting Index Server")
        oper_thread = IndexServerOperations(1, "IndexServerOperations",args.port) 
        oper_thread.start()
        
    except Exception as e:
        print (e)
        sys.exit(1)
    except (SystemExit,KeyboardInterrupt):
        print ("Switched off Index Server")
        time.sleep(1)
        sys.exit(1)