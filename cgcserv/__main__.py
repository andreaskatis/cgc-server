from flask import (
            Blueprint, Response, render_template, redirect, request, session, jsonify, Flask
            )
from flask_socketio import SocketIO, send, emit, join_room, leave_room, rooms
import sys
import os
import atexit
import shutil
import json
import subprocess
import threading
from urllib.parse import urlparse

MODULE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(MODULE_DIR)
import service
import cgcserv
import logging

app = Flask(__name__)
app.config['SCERET_KEY'] = "secret!"

#TODO: Use eventlet for threading but use python threads for now to allow messages to emit from instance threads
socketio = SocketIO(app, async_mode="threading")

sessions = {}
freeports = list(range(5001, 5100))
usedports = []

def update_sessions():
    summary = {k: v.summary() for k, v in sessions.items()}
    socketio.emit('sessions', summary)   

@app.route('/')
def index(service_list=None):
    return render_template('index.html')

@socketio.on('sessions')
def on_sessions(data):
    update_sessions()

@socketio.on('join')
def on_join(data):
    sid = data['sid']
    if sid in sessions:
        join_room(sid)
        send("Joined room " + sid)
        emit('events', {'events' : sessions[sid].events, 'cores' : sessions[sid].cores}, room=sid)
        emit('coverage', sessions[sid].dump_coverage(), room=sid)
    else:
        emit('error', {'error': 'Invalid SID'})

@socketio.on('leave')
def on_leave(data):
    sid = data['sid']
    if sid in sessions:
        leave_room(sid)
    else:
        emit('error', {'error': 'Invalid SID'})

def sessionEvent(service):
    """Callback for session events"""
    socketio.emit('events', {'events' : service.events, 'cores' : service.cores}, room=service.sid)

def sessionCoverageChange(coverage):
    """Callback for coverage changes"""
    socketio.emit('coverage', coverage.service.dump_coverage(), room=coverage.service.sid)

def sessionStart(serviceName):
    """Create a session for the given service"""
    try:
        port = freeports.pop()
    except:
        return {"error": "Out of ports"}

    try:
        s = service.serviceFactory(serviceName, port)
        s.start()
    except Exception as e:
        raise

    usedports.append(port)
    s.addCoverageListener(sessionCoverageChange)
    s.addEventListener(sessionEvent)
    sessions[s.sid] = s
    update_sessions()
    return s.details()

def sessionStop(sid):
    """Stop a session with the given session id"""
    session = sessions.pop(sid, None)
    if (session == None):
        return jsonify(error="Invalid SID")

    session.stop()
    try:
        shutil.rmtree("static/" + s.sid)
    except:
        pass
    usedports.remove(session.port)
    freeports.append(session.port)
    update_sessions()

def sessionEvents(sid):
    """Return a dictionary of events for the given session id"""
    try:
        s = sessions[sid]
    except:
        return {'error':"Invalid SID"}
    return s.events

@socketio.on_error()        # Handles the default namespace
def error_handler(e):
    raise(e)

@socketio.on('start')
def on_start(data):
    serviceName = data.pop('service', None)
    if serviceName == None:
        emit('start', {'error': 'No service Provided'})

    emit('start', sessionStart(serviceName))

@socketio.on('stop')
def on_stop(data):
    return emit('stop', sessionStop(data['sid']))

@app.route('/session/<sid>/sources')
@app.route('/session/<sid>/sources/<path:subpath>')
def sources(sid, subpath=''):
    try:
        s = sessions[sid]
    except:
        return jsonify(error="Invalid SID"), 404

    source_path = os.path.join(service.SERVICES_ROOT, subpath)
    if os.path.isdir(source_path):
        files = [f for f in s.coverage.files if f.startswith(subpath)]
        return jsonify(files)

    if subpath not in s.coverage.files:
        return jsonify(error="Invalid Path"), 404

    def read_source():
        with open(source_path, encoding="utf-8") as f:
            for line in f:
                yield line

    return Response(read_source(), mimetype='text/plain')

@app.route('/session/start')
def session_start():
    if not 'service' in request.args:
        return jsonify(error="No such service")
    return jsonify(sessionStart(request.args['service']))

@app.route('/session/<sid>/stop')
def session_stop(sid):
    return jsonify(sessionStop(sid))

@app.route('/session/<sid>/events')
def session_events(sid):
    return jsonify(sessionEvents(sid))

@app.route('/session/<sid>/coverage')
@app.route('/session/<sid>/coverage/<path:subpath>')
def coverage_id(sid, subpath=''):
    if sid not in sessions:
        return jsonify(error="Invalid SID")
    s = sessions[sid]

    coverage = s.dump_coverage()
    if subpath != ''  and subpath in coverage:
        return jsonify(coverage[subpath])

    return jsonify(coverage)

@app.route('/session/<sid>/cores')
def session_cores(sid):
    try:
        s = sessions[sid]
    except:
        return jsonify(error="Invalid SID")
    cores = os.listdir(s.cores_dir)
    return jsonify(cores)

@app.route('/session/<sid>/gdb/<core>')
def session_gdb(sid, core):
    try:
        s = sessions[sid]
    except:
        return jsonify(error="Invalid SID")
    try:
        port = freeports.pop()
    except:
        return jsonify({"error": "Out of ports"})
    
    corefile = os.path.join(s.cores_dir, core)

    #TODO: Use flask application dispatch instead of subprocess
    def gdbgui_thread(port, corefile, cmd):
        proc = subprocess.Popen(["gdbgui", "-p", str(port), "-r", "--gdb-args", corefile, cmd])
        proc.wait()
        freeports.append(port)
        return

    thread = threading.Thread(target=gdbgui_thread, args=(port, corefile, s.cmd[0]))
    thread.start()
    url = urlparse(request.base_url)
    return redirect("http://" + url.hostname + ":" + str(port))

@app.route('/session/<sid>')
def session_list(sid):
    try:
        s = sessions[sid]
    except:
        return jsonify(error="Invalid SID")
    return jsonify(s.details())

@app.route('/sessions')
def sessions_list():
    summary = {k: v.summary() for k, v in sessions.items()}
    return jsonify(summary)

@app.route('/services')
def services_list():
    return jsonify(service.Service.available())

def cleanup():
    for sid in sessions:
        sessions[sid].stop()

atexit.register(cleanup)

if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)
    logger.addHandler(logging.FileHandler(os.path.join(MODULE_DIR, "static", "cgcserv.log")))
    app.debug = True
    socketio.run(app, host = "0.0.0.0")

