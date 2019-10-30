#!/usr/bin/env python3
import socketio
import time

class CGC_Event_Handler(socketio.ClientNamespace):
    
    def __init__(self,client):
        super().__init__('')
        self.client = client
    
    def on_sessions(self,data):
        print('on session')
    
    def on_start(self,data):
        sid = data.get('id',None)
        if sid:
            self.client.sid = sid
            print("CGC Client: {} service {} started.".format(self.client.service,self.client.sid))
            self.client.emit('join',{'sid' : sid})
    
    def on_stop(self,data):
        print("CGC Client: {} service {} stopped.".format(self.client.service,self.client.sid))
        self.client.sid = None
        self.client.disconnect()
    
    def on_join(self,data):
        print("CGC Client: {} service {} monitored.".format(self.client.service,self.client.sid))
    
    def on_events(self,data):
        events = data.get('events',None)
        self.client.processEvent(events)
    
    def on_error(self,data):
        print("CGC Client: Error: {}".format(str(data)))
    
    def on_connect(self):
        print("CGC Client: connected to {}".format(self.client.server))
        self.client.emit('start',{'service' : self.client.service})

class CGC_Client(socketio.Client):
    
    def __init__(self,server,interface):
        super().__init__()
        self.server  = server
        self.service = None
        self.sid     = None
        self.interface = interface
        self.register_namespace(CGC_Event_Handler(client=self))
        self.events  = None
    
    def start(self,service):
        if not self.sid:
            self.service = service
            print("CGC Client: {} service starting .. ".format(self.service))
            self.connect(self.server)
        else:
            print("CGC Client: **ERROR** still running {}.".format(self.service))
    
    def stop(self):
        if self.sid:
            print("CGC Client: {} service {} stopping .. ".format(self.service,self.sid))
            self.emit('stop',{'sid' : self.sid})
        else:
            print("CGC Client: **ERROR** already stopped.")
    
    def processEvent(self,events):
        if not self.events:
            self.events = events
            return
        if events:
            pass
    
    def trigger(self):
        print("CGC Client: {} service {} triggered".format(self.service,self.sid))
        if self.interface:
            self.interface.capture()

def main():
    client = CGC_Client(server="http://localhost:5000",interface=None)
    client.start("PTaaS")
    time.sleep(10)
    client.stop()

if __name__ == '__main__':
    main()
