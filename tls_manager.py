import socket
import threading
import time


class tls_manager:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active = False
        self.tls_manager_thread = None
        self.address = "localhost"
        self.port = 12345

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.address, self.port))

    def manage_tls(self, x, y):
        h1 = "lane_VehicleNumber_" + chr(x + 64 - 1) + str(y) + chr(x + 64) + str(y) + "_0"
        h2 = "lane_VehicleNumber_" + chr(x + 64 + 1) + str(y) + chr(x + 64) + str(y) + "_0"
        val_h1 = 0
        val_h2 = 0
        v1 = "lane_VehicleNumber_" + chr(x + 64) + str(y + 1) + chr(x + 64) + str(y) + "_0"
        v2 = "lane_VehicleNumber_" + chr(x + 64) + str(y - 1) + chr(x + 64) + str(y) + "_0"
        val_v1 = 0
        val_v2 = 0
        try:
            self.s.sendall(h1.encode())
            response = self.s.recv(1024)
            val_h1 = int(response.decode())
            self.s.sendall(h2.encode())
            response = self.s.recv(1024)
            val_h2 = int(response.decode())
            self.s.sendall(v1.encode())
            response = self.s.recv(1024)
            val_v1 = int(response.decode())
            self.s.sendall(v2.encode())
            response = self.s.recv(1024)
            val_v2 = int(response.decode())
        except Exception as e:
            print(f"An error occurred in manage_tls: {e}")

        vertical = val_v1 + val_v2
        horizontal = val_h1 + val_h2

        phase_request = "tls_getPhase_" + chr(x + 64) + str(y)
        phase_answer = "tls_setPhase_" + chr(x + 64) + str(y)
        phase = 0

        if horizontal * 0.6 > vertical:
            self.s.sendall(phase_request.encode())
            phase = self.s.recv(1024).decode()
            if phase == "0":
                phase_answer += "_1"
                self.s.sendall(phase_answer.encode())
                response = self.s.recv(1024)
        elif vertical * 0.6 > horizontal:
            self.s.sendall(phase_request.encode())
            phase = self.s.recv(1024).decode()
            if phase == "2":
                phase_answer += "_3"
                self.s.sendall(phase_answer.encode())
                response = self.s.recv(1024)

    def close(self):
        self.s.close()

    def manage(self):
        x = 0
        while self.active:
            time.sleep(0.5)
            x += 1
            #print("Managing tls" + str(x))
            for i in range(2, 9):
                for j in range(2, 9):
                    self.manage_tls(i, j)

    def start(self):
        if self.active:
            return
        else:
            self.active = True
            self.tls_manager_thread = threading.Thread(target=self.manage)
            self.tls_manager_thread.start()

    def stop(self):
        self.active = False
        time.sleep(1)
        self.close()