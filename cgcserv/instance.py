import os, sys, subprocess, signal
import logging
import service, coverage
from threading import Thread, Lock
from ptrace.binding import (ptrace_traceme, ptrace_cont, ptrace_detach, ptrace_attach)
from ptrace.debugger.process import PtraceProcess

logger = logging.getLogger("cgcserv")
SIGNAL_NAMES = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
            if v.startswith('SIG') and not v.startswith('SIG_'))

class Instance(Thread):
    def __init__(self, service, conn):
        self.service = service
        self.coverage = service.coverage
        self.conn = conn
        self.finiaddr = self._get_symbol_addr("__gcov_exit")
        self.eventLock = Lock()
        Thread.__init__(self)
        self.start()

    def __spawn(self):
        self.pid = os.fork()
        if self.pid == 0:
            # Make GCOV dump into the session_dir
            os.environ['GCOV_PREFIX'] = self.service.gcov_dir
            os.environ['GCOV_PREFIX_STRIP'] = str(service.gcovstrip)
            os.close(sys.stdin.fileno())
            os.close(sys.stderr.fileno())
            os.close(sys.stdout.fileno())

            os.dup2(self.conn.fileno(), sys.stdin.fileno())
            os.dup2(self.conn.fileno(), sys.stderr.fileno())
            os.dup2(self.conn.fileno(), sys.stdout.fileno())

            ptrace_traceme() #force process to stop after exec
            os.execvp(self.service.cmd[0], self.service.cmd)
            raise Exception("Failed to Exec")
        (pid, ret) = os.waitpid(self.pid, 0) #Wait for first trap
        self.tracer = PtraceProcess(None, self.pid, True)
        #set a breakpoint when it exits gracefully
        self.exitbp = self.tracer.createBreakpoint(self.finiaddr)
        ptrace_cont(self.pid) #Start the process again
        self.service.instances[self.pid] = self
        #The process could still not be linked by now
        #so there is a bit of a race between getting coverage
        #and when its has counters mapped.  Add it anyway

        #and handle the I/O error when getting coverage.  This
        #is a bit faster then setting a breakpoint at main everytime
        #it spawns.

    def __handle_event(self, pid, status):
        if os.WCOREDUMP(status):
            logger.warning("Core dump created for %s" % (self.pid))

        if os.WIFEXITED(status):
            self.service.instances.pop(self.pid, None)
            self.log_event(0)
            self.__spawn()

        elif os.WIFSIGNALED(status):
            self.service.instances.pop(self.pid, None)
            sig = os.WTERMSIG(status)
            self.log_event(sig)
            self.__spawn()

        elif os.WIFSTOPPED(status):
            self.coverage.capture(self.pid)
            sig = os.WSTOPSIG(status)

            #Don't log breakpoints
            if sig == signal.SIGTRAP:
                self.exitbp.desinstall(set_ip = True)
                ptrace_cont(self.pid, 0)
                return

            self.log_event(sig)
            if sig == signal.SIGPIPE:
                ptrace_detach(self.pid)
                os.waitpid(self.pid, 0) #Clean up Zombie
                self.running = False

            elif sig == signal.SIGSEGV:
                self.__capturecore()
                self.__spawn()
            else:
                ptrace_cont(self.pid, sig)

    def run(self):
        self.running = True
        self.__spawn()
        while self.running:
            (pid, status) = os.waitpid(self.pid, 0)
            if not self.running:
                return

            self.eventLock.acquire()
            try:
                self.__handle_event(pid, status)
            finally:
                self.eventLock.release()

    def _ptrace_detach(self, tracer):
        """This cleans up a single process object without trying to delete it from a
        debugger.
        """
        ptrace_detach(self.pid) #bug piptrace doesn't detach when detach is called
        tracer.read_mem_file.close() #bug piptrace does not close file handles


    def _get_symbol_addr(self, symbol):
        """Search the elf file for the main function and return address
        """
        exe = self.service.cmd[0]
        proc = subprocess.Popen(['nm', exe], stdout=subprocess.PIPE, encoding="UTF8")
        main_addr = None
        for line in proc.stdout:
            args = line.split()
            if len(args) < 3:
                continue
            if args[2] == symbol:
                main_addr = int(args[0], 16)
        proc.wait()

        if main_addr == None:
            raise Exception("Could not find symbol 'main' in " + exe)
        return main_addr

    def log_event(self, evtnum):
        if evtnum == 0:
            name = "EXIT"
        elif evtnum in SIGNAL_NAMES:
            name = SIGNAL_NAMES[evtnum]
        else:
            name = str(evtnum)
        if name not in self.service.events:
            self.service.events[name] = 0
        self.service.events[name] += 1
        self.service.fireEvent()

    def __capturecore(self):
        ptrace_detach(self.pid, signal.SIGSTOP) #detach and leave stopped so gcore can attach
        #TODO: put process in a queue to be core dumped later

        #Relying on kernel to create a core file does not work well in a container
        #Use gcore to capture core its a little slower but reliable
        dst = os.path.join(self.service.cores_dir, "core")
        with open(os.devnull, 'w') as devnull:
            try:
                subprocess.call(["gcore", "-o", dst, str(self.pid)], stdout=devnull, stderr=devnull)
            except:
                pass

        os.kill(self.pid, signal.SIGKILL)
        # Wait to cleanup zombie
        os.waitpid(self.pid, 0)
        self.service.cores.append("core." + str(self.pid))

    def stop(self):
        self.running = True
        #Wait for last event to process
        self.eventLock.acquire()
        try:
            #Poke the process to wake up the event thread
            #The pid may be dead already so ignore errors
            os.kill(self.pid, signal.SIGTERM)
        except:
            pass
        self.eventLock.release()

        self.join()
        self.conn.close()

class MasterInstance(Instance):
    def __init__(self, service):
        self.service = service
        self.coverage = service.coverage
        self.__createMaster()

    def __createMaster(self):
        """Creates a master instance that is used as the group owner for a service.  It
        also stops the process before anything is executed so a blank graph can be created
        """
        self.__spawn()
        tracer = PtraceProcess(None, self.pid, True)
        tracer.createBreakpoint(self._get_symbol_addr("main"))
        tracer.cont()

        (pid, ret) = os.waitpid(self.pid, 0) #Wait for breakpoint
        os.kill(self.pid, signal.SIGSTOP) #Leave the master stopped at main
        self._ptrace_detach(tracer)

    def __spawn(self):
        self.pid = os.fork()
        if self.pid == 0:
            # Make GCOV dump into the session_dir
            os.environ['GCOV_PREFIX'] = self.service.gcov_dir
            os.environ['GCOV_PREFIX_STRIP'] = str(service.gcovstrip)
            os.close(sys.stdin.fileno())
            os.close(sys.stderr.fileno())
            os.close(sys.stdout.fileno())

            ptrace_traceme() #force process to stop after exec
            os.execvp(self.service.cmd[0], self.service.cmd)
            raise Exception("Failed to Exec")
        (pid, ret) = os.waitpid(self.pid, 0) #Wait for first trap

    def stop(self):
        os.kill(self.pid, signal.SIGCONT)
        os.kill(self.pid, signal.SIGKILL)
        os.waitpid(self.pid, 0) #Wait for termination
