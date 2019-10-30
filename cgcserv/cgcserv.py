import signal, os
import sys
import time
import argparse
import fnmatch
import shutil
import time
import json
import logging
import coverage
from threading import Thread
from service import Service,serviceFactory

logger = logging.getLogger("cgcserv")

def stop_service(service):
    service.stop()

def main():
    parser = argparse.ArgumentParser(description="cgcserv")
    parser.add_argument('-p', '--port', required=False,
            help="Port to listen for connections")
    parser.add_argument('-s', '--service', required=True,
            help="Quoted application to run")
    parser.set_defaults(port=5040)
    args = parser.parse_args()
    s = Service(args.service.split(), args.port)
    atexit.register(remove_service, s)
    s.start()

if __name__ == "__main__":
    sys.exit(main())
