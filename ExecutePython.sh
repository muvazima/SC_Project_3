python3 control.py -p 3365 > control.log &
sleep 20
python3 Peer.py -s 3365 > peer1.log &
sleep 20
python3 Peer.py -s 3365 > peer2.log &
sleep 20
python3 Peer.py -s 3365 > peer3.log &
sleep 20
python3 Peer.py -s 3365 > peer4.log &
sleep 20
python3 Peer.py -s 3365 > peer5.log &