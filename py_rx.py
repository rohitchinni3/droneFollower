import zmq
from enum import Enum
import threading
import time
from gps import *
import math
import csv
import paramiko
from scp import SCPClient

class Results(Enum):
    Failure = 0
    Success = 1

def decoded(s):
    return int.from_bytes(s, 'little')

def encoded(value, length):
    return value.to_bytes(length, 'little')

class Integer8():
    def __init__(self):
        self.value = None

    def encode(self):
        if self.value is None:
            return None
        return encoded(self.value, 1)

    def decode(self, s):
        self.value = decoded(s[:1])
        return s[1:]

class Integer16():
    def __init__(self):
        self.value = None

    def encode(self):
        return encoded(self.value, 2)

    def decode(self, s):
        self.value = decoded(s[:2])
        return s[2:]

class Integer32():
    def __init__(self):
        self.value = None

    def encode(self):
        out = encoded(self.value, 4)
        return out

    def decode(self, s):
        self.value = decoded(s[:4])
        return s[4:]

class Integer48():
    def __init__(self):
        self.value = None

    def encode(self):
        return encoded(self.value, 6)

    def decode(self, s):
        self.value = s[:6].hex()
        return s[6:]

def sdecoded(s):
    return int.from_bytes(s, 'little', signed=True)

class SInteger8():
    def __init__(self):
        self.value = None

    def decode(self, s):
        self.value = sdecoded(s[:1])
        return s[1:]

class Opaque():
    def __init__(self):
        self.value = None

    def encode(self):
        out = self.value.encode('utf-8')
        return out

class wsmp_hle():
    def __init__(self):
        self.wsmp_version = Integer8()
        self.channel_no = Integer8()
        self.data_rate = Integer8()
        self.tx_pow_level = SInteger8()
        self.channel_load = Integer8()
        self.user_priority = Integer8()
        self.peer_mac_addr = Integer48()
        self.psid = Integer32()
        self.dlen = Integer16()
        self.data = None

    def decode(self, s):
        ret_ver = self.wsmp_version.decode(s)
        ret_chh = self.channel_no.decode(ret_ver)
        ret_dr = self.data_rate.decode(ret_chh)
        ret_txpow = self.tx_pow_level.decode(ret_dr)
        ret_chld = self.channel_load.decode(ret_txpow)
        ret_usr_prio = self.user_priority.decode(ret_chld)
        ret_peer = self.peer_mac_addr.decode(ret_usr_prio)
        ret_psid = self.psid.decode(ret_peer)
        ret_len = self.dlen.decode(ret_psid)
        self.data = ret_len[:self.dlen.value]

class Action(Enum):
    Add = 1
    Delete = 2

class wme_sub():
    def __init__(self):
        self.action = Integer8()
        self.psid = Integer32()
        self.appname = Opaque()

    def encode(self):
        out = self.action.encode() + self.psid.encode() + self.appname.encode()
        return out

def Wme_operation():
    wme_context = zmq.Context()
    wme_socket = wme_context.socket(zmq.REQ)
    wme_socket.connect("tcp://localhost:9999")

    psid_sub_mag = wme_sub()
    psid_sub_mag.action.value = Action.Add.value
    psid_sub_mag.psid.value = 32
    psid_sub_mag.appname.value = "RX_APPLICATION"
    out = psid_sub_mag.encode()
    wme_socket.send(out)
    cmh_recv_msg = wme_socket.recv()
    print("psid 32 subscribed to wme")

def getPositionData(gps):
    nx = gpsd.next()
    if nx['class'] == 'TPV':
        latitude = getattr(nx, 'lat', 'Unknown')
        longitude = getattr(nx, 'lon', 'Unknown')
        speed = getattr(nx, 'speed', 'unknown')
        gps_data = [latitude, longitude, speed]
        return gps_data

gpsd = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)

def get_heading(aLocation):
    off_x = aLocation[-1][1] - aLocation[-2][1]
    off_y = aLocation[-1][0] - aLocation[-2][0]
    heading = 90.00 + math.atan2(-off_y, off_x) * 57.2957795
    if heading < 0:
        heading += 360.00
    return heading

def get_cartesian(lat=None, lon=None):
    lat, lon = math.radians(lat), math.radians(lon)
    R = 6371  # radius of the earth
    x = R * math.cos(lat) * math.cos(lon)
    y = R * math.cos(lat) * math.sin(lon)
    z = R * math.sin(lat)
    return x, y, z

def distance(x1, y1, z1, x2, y2, z2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

def create_ssh_client(server, port, user, password):
    """
    Creates an SSH client connection to the remote Raspberry Pi.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

def scp_file(local_file, remote_path, raspberry_pi_ip, raspberry_pi_user, raspberry_pi_password):
    """
    Transfers the CSV file to the Raspberry Pi using SCP.
    """
    ssh = create_ssh_client(raspberry_pi_ip, 22, raspberry_pi_user, raspberry_pi_password)
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_file, remote_path)
    ssh.close()

#########################################
def Wsmp_operation():
    wsmp_context = zmq.Context()
    wsmp_socket = wsmp_context.socket(zmq.SUB)
    wsmp_socket.connect("tcp://localhost:4444")
    wsmp_socket.setsockopt(zmq.SUBSCRIBE, b"32")
    x_self = 0.0
    y_self = 0.0
    z_self = 0.0
    x_rec = 0.0
    y_rec = 0.0
    z_rec = 0.0
    latitude_self = 0.0
    longitude_self = 0.0
    latitude_rec = 0.0
    longitude_rec = 0.0
    speed_self = 0.0
    dist = 0.0
    head_self = 0.0
    head_rec = 0.0
    aLocation = [[0, 0]]
    pos_time_self = [[]]
    pos_time_rec = [[]]

    # Open the CSV file in append mode
    with open('gps_data.csv', 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        
        # Write the header only if the file is empty
        if csvfile.tell() == 0:
            csvwriter.writerow(['Timestamp', 'Latitude', 'Longitude', 'Speed', 'Heading Angle'])
        
        while True:
            message = wsmp_socket.recv()
            gps_data = getPositionData(gpsd)
            if gps_data is not None:
                latitude_self = gps_data[0]
                longitude_self = gps_data[1]
                speed_self = gps_data[2]
                x_self, y_self, z_self = get_cartesian(latitude_self, longitude_self)
                pos_time_self.append([x_self, y_self, z_self])
                aLocation.append([latitude_self, longitude_self])
                head_self = get_heading(aLocation)
                
            if message != b'32':
                rx = message.decode('utf-8', errors='ignore')
                rx_clean = rx[18:]
                print("Received data: ", rx_clean)
                inp = rx_clean.split(',')
                for pair in inp:
                    k, v = pair.split(':')
                    if k == 'speed':
                        flo = float(v)
                    elif k == 'latitude':
                        latitude_rec = float(v)
                    elif k == 'longitude':
                        longitude_rec = float(v)
                    elif k == 'heading_angle':
                        head_rec = float(v)

                x_rec, y_rec, z_rec = get_cartesian(latitude_rec, longitude_rec)
                dist = distance(x_self, y_self, z_self, x_rec, y_rec, z_rec)

                # Save the received data to the CSV file
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                csvwriter.writerow([timestamp, latitude_rec, longitude_rec, flo, head_rec])
                csvfile.flush()  # Ensure the data is written to the file

                # Transfer the CSV file to the Raspberry Pi using SCP
                scp_file(
                    local_file='gps_data.csv',
                    remote_path='/home/pi/Desktop/cv2x/new/gps_data.csv',  # Adjust the remote path as needed
                    raspberry_pi_ip='192.168.1.9',  # Replace with your Raspberry Pi IP address
                    raspberry_pi_user='pi',  # Replace with your Raspberry Pi username
                    raspberry_pi_password='raspberry'  # Replace with your Raspberry Pi password
                )

#########################################

if __name__ == '__main__':
    thread_wsmp = threading.Thread(target=Wsmp_operation)
    thread_wsmp.start()
