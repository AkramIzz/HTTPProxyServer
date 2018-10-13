import socket, select
import ssl

class ProxyServer:
    def __init__(self, addr, filter = None, backlog = 5):
        if type(addr) is not tuple:
            raise TypeError(
                'AF_INET address must be tuple, not {}'.format(type(addr)))
        elif len(addr) != 2:
            raise TypeError('AF_INET address consists of host and port only')
        elif type(filter) is not list:  raise TypeError(
            'filter must be list, not {}'.format(type(filter)))
        if filter:  self.filter = filter
        else:   self.filter = []
        self.s = socket.socket()
        self.s.bind(addr)
        self.s.listen(backlog)
        self.buffer_size = 65536
        self.timeout = 0
        self.p_readers = [self.s]
        self.connections = {}
        self.extendFilter()

    def close(self):
        for s in self.connections:
            self.closeSocket(self.connections[s])
        for s in self.p_readers:
            self.closeSocket(s)

    def extendFilter(self):
        for host in self.filter[:]:
            self.filter.append(socket.gethostbyname(host))
            self.filter.remove(host)

    def closeSocket(self,c):
        if c == None:   return
        c.close()
        try:    self.p_readers.remove(c)
        except: pass
        del c
        
    def serve_forever(self):
        print('[+] Accepting connections on {}:{}'.format(*self.s.getsockname()))
        while True:
            readers = select.select(self.p_readers, [], [], self.timeout)[0]
            for s in readers:
                if str(s).find('[closed]') > -1:    continue
                
                if s == self.s:
                    c, ca = s.accept()
                    print('[+] Accepted connection from {}:{}'.format(*ca))
                    self.p_readers.append(c)
                    self.connections[c] = None
                elif s in self.connections.keys():
                    data = s.recv(self.buffer_size)
                    if len(data) == 0:
                        self.closeSocket(self.connections.get(s))
                        self.closeSocket(s)
                        print('[+] Connection closed by client')
                        break
                    print('[+] Recieved data')
                    host, port = self.getRequestedAddr(data)
                    c_server = self.connections.get(s)
                    if host and port:
                        try:
                            if socket.gethostbyname(host) in self.filter:
                                print('[-] Request Denied')
                                self.closeSocket(s)
                                continue
                        except: pass
                        print(host, port)
                        c_server = socket.socket()
                        try:
                            c_server.connect((host, port))
                        except Exception as e:
                            print('[-]', e)
                            c_server.close()
                            break
                        c_server.send(data)
                        self.p_readers.append(c_server)
                        if self.connections.get(s):
                            self.closeSocket(self.connections.get(s))
                        self.connections[s] = c_server
                        print('[+] Created connection, Data sent')
                    elif c_server:
                        c_server.send(data)
                        print('[+] No new connection, Data sent')
                        
                else:
                    data = s.recv(self.buffer_size)
                    for t in self.connections:
                        if self.connections[t] == s:
                            if len(data) == 0:
                                self.closeSocket(s)
                                self.closeSocket(t)
                                print('[+] Connection closed by server')
                            else:
                                t.send(data)
                                print('[+] Recieved data, Data sent')
                            break

    def getRequestedAddr(self, data):
        webserver, port = None, None

        first_line = data.split(b'\r\n')[0]
        if first_line.find(b'GET ') == -1:
           return webserver, port
        url = first_line.split(b' ')[1]

        http_pos = url.find(b'://')
        temp = url
        if http_pos > -1:
            temp = url[(http_pos+3):]

        webserver_pos = temp.find(b'/')
        if webserver_pos == -1:
            webserver_pos = len(temp)

        port_pos = temp.find(b':')

        webserver = ''
        port = -1
        if port_pos == -1 or webserver_pos < port_pos:
            port = 80
            webserver = temp[:webserver_pos]
        else:
            port = int(temp[ (port_pos+1) : (webserver_pos-port_pos-1) ])
            webserver = temp[:port_pos]

        return webserver, port

if __name__ == '__main__':
    socket.setdefaulttimeout(3)
    port = int(input('Enter Proxy Server port number: '))
    filter_file = input('Enter filtered sites file: ')
    filter = []
    if filter_file:
        with open(filter_file) as f:
            for l in f:
                filter.append(l.strip())

    server = ProxyServer(('', port), filter)
    try:
        server.serve_forever()
    except Exception as e:
        print(e)
        server.close()
