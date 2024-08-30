import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("localhost", 9879))
s.listen(1)
conn, addr = s.accept()
print('Connected by', addr)
while 1:
    data = conn.recv(1024)
    # print(str(data))
    if not data: break
conn.close()
