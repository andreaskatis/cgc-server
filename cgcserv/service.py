import json
import os, sys
import logging
import socket
import tempfile
import instance, coverage
import importlib
import subprocess
import shutil
from threading import Thread

logger = logging.getLogger("cgcserv")
MODULE_DIR = os.path.abspath(os.path.dirname(__file__))
try:
    SERVICES_ROOT = os.path.abspath(os.environ['CGC_ROOT'])
except:
    SERVICES_ROOT = os.path.abspath(os.path.join(MODULE_DIR, "..", "services"))

sys.path.append(SERVICES_ROOT)
with open(os.path.join(SERVICES_ROOT, "service.json")) as service_file:
    _service_list = json.load(service_file)

gcovstrip = len(SERVICES_ROOT.split(os.sep)) - 1

try:
    os.mkdir("/tmp/cgc_sessions")
except FileExistsError:
    pass

class Service(Thread):
    @staticmethod
    def available():
        return list(_service_list.keys())

    def __init__(self, name, port):
        Thread.__init__(self)
        self.name = name
        self.cmd = _service_list[self.name]['cmd'].split(" ");
        self.cmd[0] = os.path.join(SERVICES_ROOT, self.cmd[0])
        self.state = "Starting"
        self.port = port
        self.running = True
        self.notes_copied = False
        self.instances = {}
        self.events = {}
        self.cores = []
        self.eventListeners = []
        self.listener_thread = None
        self.coverage = None
        self.respawn = True
        self.master_instance = None
        self.__make_session_dirs()
        self.__build()
        self.__start_server()
        self._createMaster()
        self._createCoverage()

    def __make_session_dirs(self):
        self.session_dir = tempfile.mkdtemp(prefix="/tmp/cgc_sessions/")
        self.sid = os.path.basename(self.session_dir)
        for subdir in ["gcov", "html", "cores"]:
            path = os.path.join(self.session_dir, subdir)
            setattr(self, subdir + "_dir", path)
            os.mkdir(path)

    def __build(self):
        if os.path.isfile(self.cmd[0]):
            return
        self.state = "Building"
        logfile = os.path.join(SERVICES_ROOT, self.name + ".buildlog")
        with open(logfile, 'w') as log:
            cmd = ["make", "-C", SERVICES_ROOT, self.name]
            proc = subprocess.Popen(cmd, stdout=log, stderr=log)
            output, error = proc.communicate()
            logger.info(output)

    def __start_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("0.0.0.0", int(self.port)))
        self.sock.listen(10)
        self.state = "Waiting for Connections"

    def dump_coverage(self):
        pids = list(self.instances.keys())
        return self.coverage.get(pids = pids)

    def createInstance(self, conn):
        return instance.Instance(self, conn)

    def addCoverageListener(self, listener):
        self.coverage.addChangeListener(listener)

    def addEventListener(self, listener):
        self.eventListeners.append(listener)

    def fireEvent(self):
        for l in self.eventListeners:
            l(self)

    def _createCoverage(self):
        self.coverage = coverage.PyGcovRT(pid=self.master_instance.pid, strip=gcovstrip, prefix=self.gcov_dir)
        self.coverage.service = self

    def _createMaster(self):
        #master instance owns the process group id
        self.master_instance = instance.MasterInstance(self)

    def run(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
            except Exception as e:
                if self.running:
                    logger.error("Connection from %s:%d failed: " + str(e))
                continue
            logger.info("Connecting to %s:%d", addr[0], addr[1])
            instance = self.createInstance(conn)

    def stop(self):
        self.running = False
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        self.join()

        for k,instance in self.instances.items():
            instance.stop()
        self.master_instance.stop()
        shutil.rmtree(self.session_dir, True)

    def summary(self):
        return {"id": self.sid, "port": self.port, "name": self.name, "state": self.state}

    def details(self):
        return self.summary()

    def __str__(self):
        return self.sid

def serviceFactory(name, port = None):
    if name not in _service_list.keys():
        raise Exception("Invalid Service")

    try:
        module = importlib.import_module(name)
        if module != None:
            return module.serviceFactory(name, port)
    except ModuleNotFoundError:
        return Service(name, port)
    except:
        raise
