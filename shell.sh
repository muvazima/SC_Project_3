mkdir -p logs
python3 control.py -p 33001 > logs/control.log &
sleep 20
python3 Peer.py -s 33001 -p 33009 > logs/peer1.log &
sleep 20
python3 Peer.py -s 33001 -p 33008 > logs/peer2.log &
sleep 20
python3 Peer.py -s 33001 -p 33007 > logs/peer3.log &
sleep 20
python3 Peer.py -s 33001 -p 33006 > logs/peer4.log &
sleep 20
python3 Peer.py -s 33001 -p 33005 > logs/peer5.log &