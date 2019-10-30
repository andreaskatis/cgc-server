class PortChooser():
    def __init__(self, low, high):
        self.freeports = list(range(low, high))
        self.usedports = []

    def get_port(self):
        port = self.freeports.pop()
        self.usedports.append(port)
        return port

    def put_port(self, port):
        port = self.usedports.pop()
        self.freeports.append(port)

