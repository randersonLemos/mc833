import time
from scapy.all import TCP, IP

# Global dictionaries to track state
syn_history = {}
blacklist = {}
ban_records = {}

# Configuration
THRESHOLD = 10
WINDOW_SIZE = 2.0
BAN_TIERS = [60.0, 600.0, 3600.0, 86400.0]
BORDER = "-" * 60

def filter_packet(pkt):
    """
    Filters packets based on frequency. Implements escalating bans for repeat offenders.
    """
    if IP not in pkt:
        return True

    src_ip = pkt[IP].src
    current_time = time.time()

    # 1. CHECK THE BLACKLIST FIRST
    if src_ip in blacklist:
        if current_time < blacklist[src_ip]:
            unban_time_str = time.ctime(blacklist[src_ip])
            print(BORDER)
            print("[RATE LIMITER] DROPPED Banned Traffic!")
            print(f"   Reason: Source IP is currently serving a ban.")
            print(f"   Details: {src_ip} is banned until {unban_time_str}")
            print(BORDER)
            return False
        else:
            print(BORDER)
            print("[RATE LIMITER] IP UNBANNED")
            print(f"   Details: {src_ip} has served its time and is now allowed.")
            print(BORDER)
            del blacklist[src_ip]
            if src_ip in syn_history:
                del syn_history[src_ip]

    if TCP not in pkt or pkt[TCP].flags != "S":
        return True

    # 2. TRACK CONNECTION ATTEMPTS (SYN FLAGS)
    if src_ip not in syn_history:
        syn_history[src_ip] = []
    
    syn_history[src_ip].append(current_time)
    syn_history[src_ip] = [t for t in syn_history[src_ip] if current_time - t <= WINDOW_SIZE]

    # 3. ENFORCE RATE LIMIT AND ESCALATING BAN
    if len(syn_history[src_ip]) > THRESHOLD:
        ban_records[src_ip] = ban_records.get(src_ip, 0) + 1
        tier_index = min(ban_records[src_ip] - 1, len(BAN_TIERS) - 1)
        current_ban_duration = BAN_TIERS[tier_index]
        unban_time = current_time + current_ban_duration
        blacklist[src_ip] = unban_time
        unban_time_str = time.ctime(unban_time)

        print(BORDER)
        print("[RATE LIMITER] BLACKLISTED Source IP!")
        print(f"   Reason: Exceeded {THRESHOLD} connections in {WINDOW_SIZE}s (Strike #{ban_records[src_ip]}).")
        print(f"   Details: Banning {src_ip} for {current_ban_duration:.1f}s | Unban at: {unban_time_str}")
        print(BORDER)
        return False

    return True
