#!/bin/sh
response=$(curl --noproxy localhost -X GET http://localhost:5000/session/start?service=PTaaS 2>/dev/null)
echo "$response"
error=$(echo "$response" | sed -ne 's|.*"error": *\(.*\),.*|\1|p')
port=$(echo "$response" | sed -ne 's|.*"port": *\([0-9]\+\).*|\1|p')
if [ -z "$port" ] ; then
	echo "Failed to start: $error"
	exit 1
fi
echo Starting on port "$port"
./ptass_fuzz.py | nc localhost $port
