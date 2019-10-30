#!/bin/bash

usage()
{
	cat <<EOF

start.sh [-h | PKTFILE ]

PKTFILE defaults to pkt.bin
Starts the wifi_relay service and sends a packet from PKTFILE every 1 second
EOF
}

sendpkt()
{
	local pktfile=$1
	size=$(($(stat -c%s $pktfile) + 1 ))
	sleep 10 #Let UML startup
	while [ 1 ] ; do
		printf '0000 %04x' "$size" | xxd -r
		cat $pktfile
		echo ''
		sleep 1
	done
}

if [ "$1" == "-h" ] ; then
	usage
	exit 0
fi
service=wifi_relay
file=$1
response=$(curl --noproxy localhost -X GET http://localhost:5000/session/start?service=$service 2>/dev/null)
echo "$response"
error=$(echo "$response" | sed -ne 's|.*"error": *\(.*\),.*|\1|p')
port=$(echo "$response" | sed -ne 's|.*"port": *\([0-9]\+\).*|\1|p')
if [ -z "$port" ] ; then
	echo "Failed to start: $error"
	exit 1
fi
echo Starting on port "$port"
sendpkt "${file:=pkt.bin}" | nc localhost $port
