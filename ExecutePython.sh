#!/bin/bash
python3 control.py -p 33001 > control.log &
sleep 20;
python3 Peer.py -s 33001 -p 33002 > peer1.log &
sleep 20;
python3 Peer.py -s 33001 -p 33003 > peer2.log &
sleep 20;
python3 Peer.py -s 33001 -p 33004 > peer3.log &
sleep 20;
python3 Peer.py -s 33001 -p 33005 > peer4.log &
sleep 20;
python3 Peer.py -s 33001 -p 33006 > peer5.log &
