import service, instance, coverage
import os, sys, subprocess, signal
import inotify.adapters, inotify.constants

class UMLInstance(instance.Instance):
    def __init__(self, service, conn):
        super().__init__(service,conn)

    def _createMaster(self):
        pass

    def _spawn(self):
        self.pid = os.fork()
        if self.pid == 0:
            # Make GCOV dump into the session_dir
            os.close(sys.stdin.fileno())
            os.close(sys.stderr.fileno())
            os.close(sys.stdout.fileno())

            if self.conn:
                os.dup2(self.conn.fileno(), sys.stdin.fileno())
                os.dup2(self.conn.fileno(), sys.stderr.fileno())
                os.dup2(self.conn.fileno(), sys.stdout.fileno())

            os.execvp(self.service.cmd[0], self.service.cmd)
            raise Exception("Failed to Exec")

    def run(self):
        self._spawn()
        lcovfile = os.path.join(self.service.gcov_dir, "lcov.")
        with open(lcovfile + "lock", "w"):
            pass

        while True:
            i = inotify.adapters.Inotify()
            i.add_watch(lcovfile + "lock", inotify.constants.IN_CLOSE_WRITE)
            for event in i.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                self.coverage.update(lcovfile + "cov")

class UMLService(service.Service):
    def __init__(self, cmd, port):
        super().__init__(cmd, port)
        self.cmd.append('GCOV_PREFIX=' + self.gcov_dir)
        self.cmd.append('GCOV_PREFIX_STRIP=' + str(service.gcovstrip))
        self.proc_dir = os.path.join(self.session_dir, "proc")
        os.mkdir(self.proc_dir)
        try:
            os.mkdir("/dev/uml")
        except FileExistsError:
            pass

    def _createMaster(self):
        pass

    def _createCoverage(self):
        self.coverage = UMLCoverage(service.gcovstrip, self.gcov_dir)
        self.coverage.service = self

    def createInstance(self, conn):
        return UMLInstance(self, conn)

    def __str__(self):
        return "UMLService"

class UMLCoverage(coverage.Coverage):
    def __init__(self, strip, prefix):
        super().__init__(strip, prefix)
        self.coverage = {'files':[]}

    def __cononicalize_source(self, source):
        if (source.startswith(self.prefix)):
            source = source[len(self.prefix) + 1:]
        elif source.startswith(service.SERVICES_ROOT):
            source = source[len(service.SERVICES_ROOT) + 1:]
        elif os.path.abspath(source):
            source = "root" + source
        return source

    def update(self, file):
        self.coverage = {'files':{}}
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith('DA:'):
                    [num, count] = line[3:].split(",")
                    if num in curfile["lines"]:
                        if int(count) > 0 and curfile["lines"][num]["count"] == 0:
                            curfile["lines_executed"] += 1
                        curfile["lines"][num]["count"] += int(count)
                    else:
                        curfile["lines"][num] = {"branches": [], "count": int(count), "line_number": num, "unexecuted_block": 0, "functions_name": ""}
                        curfile["lines_total"] += 1
                        if int(count) > 0:
                            curfile["lines_executed"] += 1
                elif line.startswith('end_of_record'):
                    curfile = None
                elif line.startswith('SF:'):
                    file_name = self.__cononicalize_source(line[3:-1])
                    line_index = 0
                    curfile = None
                    if file_name in self.coverage['files']:
                        curfile = self.coverage['files'][file_name]
                    else:
                        curfile = {"file": file_name, "functions": [], "lines" : {}, 'lines_total':0, 'lines_executed':0}
                        self.coverage['files'][file_name] = curfile
                        self.files.append(file_name)
                else:
                    pass
        self.notifyChangeListeners()

    def get(self, files=None, pids=None):
        return self.coverage

    def capture(self, pid):
        coverage = self.gcovrt.get_coverage(pid = pid)
        self.coverage = self + coverage

def serviceFactory(name, port = None):
    return UMLService(name, port)
