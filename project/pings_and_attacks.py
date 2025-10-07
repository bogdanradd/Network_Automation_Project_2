"""This module is used to define every attack"""

import subprocess
import threading
import time

REMOTE = 'osboxes@192.168.201.100'
SSH_KEY = "/home/osboxes/.ssh/guest2_ed25519"
IPS = ["192.168.201.1",
       "192.168.201.100",
       "192.168.202.1",
       "192.168.202.2",
       "192.168.203.2",
       "192.168.203.3",
       "192.168.204.3",
       "192.168.204.4",
       "192.168.205.100", ]
SSH_IPS = ['192.168.201.1',
           '192.168.202.2',
           '192.168.203.3', ]


def test_ssh_acl(ip):
    """This method is used to try the SSH ACL made on given IP"""
    ssh_acl = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'ssh', '-l', 'admin', ip
        ],
        capture_output=True,
        text=True,
    )
    for line in ssh_acl.stderr.splitlines():
        if 'stdin' not in line:
            print(line)


def ping(ip):
    """This method is used to launch a basic ping to a given IP"""
    p = subprocess.run(['ping', '-c', '2', ip],
                       capture_output=True,
                       text=True)
    print(p.stdout)


def run_ping_1():
    """This method is used to send a ping from the main container to DockerGuest-1"""
    with (subprocess.Popen(['ping', '-c', '15', '192.168.205.100'],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           stdin=subprocess.PIPE,
                           text=True,
                           )
    ) as p:
        for line in p.stdout:
            print(line, end='')
        p.wait()


def run_ping_2():
    """This method is used to send a ping from Attacker to DockerGuest-1"""
    dos = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'ping', '-c', '2', '192.168.205.100'
        ],
        capture_output=True,
        text=True,
    )
    print(dos.stdout)


def run_nmap():
    """This method is used to launch a nmap from Attacker to DockerGuest-1"""
    nmap = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'sudo', '-n', 'nmap', '-sS', '--top-ports', '5', '-T5', '192.168.205.100',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    print(nmap.stdout)


def run_dos():
    """This method is used to launch a DoS attack from Attacker to DockerGuest-1"""
    dos = subprocess.run(
        [
            'ssh',
            '-i', SSH_KEY,
            '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=no',
            REMOTE,
            'sudo', '-n', 'timeout', '10s', 'hping3', '-S', '-p', '80', '--flood', '-q', '192.168.205.100',
        ],
        capture_output=True,
        text=True,
    )
    print(dos.stdout)
    print(dos.stderr)


def ping_and_dos():
    """This method combines both PING and DoS and runs them in separate Threads"""
    t1 = threading.Thread(target=run_ping_1)
    t2 = threading.Thread(target=run_dos)
    t1.start()
    time.sleep(3.5)
    print("Incoming DOS...")
    t2.start()
    t1.join()
    t2.join()


def run_all_pings():
    """This method is used to PING every device from main container"""
    threads = []
    for ip in IPS:
        t = threading.Thread(target=ping, args=(ip,))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_all_ssh_acl():
    """This method is used to test the SSH ACL made on IOU1, IOSv and CSR"""
    threads = []
    for ip in SSH_IPS:
        t = threading.Thread(target=test_ssh_acl, args=(ip,))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
