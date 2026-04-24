from scapy.all import *
import subprocess
import re

def sniff_for_syn_ack(target_ip, server_ip, client_port, interface="eth0", timeout=10):
    """
    Sniffs for a SYN/ACK packet using tcpdump and parses the output to get the ISN.
    """
    print(f"--- Sniffing for SYN/ACK using tcpdump ---")
    
    # BPF filter to capture the SYN/ACK packet
    filter_str = f"src host {target_ip} and dst host {server_ip} and tcp port {client_port} and (tcp[tcpflags] & (tcp-syn|tcp-ack)) == (tcp-syn|tcp-ack)"
    
    # Command to run tcpdump
    command = [
        "tcpdump",
        "-i", interface,
        "-l",  # Line-buffer output
        "-n",  # Don't resolve hostnames
        "-c", "1", # Capture only one packet
        filter_str
    ]
    
    print(f"[+] Running tcpdump with filter: \"{filter_str}\"")

    try:
        # Start tcpdump and capture its output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=timeout)

        if process.returncode != 0 and not stdout:
            print(f"[-] tcpdump exited with error or timed out. Stderr: {stderr.strip()}")
            return None

        # Regex to find the sequence number in the tcpdump output
        # Example output: ... seq 123456789, ...
        match = re.search(r"seq (\d+),", stdout)
        if not match:
            print("[-] Could not find sequence number in tcpdump output.")
            print(f"    Output was: {stdout.strip()}")
            return None

        target_isn = int(match.group(1))
        print(f"\n[+] Captured SYN/ACK packet. Target's ISN is: {target_isn}")
        return target_isn

    except subprocess.TimeoutExpired:
        print("\n[-] Sniffer timed out. No matching SYN/ACK packet was captured.")
        process.kill()
        return None
    except Exception as e:
        print(f"An error occurred during sniffing: {e}")
        return None
