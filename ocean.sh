#!/bin/bash

# Color and formatting definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
RESET='\033[0m'


# Icons for menu options
ICON_TELEGRAM="🚀"
ICON_INSTALL="🛠️"
ICON_LOGS="📄"
ICON_STOP="⏹️"
ICON_START="▶️"
ICON_WALLET="💰"
ICON_EXIT="❌"
ICON_CHANGE_RPC="🔄"  # New Icon for Change RPC

# Functions to draw borders and display menu
draw_top_border() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
}

draw_middle_border() {
    echo -e "${CYAN}╠══════════════════════════════════════════════════════╣${RESET}"
}

draw_bottom_border() {
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
}

print_telegram_icon() {
    echo -e "          ${MAGENTA}${ICON_TELEGRAM} Follow us on Telegram!${RESET}"
}

display_ascii() {
    echo -e "    ${RED}    ____  __ __    _   ______  ____  ___________${RESET}"
    echo -e "    ${GREEN}   / __ \\/ //_/   / | / / __ \\/ __ \\/ ____/ ___/${RESET}"
    echo -e "    ${BLUE}  / / / / ,<     /  |/ / / / / / / / __/  \\__ \\ ${RESET}"
    echo -e "    ${YELLOW} / /_/ / /| |   / /|  / /_/ / /_/ / /___ ___/ / ${RESET}"
    echo -e "    ${MAGENTA}/_____/_/ |_|  /_/ |_/\____/_____/_____//____/  ${RESET}"
}

# Function to get IP address
get_ip_address() {
    ip_address=$(hostname -I | awk '{print $1}')
    if [[ -z "$ip_address" ]]; then
        echo -ne "${YELLOW}Unable to determine IP address automatically.${RESET}"
        echo -ne "${YELLOW} Please enter the IP address:${RESET} "
        read ip_address
    fi
    echo "$ip_address"
}

show_menu() {
    clear
    draw_top_border
    display_ascii
    draw_middle_border
    print_telegram_icon
    echo -e "    ${BLUE}Subscribe to our channel: ${YELLOW}https://t.me/dknodes${RESET}"
    draw_middle_border

    # Display current working directory and IP address
    current_dir=$(pwd)
    ip_address=$(get_ip_address)
    echo -e "    ${GREEN}Current Directory:${RESET} ${current_dir}"
    echo -e "    ${GREEN}IP Address:${RESET} ${ip_address}"
    draw_middle_border

    echo -e "    ${YELLOW}Please choose an option:${RESET}"
    echo
    echo -e "    ${CYAN}1.${RESET} ${ICON_INSTALL} Install Node"
    echo -e "    ${CYAN}2.${RESET} ${ICON_LOGS} View logs of Typesense"
    echo -e "    ${CYAN}3.${RESET} ${ICON_LOGS} View logs of Ocean nodes"
    echo -e "    ${CYAN}4.${RESET} ${ICON_STOP} Stop Node"
    echo -e "    ${CYAN}5.${RESET} ${ICON_START} Start Node"
    echo -e "    ${CYAN}6.${RESET} ${ICON_WALLET} View created wallets"
    echo -e "    ${CYAN}7.${RESET} ${ICON_CHANGE_RPC} Change RPC"  # New Menu Option
    echo -e "    ${CYAN}0.${RESET} ${ICON_EXIT} Exit"
    echo
    draw_bottom_border
    echo -ne "    ${YELLOW}Enter your choice [0-7]:${RESET} "  # Updated range to [0-7]
    read choice
}

install_node() {
    echo -e "${GREEN}🛠️  Installing Node...${RESET}"
    # Update and upgrade the system
    sudo apt update && sudo apt upgrade -y

    # Install Docker if not installed
    if ! command -v docker &> /dev/null; then
        sudo apt install docker.io -y
        sudo systemctl start docker
        sudo systemctl enable docker
    fi

    # Install Docker Compose if not installed
    if ! command -v docker-compose &> /dev/null; then
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi

    # Install Python3 and pip3 if not installed
    if ! command -v python3 &> /dev/null; then
        sudo apt install python3 -y
    fi
    if ! command -v pip3 &> /dev/null; then
        sudo apt install python3-pip -y
    fi

    # Install crontab if not installed
    if ! command -v crontab &> /dev/null; then
        sudo apt install cron -y
        sudo systemctl enable cron
        sudo systemctl start cron
    fi

    # Install required Python libraries
    pip3 install eth_account requests

    # Prompt for the number of nodes
    echo -ne "${YELLOW}Enter the number of nodes:${RESET} "
    read num_nodes

    # Get IP address
    ip_address=$(hostname -I | awk '{print $1}')
    if [[ -z "$ip_address" ]]; then
        echo -ne "${YELLOW}Unable to determine IP address automatically.${RESET}"
        echo -ne "${YELLOW} Please enter the IP address:${RESET} "
        read ip_address
    fi

    # Run script.py with IP address and number of nodes
    python3 script.py "$ip_address" "$num_nodes"
    docker network create ocean_network
    # Start Docker Compose services for each node
    for ((i=1; i<=num_nodes+1; i++)); do
        docker-compose -f docker-compose$i.yaml up -d
    done
    current_dir=$(pwd)
    # Schedule req.py to run every hour using crontab
    (crontab -l 2>/dev/null; echo "0 */2 * * * python3 $(pwd)/restart.py $ip_address $current_dir") | crontab -

    echo -e "${GREEN}✅ Node installed successfully.${RESET}"
    echo
    read -p "Press Enter to return to the main menu..."
}

view_typesense_logs() {
    echo -e "${GREEN}📄 Viewing logs of Typesense...${RESET}"
    docker logs typesense
    echo
    read -p "Press Enter to return to the main menu..."
}

view_ocean_node_logs() {
    echo -ne "${YELLOW}Enter the number of nodes:${RESET} "
    read num_nodes
    echo -ne "${YELLOW}Select a node to view logs (1-${num_nodes}):${RESET} "
    read node_number
    echo -e "${GREEN}📄 Viewing logs of ocean-node-${node_number}...${RESET}"
    docker logs ocean-node-$node_number
    echo
    read -p "Press Enter to return to the main menu..."
}

stop_node() {
    echo -ne "${YELLOW}Enter the number of nodes:${RESET} "
    read num_nodes
    echo -e "${GREEN}⏹️  Stopping Nodes...${RESET}"
    for ((i=1; i<=num_nodes+1; i++)); do
        docker-compose -f docker-compose$i.yaml down
    done

    # Remove the crontab entry for req.py
    crontab -l | grep -v "req.py" | crontab -

    echo -e "${GREEN}✅ Nodes stopped and crontab entry removed.${RESET}"
    echo
    read -p "Press Enter to return to the main menu..."
}

start_node() {
    echo -ne "${YELLOW}Enter the number of nodes:${RESET} "
    read num_nodes

    # Get IP address
    ip_address=$(hostname -I | awk '{print $1}')
    if [[ -z "$ip_address" ]]; then
        echo -ne "${YELLOW}Unable to determine IP address automatically.${RESET}"
        echo -ne "${YELLOW} Please enter the IP address:${RESET} "
        read ip_address
    fi

    echo -e "${GREEN}▶️  Starting Nodes...${RESET}"
    for ((i=1; i<=num_nodes+1; i++)); do
        docker-compose -f docker-compose$i.yaml up -d
    done
    
    ip_address=$(hostname -I | awk '{print $1}')
    if [[ -z "$ip_address" ]]; then
        echo -ne "${YELLOW}Unable to determine IP address automatically.${RESET}"
        echo -ne "${YELLOW} Please enter the IP address:${RESET} "
        read ip_address
    fi
    
    current_dir=$(pwd)
    # Schedule req.py to run every hour using crontab
    (crontab -l 2>/dev/null; echo "0 * * * * python3 $(pwd)/req.py $ip_address $current_dir") | crontab -

    echo -e "${GREEN}✅ Nodes started and crontab entry added.${RESET}"
    echo
    read -p "Press Enter to return to the main menu..."
}

view_wallets() {
    echo -e "${GREEN}💰 Displaying created wallets...${RESET}"
    cat wallets.json
    echo
    read -p "Press Enter to return to the main menu..."
}

# New Function for Changing RPC
change_rpc() {
    echo -e "${GREEN}🔄 Changing RPC...${RESET}"
    
    # Install yaml if not installed
    echo -e "${YELLOW}Installing YAML library...${RESET}"
    pip3 install yaml
    
    # Define the URL of the RPC.py script
    RPC_URL="https://raw.githubusercontent.com/dknodes/ocean/master/RPC.py"
    
    # Download RPC.py
    echo -e "${YELLOW}Downloading RPC.py script...${RESET}"
    wget -O RPC.py "$RPC_URL"
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Failed to download RPC.py.${RESET}"
        echo
        read -p "Press Enter to return to the main menu..."
        return
    fi
    
    # Run RPC.py
    echo -e "${YELLOW}Executing RPC.py...${RESET}"
    python3 RPC.py
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ RPC changed successfully.${RESET}"
    else
        echo -e "${RED}❌ An error occurred while changing RPC.${RESET}"
    fi
    echo
    read -p "Press Enter to return to the main menu..."
}

# Main loop
while true; do
    show_menu
    case $choice in
        1)
            install_node
            ;;
        2)
            view_typesense_logs
            ;;
        3)
            view_ocean_node_logs
            ;;
        4)
            stop_node
            ;;
        5)
            start_node
            ;;
        6)
            view_wallets
            ;;
        7)  # New Case for Change RPC
            change_rpc
            ;;
        0)
            echo -e "${GREEN}❌ Exiting...${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid option. Please try again.${RESET}"
            echo
            read -p "Press Enter to continue..."
            ;;
    esac
done
