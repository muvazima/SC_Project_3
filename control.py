#!/usr/bin/python

import socket
import time
import threading
import json
import random
import argparse
import sys
from multiprocessing import Queue
from concurrent import futures


def get_args():
    """
    Get command line args from the user.
    """
    parser = argparse.ArgumentParser(
        description='Standard Arguments for talking to Central Index Server')
    parser.add_argument('-p', '--port',
                        type=int,
                        required=True,
                        action='store',
                        help='Server Port Number')
    
    args = parser.parse_args()
    return args

class ServerOperations(threading.Thread):
    def __init__(self, threadid, name, server_port):
        """
        Constructor used to initialize class object.

        @param threadid:    Thread ID.
        @param name:        Name of the thread.
        """
        threading.Thread.__init__(self)
        self.threadID = threadid
        self.name = name
        self.server_port = server_port
        self.hash_table_ports_peers = {}
        #self.hash_table_data = {}
        self.hash_table_peer_data = {}
        self.leader=''
        self.leader_nodes_connected=[]
        self.listener_queue = Queue()

    def server_listener(self):
        """
        Server Listener Method is used start Central Index Server to listen on
        port: 3344 for incoming connections.
        """
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            #server_host = socket.gethostbyname('localhost')
            server_host = socket.gethostbyname(socket.gethostname())
            server_socket.bind((server_host, self.server_port))
            server_socket.listen(10)
            while True:
                conn, addr = server_socket.accept()
                self.listener_queue.put((conn,addr))
        except Exception as e:
            print ("Server Listener on port Failed: %s" % e)
            sys.exit(1)

    def registry(self, addr, data, peer_port):
        """
        This method is invoked by the peer trying to register itself 
        with the Indexing Server.

        @param addr:           Address of the incoming connection.
        @param files:          File list sent by the peer.
        @param peer_port:      Peer's server port.

        @return free_socket:   Socket port to be used as a Peer Server.
        """
        try:
            self.hash_table_ports_peers[peer_port] = addr[0]
            peer_id = addr[0] + ":" + str(peer_port)
            self.hash_table_peer_data[peer_id] = data
            self.leader=peer_id
            # for f in files:
            #     if f in self.hash_table_files:
            #         self.hash_table_files[f].append(peer_id)
            #     else:
            #         self.hash_table_files[f] = [peer_id]
            return True
        except Exception as e:
            print ("Peer registration failure: %s" % e)
            return False

    def update(self, peer_update):
        """
        This method is invoked by the peer's file handler to update the files 
        in the Index Server. Peer file handler invokes this method upon addition 
        of new file or removal of existing file.

        @param peer_update:      Peer File Update details.
        """
        try:
            self.hash_table_peer_data[peer_update['peer_id']]=peer_update['data']


            return True
        except Exception as e:
            print ("Peer Sensor Data Update failure: %s" % e)
            return False
    def connect(self, node_id):
        try:
            self.leader_nodes_connected.append(node_id)
            return True
        except Exception as e:
            print ("Leader Nodes Connected Update failure: %s" % e)
            return False

    def list_peer_nodes(self):
        """
        This method is used display the list of files registered with 
        the Central Index Server.

        @return files_list:    List of files present in the server.
        """
        #try:
        nodes_list = self.hash_table_peer_data.keys()
        #print(nodes_list)
        return nodes_list

        #except Exception as e:
            #print ("Listing Peer Nodes Error, %s" % e)
    def get_leader(self):
        return self.leader
    # def search(self, file_name):
    #     """
    #     This method is used to search for a particular file.

    #     @param file_name:    File name to be searched.
    #     @return:             List of Peers associated with the file.
    #     """
    #     try:
    #         if file_name in self.hash_table_files:
    #             peer_list = self.hash_table_files[file_name]
    #         else:
    #             peer_list = []
    #         return peer_list
    #     except Exception as e:
    #         print ("Listing Files Error, %s" % e)

    def deregistry(self, peer_data):
        """
        The method is invoked when the Peer dies or Peer shutsdown to 
        remove all its entry from the Central Index Server.

        @param peer_data:      Peer data containing Peer details.
        @return True/False:    Return success or failure.
        """
        try:
            if peer_data['hosting_port'] in self.hash_table_ports_peers:
                self.hash_table_ports_peers.pop(peer_data['hosting_port'], None)
            if peer_data['peer_id'] in self.hash_table_peer_data:
                self.hash_table_peer_data.pop(peer_data['peer_id'], None)
            # for f in peer_data['files']:
            #     if f in self.hash_table_files:
            #         for peer_id in self.hash_table_files[f]:
            #             if peer_id == peer_data['peer_id']:
            #                 self.hash_table_files[f].remove(peer_id)
            #                 if len(self.hash_table_files[f]) == 0:
            #                     self.hash_table_files.pop(f, None)
            return True
        except Exception as e:
            print ("Peer deregistration failure: %s" % e)
            return False

    def run(self):
        """
        Starting thread to carry out server operations.
        """
        #try:
        print ("Starting Server Listener Daemon Thread...")
        listener_thread = threading.Thread(target=self.server_listener)
        listener_thread.setDaemon(True)
        listener_thread.start()
        
        while True:
    
            while not self.listener_queue.empty():
                with futures.ThreadPoolExecutor(max_workers=8) as executor:
                    conn, addr = self.listener_queue.get()
                    data_received = json.loads(conn.recv(1024).decode('utf-8'))
                        #data_recieved=data_recieved.decode('utf-8')

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

                    elif data_received['command'] == 'connect_update':
                        fut = executor.submit(self.connect,
                                                  data_received['peer_id'])
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

                        # print ("hash table: Files || %s" % \
                        #       self.hash_table_files)
                    print ("hash table: Port-Peers || %s" % \
                              self.hash_table_ports_peers)
                    print ("hash table: Peer-Data || %s" % \
                              self.hash_table_peer_data)
                    print("hash table: peer Leader: || %s" % \
                                self.leader)
                    print("hash table: leader nodes connected: || %s" % \
                                self.leader_nodes_connected)
                    conn.close()
        # except Exception as e:
        #     print ("Server Operations error, %s " % e)
        #     sys.exit(1)

if __name__ == '__main__':
    """
    Main method to start daemon threads for listener and operations.
    """
    try:
        args = get_args()
        print ("Starting Central Indexing Server...")
        print ("Starting Server Operations Thread...")
        operations_thread = ServerOperations(1, "ServerOperations",args.port) 
        operations_thread.start()
        
    except Exception as e:
        print (e)
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        print ("Central Index Server Shutting down...")
        time.sleep(1)
        sys.exit(1)