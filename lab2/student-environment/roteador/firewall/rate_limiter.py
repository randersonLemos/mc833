import time
from scapy.all import TCP, Ether

# Global dictionaries to track state
syn_history = {}
blacklist = {}
ban_records = {}

# Configuration
THRESHOLD = 15
WINDOW_SIZE = 2.0
BAN_TIERS = [60.0, 600.0, 3600.0, 86400.0]
BORDER = "-" * 60


def filter_packet(pkt):
    """
    Filters packets based on frequency. Implements escalating bans for repeat offenders based on MAC Address (Layer 2).
    """
    # If there is no Ethernet layer, we cannot get a MAC address, so let it pass
    if Ether not in pkt:
        return True

    src_mac = pkt[Ether].src
    current_time = time.time()

    # 1. CHECK THE BLACKLIST FIRST
    if src_mac in blacklist:
        if current_time < blacklist[src_mac]:
            unban_time_str = time.ctime(blacklist[src_mac])
            print(BORDER)
            print("[RATE LIMITER] DROPPED Banned Traffic!")
            print(f"   Reason: Source MAC is currently serving a ban.")
            print(f"   Details: {src_mac} is banned until {unban_time_str}")
            print(BORDER)
            return False
        else:
            print(BORDER)
            print("[RATE LIMITER] MAC UNBANNED")
            print(f"   Details: {src_mac} has served its time and is now allowed.")
            print(BORDER)
            del blacklist[src_mac]
            if src_mac in syn_history:
                del syn_history[src_mac]

    # Only track TCP SYN packets for the rate limit
    if TCP not in pkt or pkt[TCP].flags != "S":
        return True

    # 2. TRACK CONNECTION ATTEMPTS (SYN FLAGS)
    if src_mac not in syn_history:
        syn_history[src_mac] = []

    syn_history[src_mac].append(current_time)
    syn_history[src_mac] = [t for t in syn_history[src_mac] if current_time - t <= WINDOW_SIZE]

    # 3. ENFORCE RATE LIMIT AND ESCALATING BAN
    if len(syn_history[src_mac]) > THRESHOLD:
        ban_records[src_mac] = ban_records.get(src_mac, 0) + 1
        tier_index = min(ban_records[src_mac] - 1, len(BAN_TIERS) - 1)
        current_ban_duration = BAN_TIERS[tier_index]
        unban_time = current_time + current_ban_duration
        blacklist[src_mac] = unban_time
        unban_time_str = time.ctime(unban_time)

        print(BORDER)
        print("[RATE LIMITER] BLACKLISTED Source MAC!")
        print(f"   Reason: Exceeded {THRESHOLD} connections in {WINDOW_SIZE}s (Strike #{ban_records[src_mac]}).")
        print(f"   Details: Banning {src_mac} for {current_ban_duration:.1f}s | Unban at: {unban_time_str}")
        print(BORDER)
        return False

    return True