#!/usr/bin/python
import argparse
from multiprocessing import Queue
import time
import sys
import socket
import json
import threading
from concurrent import futures

#get arguments from command line
def get_args():
    parser = argparse.ArgumentParser(
        description='Arguments for index server')
    parser.add_argument('-p', '--port',type=int,required=True,action='store', help='Index Server Port Number')
    args = parser.parse_args()
    return args

class IndexServerOperations(threading.Thread):
    #initialize serverOperations object
    def __init__(self, threadid, name, server_port):
        
        threading.Thread.__init__(self)
        self.threadID = threadid
        self.name = name
        self.server_port = server_port
        self.hash_table_ports_peers = {}
        self.hash_table_peer_data = {}
        self.leader=''
        self.leader_nodes_connected=[]
        self.listener_queue = Queue()

    #use index server port  to listen to incoming connections to index server
    def server_listener(self):
    
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_host = socket.gethostbyname(socket.gethostname())
            server_socket.bind((server_host, self.server_port))
            server_socket.listen(10)
            while True:
                conn, addr = server_socket.accept()
                self.listener_queue.put((conn,addr))
        except Exception as e:
            print ("Server Listener on port Failed: %s" % e)
            sys.exit(1)

    #function invoked by peer trying to register to index server
    def registry(self, addr, data, peer_port):
    
        try:
            self.hash_table_ports_peers[peer_port] = addr[0]
            peer_id = addr[0] + ":" + str(peer_port)
            #add peer to hash table
            self.hash_table_peer_data[peer_id] = data
            return True
        except Exception as e:
            print ("Peer registration failure: %s" % e)
            return False

    #function invoked by peer trying to update sensor data to index server
    def update(self, peer_update):
        try:
            self.hash_table_peer_data[peer_update['peer_id']]=peer_update['data']
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
    def deregistry(self, peer_data):
        try:
            if peer_data['hosting_port'] in self.hash_table_ports_peers:
                self.hash_table_ports_peers.pop(peer_data['hosting_port'], None)
            if peer_data['peer_id'] in self.hash_table_peer_data:
                self.hash_table_peer_data.pop(peer_data['peer_id'], None)
            return True
        except Exception as e:
            print ("Peer deregistration failure: %s" % e)
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

            listener_thread = threading.Thread(target=self.server_listener)
            listener_thread.setDaemon(True)
            listener_thread.start()
            
            while True:
        
                while not self.listener_queue.empty():
                    with futures.ThreadPoolExecutor(max_workers=8) as executor:
                        conn, addr = self.listener_queue.get()
                        secured_data_received = json.loads(conn.recv(1024).decode('utf-8'))
                        data_received=self.secure_dict(secured_data_received)
                        print ("Got connection from %s on port %s, requesting " \
                                "for: %s" % (addr[0], addr[1], data_received['command']))

                        if data_received['command'] == 'register':
                            fut = executor.submit(self.registry, addr,
                                                    data_received['data'], 
                                                    data_received['peer_port'])
                            success = fut.result(timeout= None)
                            if success:
                                print ("registration successfull, Peer ID: %s:%s" \
                                        % (addr[0], data_received['peer_port']))
                                conn.send(json.dumps([addr[0], success]).encode('utf-8'))
                            else:
                                print ("registration unsuccessfull, Peer ID: %s:%s" \
                                        % (addr[0], data_received['peer_port']))
                                conn.send(json.dumps([addr[0], success]).encode('utf-8'))

                        elif data_received['command'] == 'update':
                            fut = executor.submit(self.update, data_received)
                            success = fut.result(timeout= None)
                            if success:
                                print ("Update of Peer ID: %s successful" \
                                        % (data_received['peer_id']))
                                conn.send(json.dumps(success).encode('utf-8'))
                            else:
                                print ("Update of Peer ID: %s unsuccessful" \
                                        % (data_received['peer_id']))
                                conn.send(json.dumps(success).encode('utf-8'))

                        elif data_received['command'] == 'list':
                            fut = executor.submit(self.list_peer_nodes)
                            #print(self.list_peer_nodes())
                            nodes_list = fut.result(timeout= None)
                            print ("Node list generated, %s" % nodes_list)
                            conn.send(json.dumps(list(nodes_list)).encode('utf-8'))
                        
                        elif data_received['command']=='leader':
                            fut = executor.submit(self.get_leader)
                            #print(self.list_peer_nodes())
                            leader = fut.result(timeout= None)
                            print ("Leader node: , %s" % leader)
                            conn.send(json.dumps(leader).encode('utf-8'))
                        
                        elif data_received['command']=='update_leader':
                            fut = executor.submit(self.update_leader,data_received['peer_id'])
                            #print(self.list_peer_nodes())
                            success = fut.result(timeout= None)
                            print ("Updated Leader node: , %s" % data_received['peer_id'])
                            conn.send(json.dumps(success).encode('utf-8'))

                        elif data_received['command'] == 'connect_update':
                            fut = executor.submit(self.connect,data_received['peer_id'])
                            success = fut.result(timeout= None)
                            if success:
                                print ("Update of leader nodes connected: %s successful" \
                                        % (data_received['peer_id']))
                                conn.send(json.dumps(success).encode('utf-8'))
                            else:
                                print ("Update of leader nodes connected: %s unsuccessful" \
                                        % (data_received['peer_id']))
                                conn.send(json.dumps(success).encode('utf-8'))

                        elif data_received['command'] == 'deregister':
                            fut = executor.submit(self.deregistry, data_received)
                            success = fut.result(timeout= None)
                            if success:
                                print ("deregistration of Peer ID: %s successful" \
                                        % (data_received['peer_id']))
                                print(data_received['message'])
                                conn.send(json.dumps(success).encode('utf-8'))
                            else:
                                print ("deregistration of Peer ID: %s unsuccessful" \
                                        % (data_received['peer_id']))
                                conn.send(json.dumps(success).encode('utf-8'))

                        
                        print ("Peer ports : %s" % self.hash_table_ports_peers)
                        print ("Peer sensor data : %s" % self.hash_table_peer_data)
                        print ("Peer Leader:  %s" % self.leader)
                        print ("Leader nodes connected: %s" % self.leader_nodes_connected)
                        conn.close()
                        
        except Exception as e:
            print ("Server Run error, %s " % e)
            sys.exit(1)
        
if __name__ == '__main__':
    
    try:
        args = get_args()
        print ("Index Server.....")
        oper_thread = IndexServerOperations(1, "IndexServerOperations",args.port) 
        oper_thread.start()
        
    except Exception as e:
        print (e)
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        print ("Index Server Switching off.....")
        time.sleep(1)
        sys.exit(1)