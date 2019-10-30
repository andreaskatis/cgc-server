import signal, os
import pygcovrt
import struct
import time
from threading import Thread

class ChangeNotifyer():
    def __init__(self):
        self.listeners = []

    def addChangeListener(self, listener):
        self.listeners.append(listener)

    def notifyChangeListeners(self):
        for l in self.listeners:
            l(self)

class Coverage(ChangeNotifyer):
    def __init__(self, strip=0, prefix=""):
        ChangeNotifyer.__init__(self)
        self.files = []
        self.strip = strip
        self.prefix = prefix
        self.coverage = None
        self.service = None

    def capture(self, pid):
        newcov = self.get()

    def get(self, files):
        pass

    def add_pids(self, pid):
        pids.append(pid)

    def remove_pids(self, pids):
        pids.remove(pids)

    def __add__(self, other):
        if self.coverage == None:
            return other
        try:
            for f in self.coverage:
                for l in self.coverage[f]:
                    other[f][l] += self.coverage[f][l]
        except:
            raise

        return other

class PyGcovRT(Coverage, Thread):
    def __init__(self, pid, elf=None, mem=None, strip = 0, prefix = ""):
        super().__init__(strip, prefix)
        Thread.__init__(self)
        self.gcovrt = pygcovrt.pygcovrt(pid=pid, elf=elf, mem=mem)
        self.strip = strip
        self.strippath = None
        for s in self.gcovrt.sources:
            if os.path.isabs(s):
                if self.strippath == None:
                    self.strippath = os.path.join(*s.split(os.sep)[:strip+1])
                    self.stripn = len(self.strippath) + 2
                s = s[self.stripn:]
            self.files.append(s)
        self.start()
    
    def run(self):
        while True:
            time.sleep(0.5)
            self.notifyChangeListeners()

    def __coveragetogcov(self, orig):
        coverage = {"files":[]}
        for name, lines in orig.items():
            f = {"file": name, "functions":[], "lines":[], "lines_executed":0, "lines_total":0}
            coverage['files'].append(f)
            for num, count in lines.items():
                l = {"line_number": num, "count": count}
                f['lines'].append(l)
                f['lines_total'] += 1
                if (count > 0):
                    f['lines_executed'] += 1
        return coverage

    def get(self, files=None, pids=None):
        coverage_striped = {}
        try:
            coverage = self.gcovrt.get_coverage(pids = pids)
        except:
            #Failed to get coverage.  This can occur when the pid dies while
            #coverage is being collected on it.
            return None

        coverage = self + coverage
        for k in coverage:
            newpath = k
            if not os.path.isabs(k):
                newpath = os.path.join(self.relprefix, k)
            newpath = newpath[self.stripn:]
            coverage_striped[newpath] = coverage[k]
        return self.__coveragetogcov(coverage_striped)

    def capture(self, pid):
        coverage = self.gcovrt.get_coverage(pid = pid)
        self.coverage = self + coverage


