#!/usr/bin/env python3
# fake_direwolf.py - Mimics Direwolf's KISS interface over TCP with LAN discovery

import socket
import threading
import sys
import time
import os
import curses
import logging
import select
import configparser  # CHANGE: Added for config file support
from collections import deque

KISS_PORT = 8051
PEER_PORT = 8052
BROADCAST_PORT = 5000
BROADCAST_INTERVAL = 60
BUFFER_SIZE = 1024
RETRY_INTERVAL = 10
PEER_TIMEOUT = 120
MAX_LOG_LINES = 20
MAX_STATUS_LINES = 5
LOG_DIR = os.path.expanduser('~/terminal/server_data')
LOG_FILE = os.path.join(LOG_DIR, 'fake_direwolf.log')

peer_status = "Disconnected"
packet_log = deque(maxlen=MAX_LOG_LINES)  # (receive_time, deliver_time, ts, direction, frame)
status_messages = deque(maxlen=MAX_STATUS_LINES)
screen_lock = threading.Lock()
screen_needs_update = {}
peer_socket = None
stop_event = threading.Event()
discovered_peers = {}
active_kiss_clients = []
connection_lock = threading.Lock()

os.makedirs(LOG_DIR, exist_ok=True)
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.info
# Backup logging always on
log(f"Deleted old log file and started new session (PID: {os.getpid()})")

# Config file setup with enhanced logging options
config = configparser.ConfigParser()
CONFIG_FILE = os.path.join(LOG_DIR, 'fake_direwolf.conf')
if not os.path.exists(CONFIG_FILE):
    config['Settings'] = {
        'log_kiss_receive_loop': 'False',      # Reduced spam: loop entry/exit
        'log_kiss_raw_data': 'True',          # Useful: raw data received
        'log_kiss_frame_parse': 'True',       # Useful: frame parsing steps
        'log_kiss_send': 'True',             # Useful: packet sends
        'log_kiss_buffer_state': 'False',     # Reduced spam: buffer changes
        'log_kiss_errors': 'True',           # Useful: KISS errors
        'log_kiss_frame_validation': 'True',  # New: frame structure validation
        'log_kiss_payload_decode': 'True',    # New: payload decode attempts
        'log_peer_receive_loop': 'False',     # Reduced spam: peer loop
        'log_peer_raw_data': 'True',         # Useful: peer raw data
        'log_peer_frame_parse': 'True',      # Useful: peer frame parsing
        'log_peer_send': 'True',            # Useful: peer sends
        'log_peer_frame_validation': 'True', # New: peer frame validation
        'log_peer_payload_decode': 'True',   # New: peer payload decode
        'log_broadcast': 'True',            # Useful: broadcast events
        'log_peer_state': 'True',          # Useful: peer state changes
        'log_ui_updates': 'False',          # Reduced spam: UI updates
        'log_thread_management': 'True',    # New: thread start/stop
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
config.read(CONFIG_FILE)
LOG_KISS_RECEIVE_LOOP = config.getboolean('Settings', 'log_kiss_receive_loop', fallback=False)
LOG_KISS_RAW_DATA = config.getboolean('Settings', 'log_kiss_raw_data', fallback=True)
LOG_KISS_FRAME_PARSE = config.getboolean('Settings', 'log_kiss_frame_parse', fallback=True)
LOG_KISS_SEND = config.getboolean('Settings', 'log_kiss_send', fallback=True)
LOG_KISS_BUFFER_STATE = config.getboolean('Settings', 'log_kiss_buffer_state', fallback=False)
LOG_KISS_ERRORS = config.getboolean('Settings', 'log_kiss_errors', fallback=True)
LOG_KISS_FRAME_VALIDATION = config.getboolean('Settings', 'log_kiss_frame_validation', fallback=True)
LOG_KISS_PAYLOAD_DECODE = config.getboolean('Settings', 'log_kiss_payload_decode', fallback=True)
LOG_PEER_RECEIVE_LOOP = config.getboolean('Settings', 'log_peer_receive_loop', fallback=False)
LOG_PEER_RAW_DATA = config.getboolean('Settings', 'log_peer_raw_data', fallback=True)
LOG_PEER_FRAME_PARSE = config.getboolean('Settings', 'log_peer_frame_parse', fallback=True)
LOG_PEER_SEND = config.getboolean('Settings', 'log_peer_send', fallback=True)
LOG_PEER_FRAME_VALIDATION = config.getboolean('Settings', 'log_peer_frame_validation', fallback=True)
LOG_PEER_PAYLOAD_DECODE = config.getboolean('Settings', 'log_peer_payload_decode', fallback=True)
LOG_BROADCAST = config.getboolean('Settings', 'log_broadcast', fallback=True)
LOG_PEER_STATE = config.getboolean('Settings', 'log_peer_state', fallback=True)
LOG_UI_UPDATES = config.getboolean('Settings', 'log_ui_updates', fallback=False)
LOG_THREAD_MANAGEMENT = config.getboolean('Settings', 'log_thread_management', fallback=True)

def add_status_message(message):
    with screen_lock:
        status_messages.append(f"{time.strftime('%H:%M:%S')}: {message}")
        screen_needs_update['status_messages'] = True
        if LOG_UI_UPDATES:
            log(f"UI update queued: status_messages at {time.time()}")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def ping_peer(host):
    try:
        response = os.system(f"ping -c 1 -W 2 {host} > /dev/null 2>&1")
        return response == 0
    except Exception:
        return False

def parse_ax25_callsigns(frame):
    if len(frame) < 16:
        if LOG_KISS_FRAME_PARSE:
            log(f"Frame too short for callsign parsing: {frame.hex()} (len={len(frame)})")
        return "Unknown", "Unknown"
    ax25 = frame[2:-1]
    dest = ''.join(chr(b >> 1) for b in ax25[:6]).strip()
    src = ''.join(chr(b >> 1) for b in ax25[7:13]).strip()
    dest_ssid = (ax25[6] >> 1) & 0x0F
    src_ssid = (ax25[13] >> 1) & 0x0F
    if LOG_KISS_FRAME_PARSE:
        log(f"Parsed callsigns - src={src}-{src_ssid}, dest={dest}-{dest_ssid}")
    return f"{src}-{src_ssid}" if src_ssid else src, f"{dest}-{dest_ssid}" if dest_ssid else dest

def decode_payload(frame):
    if len(frame) < 18:
        if LOG_KISS_PAYLOAD_DECODE:
            log(f"Frame too short for payload decode: {frame.hex()} (len={len(frame)})")
        return "<short-frame>"
    ax25 = frame[2:-1]  # Strip KISS delimiters and trailing 7e
    payload_start = 17  # Skip dest (7) + src (7) + control (1) + pid (1)
    payload_end = len(ax25) - 2  # Exclude FCS (2 bytes)
    if payload_end <= payload_start:
        if LOG_KISS_PAYLOAD_DECODE:
            log(f"Empty payload detected: {frame.hex()}")
        return "<empty-payload>"
    payload = ax25[payload_start:payload_end]
    if LOG_KISS_PAYLOAD_DECODE:
        log(f"Extracted payload bytes: {payload.hex()} (len={len(payload)})")
    try:
        decoded = payload.decode('ascii')
        if LOG_KISS_PAYLOAD_DECODE:
            log(f"Successfully decoded payload: {decoded}")
        return decoded
    except Exception as e:
        if LOG_KISS_PAYLOAD_DECODE:
            log(f"Decode failed: {e}, raw bytes: {payload.hex()}")
        return f"<hex: {payload.hex()}>"

def handle_kiss_client(kiss_socket):
    addr = kiss_socket.getpeername()
    log(f"KISS client connected: {addr}")
    add_status_message(f"KISS client connected: {addr}")
    with screen_lock:
        active_kiss_clients.append(kiss_socket)
        screen_needs_update['clients'] = True
    buffer = b""
    while True:
        if LOG_KISS_RECEIVE_LOOP:
            log(f"KISS client {addr}: Entering receive loop at {time.time()}")
        try:
            readable, _, errored = select.select([kiss_socket], [], [kiss_socket], 1.0)
            if errored:
                log(f"KISS client {addr} errored")
                if LOG_KISS_ERRORS:
                    log(f"KISS client {addr} select error detected")
                break
            if readable:
                data = kiss_socket.recv(BUFFER_SIZE)
                if not data:
                    log(f"KISS client {addr} disconnected (no data)")
                    add_status_message(f"KISS client disconnected: {addr}")
                    break
                receive_time = time.time()
                if LOG_KISS_RAW_DATA:
                    log(f"KISS client {addr} received raw data at {receive_time}: {data.hex()}")
                buffer += data
                if LOG_KISS_BUFFER_STATE:
                    log(f"KISS client {addr} buffer updated: {buffer.hex()} (len={len(buffer)})")
                while b'\xC0' in buffer[1:]:
                    end = buffer.find(b'\xC0', 1)
                    if end == -1:
                        if LOG_KISS_FRAME_PARSE:
                            log(f"KISS client {addr}: Incomplete frame, waiting for more data: {buffer.hex()}")
                        break
                    frame = buffer[:end + 1]
                    buffer = buffer[end + 1:]
                    if LOG_KISS_BUFFER_STATE:
                        log(f"KISS client {addr} buffer after frame split: {buffer.hex()} (len={len(buffer)})")
                    if len(frame) > 2 and frame[0] == 0xC0 and frame[-1] == 0xC0:
                        if LOG_KISS_FRAME_VALIDATION:
                            log(f"KISS client {addr}: Valid KISS frame structure: {frame.hex()}")
                        src, dest = parse_ax25_callsigns(frame)
                        payload = decode_payload(frame)
                        log(f"Packet received from {src} to {dest} at {addr} at {receive_time}: {frame.hex()} (payload: {payload})")
                        deliver_time = None
                        with connection_lock:
                            if peer_socket:
                                log(f"Sending to peer {peer_socket.getpeername()} at {time.time()}")
                                if LOG_KISS_SEND:
                                    log(f"KISS client {addr}: Sending frame to peer {peer_socket.getpeername()}: {frame.hex()}")
                                peer_socket.send(frame)
                                deliver_time = time.time()
                                log(f"Packet delivery to peer confirmed at {deliver_time}")
                        with screen_lock:
                            for client in active_kiss_clients:
                                if client != kiss_socket:
                                    log(f"Sending to KISS client {client.getpeername()} at {time.time()}")
                                    if LOG_KISS_SEND:
                                        log(f"KISS client {addr}: Sending frame to client {client.getpeername()}: {frame.hex()}")
                                    client.send(frame)
                                    deliver_time = time.time() if deliver_time is None else deliver_time
                                    log(f"Packet delivery to KISS client {client.getpeername()} confirmed at {deliver_time}")
                            packet_log.append((receive_time, deliver_time or time.time(), time.strftime('%H:%M:%S'), f"From {src} to {dest}", f"{payload} ({frame.hex()[:20]}...)"))
                            screen_needs_update['packet_log'] = True
                    else:
                        if LOG_KISS_FRAME_VALIDATION:
                            log(f"KISS client {addr}: Invalid KISS frame skipped: {frame.hex()}")
            if LOG_KISS_RECEIVE_LOOP:
                log(f"KISS client {addr}: Receive loop iteration complete at {time.time()}")
        except Exception as e:
            log(f"KISS client {addr} error: {e}")
            if LOG_KISS_ERRORS:
                log(f"KISS client {addr} exception: {e}")
            add_status_message(f"KISS client error: {addr} - {e}")
            break
    with screen_lock:
        if kiss_socket in active_kiss_clients:
            active_kiss_clients.remove(kiss_socket)
            screen_needs_update['clients'] = True
    kiss_socket.close()

def handle_peer(peer_socket_ref):
    global peer_status, screen_needs_update
    peer_addr = peer_socket_ref.getpeername()
    log(f"Connected to peer: {peer_addr}")
    add_status_message(f"Connected to peer: {peer_addr}")
    with screen_lock:
        peer_status = f"Connected to {peer_addr[0]}:{peer_addr[1]}"
        screen_needs_update['peer_status'] = True
    buffer = b""
    while True:
        if LOG_PEER_RECEIVE_LOOP:
            log(f"Peer {peer_addr}: Entering receive loop at {time.time()}")
        try:
            readable, _, errored = select.select([peer_socket_ref], [], [peer_socket_ref], PEER_TIMEOUT)
            if errored or not readable:
                log(f"Peer {peer_addr} not responding, closing")
                add_status_message(f"Peer {peer_addr} not responding")
                break
            data = peer_socket_ref.recv(BUFFER_SIZE)
            if not data:
                log(f"Peer disconnected: {peer_addr} (no data received)")
                add_status_message(f"Peer disconnected: {peer_addr}")
                break
            receive_time = time.time()
            if LOG_PEER_RAW_DATA:
                log(f"Peer {peer_addr} received raw data at {receive_time}: {data.hex()}")
            buffer += data
            log(f"Received raw data from peer {peer_addr} at {receive_time}: {buffer.hex()}")
            while b'\xC0' in buffer[1:]:
                end = buffer.find(b'\xC0', 1)
                if end == -1:
                    if LOG_PEER_FRAME_PARSE:
                        log(f"Peer {peer_addr}: Incomplete frame, waiting for more data: {buffer.hex()}")
                    break
                frame = buffer[:end + 1]
                buffer = buffer[end + 1:]
                if len(frame) > 2 and frame[0] == 0xC0 and frame[-1] == 0xC0:
                    if LOG_PEER_FRAME_VALIDATION:
                        log(f"Peer {peer_addr}: Valid KISS frame structure: {frame.hex()}")
                    src, dest = parse_ax25_callsigns(frame)
                    payload = decode_payload(frame)
                    log(f"Packet received from {src} to {dest} from peer {peer_addr} at {receive_time}: {frame.hex()} (payload: {payload})")
                    deliver_time = None
                    with screen_lock:
                        for kiss_socket in active_kiss_clients:
                            log(f"Sending to KISS client {kiss_socket.getpeername()} at {time.time()}")
                            if LOG_PEER_SEND:
                                log(f"Peer {peer_addr}: Sending frame to client {kiss_socket.getpeername()}: {frame.hex()}")
                            kiss_socket.send(frame)
                            deliver_time = time.time()
                            log(f"Packet delivery to KISS client {kiss_socket.getpeername()} confirmed at {deliver_time}")
                        packet_log.append((receive_time, deliver_time or time.time(), time.strftime('%H:%M:%S'), f"From {src} to {dest}", f"{payload} ({frame.hex()[:20]}...)"))
                        screen_needs_update['packet_log'] = True
                else:
                    if LOG_PEER_FRAME_VALIDATION:
                        log(f"Peer {peer_addr}: Invalid KISS frame skipped: {frame.hex()}")
            if LOG_PEER_RECEIVE_LOOP:
                log(f"Peer {peer_addr}: Receive loop iteration complete at {time.time()}")
        except Exception as e:
            log(f"Peer error {peer_addr}: {e}")
            add_status_message(f"Peer error: {e}")
            break
    with screen_lock:
        peer_status = "Disconnected"
        screen_needs_update['peer_status'] = True
    peer_socket_ref.close()
    with connection_lock:
        global peer_socket
        if peer_socket == peer_socket_ref:
            log(f"Clearing peer_socket {peer_addr} due to disconnection")
            peer_socket = None

def kiss_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', KISS_PORT))
        server.listen(1)
        log(f"KISS server listening on port {KISS_PORT} (Thread ID: {threading.current_thread().ident})")
    except Exception as e:
        log(f"KISS server bind error: {e}")
        if LOG_KISS_ERRORS:
            log(f"KISS server bind failed: {e}")
        sys.exit(1)
    while not stop_event.is_set():
        try:
            kiss_socket, addr = server.accept()
            threading.Thread(target=handle_kiss_client, args=(kiss_socket,), daemon=True).start()
        except Exception as e:
            log(f"KISS server accept error: {e}")
            if LOG_KISS_ERRORS:
                log(f"KISS server accept failed: {e}")
            time.sleep(1)

def peer_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', PEER_PORT))
        server.listen(1)
        log(f"Peer server listening on port {PEER_PORT} (Thread ID: {threading.current_thread().ident})")
    except Exception as e:
        log(f"Peer server bind error: {e}")
        sys.exit(1)
    while not stop_event.is_set():
        try:
            peer_socket_ref, addr = server.accept()
            with connection_lock:
                global peer_socket
                if not peer_socket or not ping_peer(peer_socket.getpeername()[0] if peer_socket else '0.0.0.0'):
                    peer_socket = peer_socket_ref
                    log(f"Peer connection accepted from {addr}")
                    threading.Thread(target=handle_peer, args=(peer_socket_ref,), daemon=True).start()
                else:
                    log(f"Already connected to {peer_socket.getpeername()}, rejecting additional connection from {addr}")
                    peer_socket_ref.close()
        except Exception as e:
            log(f"Peer server accept error: {e}")
            time.sleep(1)

def broadcast_presence():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    local_ip = get_local_ip()
    message = f"FAKE_DIREWOLF|{local_ip}|{PEER_PORT}".encode()
    while not stop_event.is_set():
        try:
            udp_socket.sendto(message, ('255.255.255.255', BROADCAST_PORT))
            if LOG_BROADCAST:
                log(f"BCAST_SENT: {message.decode()}")
            add_status_message(f"Broadcast sent: {message.decode()}")
        except Exception as e:
            log(f"Broadcast error: {e}")
            add_status_message(f"Broadcast error: {e}")
        time.sleep(BROADCAST_INTERVAL)

def listen_for_peers():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', BROADCAST_PORT))
    local_ip = get_local_ip()
    while not stop_event.is_set():
        try:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            message = data.decode()
            if message.startswith("FAKE_DIREWOLF|"):
                _, peer_ip, peer_port = message.split('|')
                peer_port = int(peer_port)
                if peer_ip != local_ip:
                    with screen_lock:
                        discovered_peers[peer_ip] = peer_port
            if LOG_BROADCAST:
                log(f"BCAST_RCVD: {message} from {addr}")
            add_status_message(f"Broadcast received: {message} from {addr[0]}")
        except Exception as e:
            log(f"Listen error: {e}")

def peer_manager():
    global peer_socket, peer_status, screen_needs_update
    local_ip = get_local_ip()
    while not stop_event.is_set():
        with connection_lock:
            if peer_socket:
                try:
                    peer_ip, peer_port = peer_socket.getpeername()
                    readable, writable, errored = select.select([], [peer_socket], [peer_socket], 0.1)
                    if not writable or errored:
                        raise ConnectionError("Socket not writable or in error state")
                    peer_socket.send(b'')
                    if not ping_peer(peer_ip):
                        log(f"Peer {peer_ip} not responding, closing")
                        add_status_message(f"Peer {peer_ip} not responding")
                        peer_socket.close()
                        peer_socket = None
                        peer_status = "Disconnected"
                        screen_needs_update['peer_status'] = True
                        if LOG_PEER_STATE:
                            log(f"UI update queued: peer_status at {time.time()}")
                except Exception as e:
                    log(f"Peer socket error or disconnected: {e} (was {peer_socket.getpeername() if peer_socket else 'None'})")
                    add_status_message(f"Peer disconnected: {e}")
                    if peer_socket:
                        peer_socket.close()
                    peer_socket = None
                    peer_status = "Disconnected"
                    screen_needs_update['peer_status'] = True
                    if LOG_PEER_STATE:
                        log(f"UI update queued: peer_status at {time.time()}")
            if LOG_PEER_STATE:
                log(f"Peer state check: peer_socket={peer_socket}, discovered_peers={discovered_peers}")
            if not peer_socket and discovered_peers:
                for peer_ip, peer_port in list(discovered_peers.items()):
                    if peer_ip == local_ip:
                        continue
                    if local_ip >= peer_ip:
                        if LOG_PEER_STATE:
                            log(f"Skipping outbound to {peer_ip}:{peer_port}—local IP {local_ip} >= peer IP {peer_ip}")
                        add_status_message(f"Waiting for inbound from {peer_ip}")
                        continue
                    log(f"Attempting outbound connection to {peer_ip}:{peer_port}")
                    add_status_message(f"Connecting to {peer_ip}:{peer_port}")
                    new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        new_socket.connect((peer_ip, peer_port))
                        peer_socket = new_socket
                        log(f"Connected outbound to peer {peer_ip}:{peer_port}")
                        peer_status = f"Connected to {peer_ip}:{peer_port}"
                        screen_needs_update['peer_status'] = True
                        if LOG_PEER_STATE:
                            log(f"UI update queued: peer_status at {time.time()}")
                        threading.Thread(target=handle_peer, args=(peer_socket,), daemon=True).start()
                        break
                    except Exception as e:
                        log(f"Outbound connection to {peer_ip}:{peer_port} failed: {e}")
                        add_status_message(f"Failed to connect to {peer_ip}: {e}")
                        new_socket.close()
        time.sleep(RETRY_INTERVAL)

def status_display(stdscr):
    global screen_needs_update
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
    stdscr.nodelay(True)
    kiss_thread = threading.Thread(target=kiss_server, daemon=True)
    peer_thread = threading.Thread(target=peer_server, daemon=True)
    broadcast_thread = threading.Thread(target=broadcast_presence, daemon=True)
    listen_thread = threading.Thread(target=listen_for_peers, daemon=True)
    manager_thread = threading.Thread(target=peer_manager, daemon=True)
    kiss_thread.start()
    peer_thread.start()
    broadcast_thread.start()
    listen_thread.start()
    manager_thread.start()
    if LOG_THREAD_MANAGEMENT:
        log(f"Started threads: KISS ({kiss_thread.ident}), Peer ({peer_thread.ident}), Broadcast ({broadcast_thread.ident}), Listen ({listen_thread.ident}), Manager ({manager_thread.ident})")

    max_y, max_x = stdscr.getmaxyx()
    stdscr.clear()
    stdscr.addstr(0, 0, "=" * (max_x - 2), curses.color_pair(1))
    stdscr.addstr(1, 2, f"Fake Direwolf Status - KISS Port: {KISS_PORT}", curses.color_pair(3))
    stdscr.addstr(2, 2, f"Local IP: {get_local_ip()} Peer Port: {PEER_PORT}", curses.color_pair(3))
    stdscr.addstr(3, 2, f"Peer Status: {peer_status}", curses.color_pair(2 if 'Connected' in peer_status else 1))
    stdscr.addstr(4, 2, f"KISS Clients: {len(active_kiss_clients)}", curses.color_pair(2 if active_kiss_clients else 1))
    stdscr.addstr(5, 2, "Status Updates:", curses.color_pair(3))
    stdscr.addstr(min(6 + MAX_STATUS_LINES, max_y - 2), 2, "Recv Time  Deliv Time  Timestamp  Direction  Packet", curses.color_pair(3))
    stdscr.addstr(max_y - 1, 0, "=" * (max_x - 2), curses.color_pair(1))
    stdscr.refresh()

    while True:
        with screen_lock:
            if 'peer_status' in screen_needs_update:
                stdscr.addstr(3, 2, f"Peer Status: {peer_status.ljust(max_x-14)}", 
                            curses.color_pair(2 if 'Connected' in peer_status else 1))
                screen_needs_update.pop('peer_status')
            if 'clients' in screen_needs_update:
                stdscr.addstr(4, 2, f"KISS Clients: {len(active_kiss_clients)}".ljust(max_x-15), 
                            curses.color_pair(2 if active_kiss_clients else 1))
                screen_needs_update.pop('clients')
            if 'status_messages' in screen_needs_update:
                for i in range(6, 6 + MAX_STATUS_LINES):
                    stdscr.move(i, 4)
                    stdscr.clrtoeol()
                for i, msg in enumerate(status_messages, start=6):
                    if i < max_y - 2 and i < 6 + MAX_STATUS_LINES:
                        stdscr.addstr(i, 4, msg[:max_x-6], curses.color_pair(3))
                screen_needs_update.pop('status_messages')
            if 'packet_log' in screen_needs_update:
                for i in range(7 + MAX_STATUS_LINES, max_y - 2):
                    stdscr.move(i, 4)
                    stdscr.clrtoeol()
                for i, (receive_time, deliver_time, ts, direction, frame) in enumerate(packet_log, start=7 + MAX_STATUS_LINES):
                    if i < max_y - 2:
                        recv_str = f"{time.strftime('%H:%M:%S', time.localtime(receive_time))}"
                        deliv_str = f"{time.strftime('%H:%M:%S', time.localtime(deliver_time))}" if deliver_time else "N/A"
                        fixed_length = 30  # Time fields and spaces
                        direction_str = f"{direction}: "
                        frame_max_len = max_x - fixed_length - len(direction_str) - 4
                        frame_str = frame[:frame_max_len] if frame_max_len > 0 else ""
                        line = f"{recv_str}  {deliv_str}  {ts}  {direction_str}{frame_str}"
                        stdscr.addstr(i, 4, line[:max_x-4], curses.color_pair(2))
                screen_needs_update.pop('packet_log')
            if screen_needs_update:
                stdscr.refresh()

        char = stdscr.getch()
        if char == ord('q') or char == ord('Q'):
            log("Shutting down via UI")
            if LOG_THREAD_MANAGEMENT:
                log("Stopping all threads")
            add_status_message("Shutting down")
            stop_event.set()
            with connection_lock:
                if peer_socket:
                    peer_socket.close()
            sys.exit(0)
        time.sleep(0.05)

def main():
    curses.wrapper(status_display)

if __name__ == "__main__":
    main()

# CHANGE LOG:
# - Added configparser import and config file setup with new logging types (Lines 9, 40-86)
# - New logging types: kiss_receive_loop, kiss_raw_data, kiss_frame_parse, kiss_send, kiss_buffer_state, kiss_errors, peer_receive_loop, peer_raw_data, peer_frame_parse, peer_send (Lines 48-79)
# - Added detailed logging in handle_kiss_client for receive loop, raw data, frame parsing, sends, buffer state, and errors (Lines 144-216)
# - Added logging in handle_peer for receive loop, raw data, frame parsing, and sends (Lines 217-268)
# - Updated existing logs with config toggles (e.g., LOG_BROADCAST, LOG_PEER_STATE) (Lines 80-86)
# - Backup logging remains always on (Line 130)
# - Line count increased from ~370 to ~430 due to config setup and additional logging
# - Updated CHANGE LOG below for new fixes (March 18, 2025)
# - Fixed decode_payload to exclude FCS correctly (Lines 135-153)
# - Enhanced parse_ax25_callsigns for SSID support (Lines 117-133)
# - Adjusted status_display packet log to prevent wrapping (Lines 400-408)
# - Added new logging types for frame validation and payload decode (Lines 67-74)
# - Turned off spammy logs by default (e.g., receive_loop, buffer_state) (Lines 54-65)