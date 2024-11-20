import requests
import json
import subprocess
import logging
import os
import sys
from datetime import datetime, timedelta

if len(sys.argv) != 3:
    print("Usage: python3 req.py <IP_ADDRESS> <WORKING_DIRECTORY>")
    sys.exit(1)

ip_address = sys.argv[1]
working_directory = sys.argv[2]

logger = logging.getLogger('DockerRestartLogger')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler(os.path.join(working_directory, 'docker_restart.log'), encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def format_timestamp_to_gmt7(timestamp):
    date = datetime.fromtimestamp(timestamp / 1000)
    date_gmt7 = date + timedelta(hours=7)
    formatted_date = date_gmt7.strftime("%H:%M:%S")
    return formatted_date

file_path = os.path.join(working_directory, 'nodes_data.json')
url = f"https://incentive-backend.oceanprotocol.com/nodes?page=1&size=10&search={ip_address}"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Priority": "u=1, i",
    "Sec-CH-UA": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Referer": "https://nodes.oceanprotocol.com/",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}

def fetch_nodes():
    try:
        logger.info("Executing GET request to the API.")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        nodes = data.get('nodes', [])
        nodes = [node for node in nodes if 3001 <= node['_source']['ipAndDns']['port'] <= 3005] # and node['_source']['ipAndDns']['port'] != 3008]
        logger.info(f"Retrieved {len(nodes)} nodes from API.")
        return nodes
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error during request: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error during request: {req_err}")
    except json.JSONDecodeError as json_err:
        logger.error(f"Error parsing JSON: {json_err}")
    except Exception as err:
        logger.error(f"Unexpected error: {err}")
    return []

# Function to fetch nodes data and add 'restarted' key with value 'false'
def fetch_and_save_nodes(filename="nodes_data.json"):
    nodes = fetch_nodes()
    if not nodes:
        logger.warning("No available nodes to save.")
        return

    # Load existing data if the file exists
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing_data = json.load(f)
        existing_nodes = {node['_id']: node for node in existing_data.get("nodes", [])}
    else:
        existing_nodes = {}

    # Update 'restarted' to False only if 'lastCheck' has changed
    for node in nodes:
        node_id = node['_id']
        previous_node = existing_nodes.get(node_id)
        if previous_node and previous_node['_source']['lastCheck'] == node['_source']['lastCheck']:
            logger.info(f"Node {node_id} 'lastCheck' has not changed. Keeping previous 'restarted' status.")
            # Keep previous 'restarted' status if 'lastCheck' hasn't changed
            previous_node
            node['_source']['restarted'] = previous_node['_source'].get('restarted', False)
        else:
            # Reset 'restarted' to False if 'lastCheck' has changed or node is new
            logger.info(f"Node {node_id} 'lastCheck' has changed. Resetting 'restarted' to False.")
            node['_source']['restarted'] = False


    # Save updated nodes data to JSON file
    with open(filename, 'w') as f:
        json.dump({"nodes": nodes}, f, indent=4)
    logger.info(f"Fetched data saved to {filename} with selective 'restarted' updates.")


# Function to update the 'restarted' field to True for a specific node after restart
def update_restarted_status(node_id, filename="nodes_data.json"):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)

        # Find and update 'restarted' field to True for the specific node
        for node in data['nodes']:
            if node['_source']['id'] == node_id:
                node['_source']['restarted'] = True
                break

        # Write updated data back to the JSON file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info(f"'restarted' status updated to True for node {node_id} in {filename}.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error updating 'restarted' status: {e}")

def extract_ports(nodes):
    ports = []
    errors = []
    for node in nodes:
        source = node.get('_source', {})
        if not isinstance(source, dict):
            continue
        if not source.get('eligible', True):
            ip_and_dns = source.get('ipAndDns', {})
            port = ip_and_dns.get('port', None)
            if port is not None:
                ports.append(port)
                errors.append(f"{format_timestamp_to_gmt7(source.get('lastCheck', 0))} - {port} - {source.get('eligibilityCauseStr', 'N/A')}")
    logger.info(f"Extracted {len(ports)} port(s) from nodes with 'eligible': false.")
    return errors

def execute_docker_compose(port, cwd):

    if port == 9000:
        command = ["docker", "restart", "ocean-node"]
        node_info = "ocean-node"
    # else if port greater than 3008 skipped
    elif port > 3005: # or port == 3008:
        # logger.warning(f"Port {port} is greater than 3008. Skipping.")
        return False
    else:
        port_new = port - 3001
        if port_new < 0:
            logger.warning(f"Calculated port for {port} resulted in {port_new}, which is less than 0. Skipping.")
            return False
        filename = f"docker-compose{port_new}.yaml"
        node_info = filename
        if not os.path.isfile(os.path.join(cwd, filename)):
            logger.error(f"File '{filename}' not found in directory '{cwd}'. Command skipped.")
            return False
        
        command_down = ["sudo", "docker-compose", "-f", os.path.join(cwd, filename), "down"]
        command_up = ["sudo", "docker-compose", "-f", os.path.join(cwd, filename), "up", "-d"]

    logger.info(f"Executing command for node: {node_info}")
    logger.info(f"Down Command: {' '.join(command_down)}")
    logger.info(f"Up Command: {' '.join(command_up)}")

    try:
        result_down = subprocess.run(command_down, capture_output=True, text=True, check=True, cwd=cwd)
        logger.info(f"Successfully executed: {' '.join(command_down)}")
        if result_down.stdout:
            logger.info(f"Down Command output:\n{result_down.stdout.strip()}")
        if result_down.stderr:
            logger.warning(f"Down Command errors:\n{result_down.stderr.strip()}")

        result_up = subprocess.run(command_up, capture_output=True, text=True, check=True, cwd=cwd)
        logger.info(f"Successfully executed: {' '.join(command_up)}")
        if result_up.stdout:
            logger.info(f"Up Command output:\n{result_up.stdout.strip()}")
        if result_up.stderr:
            logger.warning(f"Up Command errors:\n{result_up.stderr.strip()}")

        return True
    except subprocess.CalledProcessError as cpe:
        logger.error(f"Error executing commands")
        if cpe.stderr:
            logger.error(f"Error output:\n{cpe.stderr.strip()}")
        return False
    except FileNotFoundError:
        logger.error(f"'docker-compose' command not found. Ensure Docker Compose is installed and available in PATH.")
        return False
    except Exception as err:
        logger.error(f"Unexpected error executing command\nError: {err}")
        return False
        
def send_telegram_alert(message):
    bot_token = ""
    chat_id = ""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("Alert sent successfully.")
        else:
            print(f"Failed to send alert. Status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error occurred: {e}")


# Function to check restart conditions and perform restart if conditions are met
# def check_and_restart_nodes(filename="nodes_data.json"):
#     current_time = int(datetime.now().timestamp() * 1000)  # Current time in milliseconds

#     try:
#         with open(filename, 'r') as f:
#             data = json.load(f)

#         for node in data['nodes']:
#             node_id = node['_source']['id']
#             last_check = node['_source']['lastCheck']
#             eligible = node['_source']['eligible']
#             restarted = node.get('restarted', False)

#             # Skip node if it's already restarted
#             if restarted:
#                 logger.info(f"Node {node_id} has already been restarted. Skipping restart.")
#                 continue

#             # Check if restart conditions are met
#             if last_check < current_time and not eligible:
#                 port = node['_source']['ipAndDns']['port']
#                 logger.info(f"Node {node_id} eligible for restart. Restarting...")
#                 if execute_docker_compose(port, working_directory):
#                     # Update 'restarted' status to True after restart
#                     update_restarted_status(node_id)
#             else:
#                 logger.info(f"Node {node_id} is not eligible for restart. Skipping.")

#     except (FileNotFoundError, json.JSONDecodeError) as e:
#         logger.error(f"Error reading or updating nodes data: {e}")


def main():
    logger.info("=== Script execution started ===")

    # Step 1: Fetch and save nodes with 'restarted': False
    fetch_and_save_nodes()

    # Step 2: Load nodes from the saved JSON file
    with open("nodes_data.json", "r") as file:
        nodes_data = json.load(file)

    # Step 3: Process each node and check eligibility for restart
    ports = []
    for node in nodes_data["nodes"]:
        current_time = int(datetime.now().timestamp() * 1000)  # Current time in milliseconds
        node_id = node['_source']['id']
        last_check = node['_source']['lastCheck']
        eligible = node['_source']['eligible']
        restarted = node['_source']['restarted']
        _source = node.get("_source", {})
        port = _source.get('ipAndDns', {}).get('port')

        # Skip node if it's already restarted
        if restarted:
            print(f"Node {node_id} has already been restarted. Skipping restart.")
            continue

        # Check if node is eligible, and has a lastCheck in the past
        if (not eligible and last_check < current_time):
            print(f"Node {node_id} eligible for restart. Restarting...")
            if port:
                ports.append(port)
    
    if not ports:
        logger.info("No nodes with 'eligible': false and 'restarted': False found.")
        return

    # Step 4: Restart each Docker container and update 'restarted' status
    for port in ports:
        if execute_docker_compose(port, working_directory):
        # Update 'restarted' status in the JSON data after a successful restart
            for node in nodes_data["nodes"]:
                if node["_source"]["ipAndDns"]["port"] == port:
                    node["_source"]["restarted"] = True
                    logger.info(f"'restarted' status updated to True for node {node_id} in nodes_data.json.")

    # Step 5: Save the updated nodes data back to the JSON file
    with open("nodes_data.json", "w") as file:
        json.dump(nodes_data, file, indent=4)

    # Send alert and finish script
    nodeData = [node for node in nodes_data["nodes"] if node["_source"]["ipAndDns"]["port"] in ports]
    error_message = "\n".join(f"» Port {node['_source']['ipAndDns']['port']} - {node['_source']['eligibilityCauseStr']}" for node in nodeData)
    send_telegram_alert(f"OCEAN NODE\n\nFound {len(ports)} Nodes InEligible! Restarting... \n{error_message}")
    logger.info("=== Script execution finished ===")

if __name__ == "__main__":
    main()
