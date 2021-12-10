mkdir -p logs_n2
python3 index_server.py -p 33100 -n '10.35.70.7:33001' > logs_n2/control.log &
sleep 20
python3 Peer.py -s 33100 -p 33109 -n '10.35.70.7:33001'> logs_n2/peer1.log &
sleep 20
python3 Peer.py -s 33100 -p 33108 -n '10.35.70.7:33001'> logs_n2/peer2.log &
sleep 20
python3 Peer.py -s 33100 -p 33107 -n '10.35.70.7:33001'> logs_n2/peer3.log &
sleep 20
python3 Peer.py -s 33100 -p 33106 -n '10.35.70.7:33001'> logs_n2/peer4.log &
sleep 20
python3 Peer.py -s 33100 -p 33105 -n '10.35.70.7:33001'> logs_n2/peer5.log &