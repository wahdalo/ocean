import requests
import json
import subprocess
import logging
import os
import sys

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

url = f"https://incentive-backend.oceanprotocol.com/nodes?page=1&size=100&search=http%3A%2F%2F{ip_address}%2F"

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

def extract_ports(nodes):
    ports = []
    for node in nodes:
        source = node.get('_source', {})
        if not isinstance(source, dict):
            continue
        if not source.get('eligible', True):
            ip_and_dns = source.get('ipAndDns', {})
            port = ip_and_dns.get('port', None)
            if port is not None:
                ports.append(port)
    logger.info(f"Extracted {len(ports)} port(s) from nodes with 'eligible': false.")
    return ports

def execute_docker_compose(port, cwd):
    if port == 9000:
        command = ["docker", "restart", "ocean-node"]
        node_info = "ocean-node"
    else:
        port_new = port - 3001
        if port_new < 0:
            logger.warning(f"Calculated port for {port} is less than 0. Skipping.")
            return
        filename = f"docker-compose{port_new}.yaml"
        node_info = filename
        if not os.path.isfile(os.path.join(cwd, filename)):
            logger.error(f"File '{filename}' not found. Command skipped.")
            return
        command = ["docker-compose", "-f", filename, "restart"]
    command_str = ' '.join(command)
    logger.info(f"Executing command for node: {node_info}")
    logger.info(f"Command: {command_str}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=cwd)
        logger.info(f"Successfully executed: {command_str}")
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            logger.info(f"Command output:\n{stdout}")
        if stderr:
            logger.warning(f"Command errors:\n{stderr}")
    except subprocess.CalledProcessError as cpe:
        logger.error(f"Error executing command: {command_str}")
        error_output = cpe.stderr.strip()
        if error_output:
            logger.error(f"Error output:\n{error_output}")
    except FileNotFoundError:
        logger.error(f"'docker-compose' command not found. Ensure Docker Compose is installed and available in PATH.")
    except Exception as err:
        logger.error(f"Unexpected error executing command: {command_str}\nError: {err}")

def main():
    logger.info("=== Script execution started ===")
    nodes = fetch_nodes()
    if not nodes:
        logger.warning("No available nodes to process.")
        return
    ports = extract_ports(nodes)
    if not ports:
        logger.info("No nodes with 'eligible': false or missing ports.")
        return
    logger.info(f"Starting processing of ports: {ports}")
    for port in ports:
        execute_docker_compose(port, working_directory)
    logger.info("=== Script execution finished ===")

if __name__ == "__main__":
    main()
