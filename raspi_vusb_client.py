import socket
import ssl
import threading
import traceback
import queue
import time


class SSLClient:
    def __init__(self, host):
        self.send_thread = None
        self.host, self.port = tuple(host.split(':'))
        self.port = int(self.port)
        self.q = queue.Queue()
        # Create a TCP/IP socket
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.sock = context.wrap_socket(self.sk, server_hostname="testserver.com")
        
        self.is_running = False

    def send_loop(self):
        print(f'TCP connect to {self.host}:{self.port}')
        self.sock.settimeout(5)
        try:
            self.sock.connect((self.host, self.port))
        except:
            traceback.print_exc()
            print('TCP connection failed.')
            self.sock.close()
            return

        print('TCP send_loop start')
        self.is_running = True
        self.sock.settimeout(0.1)

        while self.is_running:
            try:
                if not self.q.empty():
                    data = self.q.get()
                    self.sock.send(data)
                    # print(f'TCP send: {data}')
                    # print("jb")
                    # data = self.sock.recv(1)  # 接收数据和返回地址
                    # dec_d = data.decode(encoding='ascii')
                    # print(f'TCP received: {data}')
                time.sleep(1e-1)
            except socket.timeout:
                pass
            except:
                traceback.print_exc()
                break
        self.is_running = False
        self.sock.close()
        self.sk.close()
        print('TCP send_loop done')

    def start_loop(self):
        self.send_thread = threading.Thread(target=SSLClient.send_loop, args=(self,))
        self.send_thread.start()

    def stop_loop(self):
        self.is_running = False
        self.send_thread.join()

    def send(self, msg):
        self.q.put(msg)
        return 0
        
        
        
class VUSBClient:
    def __init__(self, _config):
        self.host = _config['host']
        self.tcp = SSLClient(self.host)

    def __enter__(self):
        self.tcp.start_loop()
        return self
        
    def __exit__(self, *args):
        self.tcp.stop_loop()
        
    def mouse_move(self, nx, ny, relative=False):
        # protocal: https://stackoverflow.com/questions/57987969/raspberry-pi-zero-turned-into-a-virtual-mouse-is-not-working-properly-on-windo
        if relative:
            def move_rel(dx, dy):
                def flip_neg(val):
                    return val + 256 if val < 0 else val
                return [0, flip_neg(dx), flip_neg(dy), 0, 0, 0]

            dl = max(abs(nx), abs(ny)) # 移动最长的像素
            if dl == 0:
                return 0
            rel = 127 # 每次最长移动
            num_of_loop = abs(dl) // rel + 1
            # 计算每次移动的量
            def get_diff_list(df):
                if num_of_loop == 0:
                    return [df]
                l = [df // num_of_loop if df >= 0 else -((-df) // num_of_loop)] * num_of_loop
                res = df - l[0] * num_of_loop # 还差res个像素
                if res < 0:
                    for i in range(-res):
                        l[i] -= 1
                else:
                    for i in range(res):
                        l[i] += 1
                return l
            dxl = get_diff_list(nx)
            dyl = get_diff_list(ny)
            for dxi, dyi in zip(dxl, dyl):
                if self.send_mouse_event(move_rel(dxi, dyi), relative):
                    return 1
                time.sleep(5e-2)
            return 0
        else:
            dt = [0xff & nx, (0xff00 & nx) >> 8, 0xff & ny, (0xff00 & ny) >> 8] + [0] * 6
            return self.send_mouse_event(dt, relative)
        
    def mouse_press(self, button=0):
        # button 0: left, 1:right, 2:center
        relative = True
        dt = [0x01 << button, 0, 0, 0]
        return self.send_mouse_event(dt, relative)
        
    def send_mouse_event(self, dt, relative=False):
        dt_len = len(dt)
        if dt_len == 0:
            # no data
            return 1
        db = [0x06 if relative else 0x07] + dt
        # pkt: byte0-3: packet length, byte4: relative, byte5-10
        pkt = [len(db), 0, 0, 0] + db
        # print(pkt)
        return self.send_data(pkt)
        
    def send_data(self, pkt):
        pkb = bytes(pkt)
        # print(pkb)
        return self.tcp.send(pkb)
        

if __name__ == '__main__':
    config = {
        'host': '192.168.0.81:19509',
    }
    
    with VUSBClient(config) as v:
        while True:
            v.mouse_move(-10, 10, True)
            time.sleep(1)
            v.mouse_move(10, -10, True)
            time.sleep(1)
            v.mouse_press(0)
            time.sleep(1)