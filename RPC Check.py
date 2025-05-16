import requests
import time

def measure_rps(func, rpc_url, num_requests=20):
    success_count = 0
    start = time.time()
    for _ in range(num_requests):
        try:
            func(rpc_url, silent=True)
            success_count += 1
        except Exception:
            # Ignore failures in burst test
            pass
    end = time.time()
    duration = end - start
    if duration > 0:
        rps = success_count / duration
        print(f"[+] Successful requests: {success_count}/{num_requests} in {duration:.2f}s -> RPS: {rps:.2f}")
    else:
        print("[!] Duration too short to measure RPS")

def check_evm_rpc(rpc_url, silent=False):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }
    response = requests.post(rpc_url, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    block_number = data.get('result')
    if block_number:
        if not silent:
            print(f"[+] EVM RPC is online. Current block number: {int(block_number, 16)}")
    else:
        if not silent:
            print("[-] No block number in response.")
        raise Exception("No block number in response")

def check_beacon_rpc(rpc_url, silent=False):
    endpoint = f"{rpc_url.rstrip('/')}/eth/v1/beacon/states/head/finality_checkpoints"
    response = requests.get(endpoint, timeout=10)
    response.raise_for_status()
    data = response.json()
    block_root = data.get('data', {}).get('finalized', {}).get('root')
    if block_root:
        if not silent:
            print(f"[+] Beacon chain RPC is online. Finalized block root: {block_root}")
    else:
        if not silent:
            print("[-] No finalized block root in response.")
        raise Exception("No finalized block root in response")

def check_solana_rpc(rpc_url, silent=False):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSlot",
        "params": []
    }
    response = requests.post(rpc_url, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    slot = data.get('result')
    if slot is not None:
        if not silent:
            print(f"[+] Solana RPC is online. Current slot: {slot}")
    else:
        if not silent:
            print("[-] No slot info in response.")
        raise Exception("No slot info in response")

def check_aptos_rpc(rpc_url, silent=False):
    endpoint = f"{rpc_url.rstrip('/')}/"
    response = requests.get(endpoint, timeout=10)
    response.raise_for_status()
    data = response.json()
    ledger_version = data.get('ledger_version') or data.get('ledger_info', {}).get('version')
    if ledger_version is not None:
        if not silent:
            print(f"[+] Aptos RPC is online. Ledger version: {ledger_version}")
    else:
        alt_endpoint = f"{rpc_url.rstrip('/')}/v1"
        response2 = requests.get(alt_endpoint, timeout=10)
        response2.raise_for_status()
        data2 = response2.json()
        ledger_version2 = data2.get('ledger_version') or data2.get('ledger_info', {}).get('version')
        if ledger_version2 is not None:
            if not silent:
                print(f"[+] Aptos RPC is online. Ledger version: {ledger_version2}")
        else:
            if not silent:
                print("[-] No ledger version info in response.")
            raise Exception("No ledger version info in response")

def check_sui_rpc(rpc_url, silent=False):
    payload = {
        "jsonrpc": "2.0",
        "method": "sui_getLatestCheckpointSequenceNumber",
        "params": [],
        "id": 1
    }
    response = requests.post(rpc_url, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    checkpoint = data.get('result')
    if checkpoint is not None:
        if not silent:
            print(f"[+] Sui RPC is online. Latest checkpoint sequence number: {checkpoint}")
    else:
        if not silent:
            print("[-] No checkpoint info in response.")
        raise Exception("No checkpoint info in response")

def auto_detect_chain(rpc_url):
    rpc_lower = rpc_url.lower()
    # Keywords map to chain type choices
    if any(k in rpc_lower for k in ['aptos', 'apt']):
        return '4'  # Aptos
    if any(k in rpc_lower for k in ['sui']):
        return '5'  # Sui
    if any(k in rpc_lower for k in ['sol', 'solana']):
        return '3'  # Solana
    if any(k in rpc_lower for k in ['beacon', 'consensus']):
        return '2'  # Beacon chain
    if any(k in rpc_lower for k in ['ethereum', 'eth', 'rpc', 'bsc', 'polygon', 'matic']):
        # EVM generic keywords, fallback
        return '1'  # EVM execution layer
    return None

def manual_chain_prompt():
    print("\nUnable to detect chain automatically.")
    print("Please select the chain type manually:")
    print("1. EVM execution layer (Ethereum, BSC, Polygon, etc.)")
    print("2. Beacon chain (Ethereum consensus layer)")
    print("3. Solana")
    print("4. Aptos")
    print("5. Sui")
    choice = input("Enter choice [1-5]: ").strip()
    return choice

def main():
    print("Enter the RPC URL to check:")
    rpc_url = input().strip()

    detected_choice = auto_detect_chain(rpc_url)
    if detected_choice:
        print(f"\nDetected chain type based on RPC URL: {detected_choice}")
    else:
        detected_choice = manual_chain_prompt()

    check_funcs = {
        '1': check_evm_rpc,
        '2': check_beacon_rpc,
        '3': check_solana_rpc,
        '4': check_aptos_rpc,
        '5': check_sui_rpc
    }

    check_func = check_funcs.get(detected_choice)
    if not check_func:
        print("Invalid choice. Exiting.")
        return

    print("\nChecking RPC availability...")
    try:
        check_func(rpc_url)
    except Exception as e:
        print(f"[-] RPC check failed or offline: {e}")
        # Ask manual chain selection on failure if auto detected first
        if detected_choice != manual_chain_prompt():
            print("\nTrying manual chain selection due to failure.")
            choice = manual_chain_prompt()
            check_func = check_funcs.get(choice)
            if not check_func:
                print("Invalid choice. Exiting.")
                return
            try:
                check_func(rpc_url)
            except Exception as e2:
                print(f"[-] RPC check failed again: {e2}")
                return
        else:
            return

    print("\nMeasuring requests per second (RPS)... This may take a few seconds.")
    measure_rps(check_func, rpc_url, num_requests=20)

if __name__ == "__main__":
    main()
