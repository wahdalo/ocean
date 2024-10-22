import os
import glob
import yaml
import json
import copy

DEFAULT_RPCS = {
    "1": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "fallbackRPCs": [
            "https://rpc.ankr.com/eth",
            "https://1rpc.io/eth",
            "https://eth.api.onfinality.io/public"
        ],
        "chainId": 1,
        "network": "mainnet",
        "chunkSize": 100
    },
    "10": {
        "rpc": "https://mainnet.optimism.io",
        "fallbackRPCs": [
            "https://optimism-mainnet.public.blastapi.io",
            "https://rpc.ankr.com/optimism",
            "https://optimism-rpc.publicnode.com"
        ],
        "chainId": 10,
        "network": "optimism",
        "chunkSize": 100
    },
    "137": {
        "rpc": "https://polygon-rpc.com/",
        "fallbackRPCs": [
            "https://polygon-mainnet.public.blastapi.io",
            "https://1rpc.io/matic",
            "https://rpc.ankr.com/polygon"
        ],
        "chainId": 137,
        "network": "polygon",
        "chunkSize": 100
    },
    "23294": {
        "rpc": "https://sapphire.oasis.io",
        "fallbackRPCs": [
            "https://1rpc.io/oasis/sapphire"
        ],
        "chainId": 23294,
        "network": "sapphire",
        "chunkSize": 100
    },
    "23295": {
        "rpc": "https://testnet.sapphire.oasis.io",
        "chainId": 23295,
        "network": "sapphire-testnet",
        "chunkSize": 100
    },
    "11155111": {
        "rpc": "https://eth-sepolia.public.blastapi.io",
        "fallbackRPCs": [
            "https://1rpc.io/sepolia",
            "https://eth-sepolia.g.alchemy.com/v2/{API_KEY}"
        ],
        "chainId": 11155111,
        "network": "sepolia",
        "chunkSize": 100
    },
    "11155420": {
        "rpc": "https://sepolia.optimism.io",
        "fallbackRPCs": [
            "https://endpoints.omniatech.io/v1/op/sepolia/public",
            "https://optimism-sepolia.blockpi.network/v1/rpc/public"
        ],
        "chainId": 11155420,
        "network": "optimism-sepolia",
        "chunkSize": 100
    }
}

CUSTOM_RPCS_TEMPLATE = {
    "1": {
        "rpc": "https://eth-mainnet.g.alchemy.com/v2/{API_KEY}",
        "fallbackRPCs": [
            "https://rpc.ankr.com/eth",
            "https://1rpc.io/eth"
        ],
        "chainId": 1,
        "network": "mainnet",
        "chunkSize": 100
    },
    "10": {
        "rpc": "https://opt-mainnet.g.alchemy.com/v2/{API_KEY}",
        "fallbackRPCs": [
            "https://optimism-mainnet.public.blastapi.io",
            "https://rpc.ankr.com/optimism",
            "https://optimism-rpc.publicnode.com"
        ],
        "chainId": 10,
        "network": "optimism",
        "chunkSize": 100
    },
    "137": {
        "rpc": "https://polygon-mainnet.g.alchemy.com/v2/{API_KEY}",
        "fallbackRPCs": [
            "https://polygon-mainnet.public.blastapi.io",
            "https://1rpc.io/matic",
            "https://rpc.ankr.com/polygon"
        ],
        "chainId": 137,
        "network": "polygon",
        "chunkSize": 100
    },
    "23294": {
        "rpc": "https://sapphire.oasis.io",
        "fallbackRPCs": [
            "https://1rpc.io/oasis/sapphire"
        ],
        "chainId": 23294,
        "network": "sapphire",
        "chunkSize": 100
    },
    "11155111": {
        "rpc": "https://eth-sepolia.g.alchemy.com/v2/{API_KEY}",
        "fallbackRPCs": [
            "https://1rpc.io/sepolia"
        ],
        "chainId": 11155111,
        "network": "sepolia",
        "chunkSize": 100
    },
    "11155420": {
        "rpc": "https://opt-sepolia.g.alchemy.com/v2/{API_KEY}",
        "fallbackRPCs": [
            "https://endpoints.omniatech.io/v1/op/sepolia/public",
            "https://optimism-sepolia.blockpi.network/v1/rpc/public"
        ],
        "chainId": 11155420,
        "network": "optimism-sepolia",
        "chunkSize": 100
    }
}

def get_docker_compose_files():
    all_files = glob.glob("docker-compose*.yaml")
    files = [f for f in all_files if os.path.basename(f) != "docker-compose1.yaml"]
    if not files:
        print("No docker-compose*.yaml files, except docker-compose1.yaml, found in the current directory.")
    else:
        print(f"Files found for processing: {files}")
    return files

def load_yaml(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def save_yaml(content, file_path):
    with open(file_path, 'w') as f:
        yaml.dump(content, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
    print(f"File updated: {file_path}")

def construct_custom_rpcs(api_key):
    rpcs = copy.deepcopy(CUSTOM_RPCS_TEMPLATE)
    for chain_id, config in rpcs.items():
        if "{API_KEY}" in config["rpc"]:
            rpcs[chain_id]["rpc"] = config["rpc"].replace("{API_KEY}", api_key)
    return rpcs

def main():
    files = get_docker_compose_files()
    if not files:
        return

    print("\nChoose RPCS replacement option:")
    print("1. Replace with default RPCS configuration.")
    print("2. Replace with custom RPCS configuration using your API key.")
    choice = input("Enter 1 or 2: ").strip()

    if choice == '1':
        new_rpcs = DEFAULT_RPCS
    elif choice == '2':
        api_key = input("Enter your Alchemy API key: ").strip()
        if not api_key:
            print("API key cannot be empty.")
            return
        new_rpcs = construct_custom_rpcs(api_key)
    else:
        print("Invalid choice. Exiting.")
        return

    rpcs_json = json.dumps(new_rpcs, separators=(',', ':'))

    for file in files:
        try:
            content = load_yaml(file)

            services = content.get('services', {})
            updated = False
            for service_name, service_config in services.items():
                env = service_config.get('environment', {})
                if 'RPCS' in env:
                    print(f"Updating RPCS in service '{service_name}' of file '{file}'.")
                    env['RPCS'] = rpcs_json
                    updated = True
                else:
                    print(f"RPCS environment variable not found in service '{service_name}' of file '{file}'. Skipping.")

            if updated:
                save_yaml(content, file)
            else:
                print(f"File '{file}' does not require updating.")

        except Exception as e:
            print(f"Error processing file '{file}': {e}")

if __name__ == "__main__":
    main()
