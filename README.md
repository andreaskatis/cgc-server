# CGC Server                                                                  

cgcserv exposes each service's stdin and stdout on a tcp socket.  Each new tcp 
connection spawns a new cgc process. The process is killed and the connection 
is closed only when the the client closes the socket (Results in process getting SIGPIPE).
If the process exits successfully (some cgc applications may be "one-off" some 
may exit when given an appropriate command) cgcserv will re-spawn the process
and keep the connection to the fuzzer open.

cgcserv is provided in a docker environment for convenience.  The docker container 
takes care of building the cgc binaries and starting the cgcserver.

## Building                                                               

From the root directory,

  `make`
 
This will execute the command:

  `docker build -t cgcserv .`

### Building behind a proxy

Add proxies to ~/docker/config.json

See: https://docs.docker.com/network/proxy/

## Starting the Server                                                                

The server requires that ports are exposed.  Each new session will start
attached to a random port in the given range.  From the root directory you can
simply execute:

  `run.sh`
  
which will execute the command:

  `docker run -it -p 5000-5100:5000-5100 cgcserv`                                                  

To stop the server, type Ctl-C.

Ports can be mapped on the host if needed.

See: https://docs.docker.com/engine/reference/run/        

This starts the main server which runs on port 5000 and waits for http requests
to start services.

## Web Interface

A web interface is provided to manage the server and provide coverage
data.  The interface is accessed by directing a browser to http://localhost:5000/.
The server can also be managed by making direct GET requests to the server.

## Sessions

A session is a single service attached to a unique port and allows multiple
clients to attach to it.  Each new client spawns a new instance of the
service.  Coverage data is aggregated between all clients on the same session.

## Start Session

A session can be started by sending a GET request to the main server
on port 5000.

'curl -X GET http://localhost:5000/session/start?service=SERVICE'

Where SERVICE is the name of the service to start.  Arguments can be passed
to the service by using '+' instead of spaces.

'curl -X GET http://localhost:5000/session/start?service=PTaaS+unused'

This returns a json struct as the response:

'{
	sid:<SESSION_ID>
	port:<PORT_NO>
}'

Where SESSION_ID is a unique ID for the new session and PORT_NO is the tcp
port that the service was attached to.

## Stop Session

A session can be stopped by sending a GET request to the main server
on port 5000.

'curl -X GET http://localhost:5000/session/SESSION_ID/stop

## Details

Get details about a running session

'curl -X GET http://localhost:5000/session/SESSION_ID/details

## Simple 1-way Connections

Assuming that "fuzzer" generates tests on stdout:

  `fuzzer | nc localhost PORT_NO`

Or more generally:

  `fuzzer | nc <ip_address> PORT_NO`
  
Any output from the CGC server will appear on stdout.

## Fuzzing with Feedback

To send service output back to the fuzzer:

  `socat EXEC:"fuzzer" TCP4:<ip_address>:PORT_NO`

## Demo

After starting the server, go to the /demos/PTaaS directory and execute:

  `start.sh`

This will connect a fuzzer to the PTaaS service provided by the CGC server.

You can see live coverage results for this session by pointing your browser to:

  `http://localhost:5000`
