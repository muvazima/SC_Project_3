python3 control.py -p 3366 > control.log &
sleep 20
python3 Peer.py -s 3366 > peer1.log &
sleep 20
python3 Peer.py -s 3366 > peer2.log &
sleep 20
python3 Peer.py -s 3366 > peer3.log &
sleep 20
python3 Peer.py -s 3366 > peer4.log &
sleep 20
python3 Peer.py -s 3366 > peer5.log &