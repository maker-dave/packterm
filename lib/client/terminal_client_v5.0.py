#!/usr/bin/env python3
# terminal_client.py
# Version 5.0.0 - 2025-03-22  # CHANGE v5.0.0: Added CMS with push sync, compression, menu access
# This is a test
# Chunk 1 v5.0.0 - Imports and Config
import time
import random
import sys
import os
import curses
import socket
import traceback
import textwrap
import glob
import shutil
import hashlib
import threading
import configparser
import pandas as pd
import queue
import crcmod
import json
import re
import zlib  # Added for AX.25 compression
from tabulate import tabulate
from pathlib import Path  # Added for CMS path handling

INSTALL_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(INSTALL_DIR, "terminal_client.conf")
CMS_DIR = Path("/opt/terminal_client/cms")  # CMS local cache
CMS_DIR.mkdir(exist_ok=True)
CMS_PUSH_DIR = CMS_DIR / "push"
CMS_PUSH_DIR.mkdir(exist_ok=True)
CALLSIGN = None
CALLSIGN_SSID = 0
COMM_MODE = 'KISS'
ROWS, COLS = 24, 80
TX_WINDOW = 10
SERVER_HOST = 'pi4.lan'
SERVER_PORT = 12345
FAKE_DIREWOLF_HOST = '127.0.0.1'
FAKE_DIREWOLF_PORT = 8051
LOG_FILE = os.path.join(INSTALL_DIR, "skippys_messups.log")
FORMS_DIR = os.path.join(INSTALL_DIR, "forms")
BACKUP_DIR = os.path.join(INSTALL_DIR, "backups")
MAX_RETRIES = 5
RETRY_DELAY = 5
PACLEN = 255
VERSION = "5.0.0"  # CHANGE v5.0.0: Major update

config = configparser.ConfigParser()
if not os.path.exists(CONFIG_FILE):
    config['Settings'] = {
        'callsign': 'CLT001',
        'callsign_ssid': '0',
        'comm_mode': 'KISS',
        'paclen': str(PACLEN),
        'fake_direwolf_host': '127.0.0.1',
        'fake_direwolf_port': '8051',
        'cms_sync_enabled': 'True',  # Added for CMS push sync
        'cms_sync_max_age': '604800',  # 1 week in seconds
        # Existing logging toggles (abridged)
        'log_callsign_prompt': 'True',
        'log_connectivity': 'True',
        'log_submission': 'True',
        # New CMS logging toggles
        'log_cms_sync': 'True',
        'log_cms_operations': 'True',
        'log_cms_packet_build': 'True',
        'log_cms_ui_state': 'False',  # Off to reduce spam
        # ... other existing settings ...
    }
    os.makedirs(INSTALL_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
config.read(CONFIG_FILE)
CALLSIGN = config.get('Settings', 'callsign', fallback='CLT001')
CALLSIGN_SSID = config.getint('Settings', 'callsign_ssid', fallback=0)
COMM_MODE = config.get('Settings', 'comm_mode', fallback='KISS')
PACLEN = config.getint('Settings', 'paclen', fallback=PACLEN)
FAKE_DIREWOLF_HOST = config.get('Settings', 'fake_direwolf_host', fallback='127.0.0.1')
FAKE_DIREWOLF_PORT = config.getint('Settings', 'fake_direwolf_port', fallback=8051)
CMS_SYNC_ENABLED = config.getboolean('Settings', 'cms_sync_enabled', fallback=True)
CMS_SYNC_MAX_AGE = config.getint('Settings', 'cms_sync_max_age', fallback=604800)
# Existing config vars (abridged)
LOG_CALLSIGN_PROMPT = config.getboolean('Settings', 'log_callsign_prompt', fallback=True)
LOG_CONNECTIVITY = config.getboolean('Settings', 'log_connectivity', fallback=True)
LOG_SUBMISSION = config.getboolean('Settings', 'log_submission', fallback=True)
LOG_CMS_SYNC = config.getboolean('Settings', 'log_cms_sync', fallback=True)
LOG_CMS_OPERATIONS = config.getboolean('Settings', 'log_cms_operations', fallback=True)
LOG_CMS_PACKET_BUILD = config.getboolean('Settings', 'log_cms_packet_build', fallback=True)
LOG_CMS_UI_STATE = config.getboolean('Settings', 'log_cms_ui_state', fallback=False)
# ... other existing config vars ...

# Chunk 2 v5.0.0 - Global State
cursor_row, cursor_col = None, None
form_fields = {}
field_values = {}
cursor_offset = 0
current_field = None
comms_log = []
debug_log = []
screen_dirty = True
form_id = None
selecting_mode = False
show_menu = False
menu_selection = 0
mode = None
messages = []
unread_messages = False
kiss_socket = None
last_no_data = 0
sending = False
submission_result = None
syncing = False
packet_queue = queue.Queue(maxsize=100)
socket_connected = False
form_parts = {}
cms_parts = {}  # Added for CMS multi-packet buffering

def log_event(message, ui=False, debug=False, submission=False, ui_state=False, packet=False, segment=False, submission_details=False, payload=False, segment_failure=False, socket_state=False, retries=False, ui_transitions=False, ack_processing=False, send_state=False, listener_state=False, search_query=False, search_results=False, screen_state=False, field_state=False, submission_flow=False, cursor_movement=False, packet_timing=False, error_details=False, packet_build=False, packet_parse=False, sync_state=False, sync_md5=False, sync_forms=False, sync_packets=False, packet_integrity=False, listener_retries=False, socket_reset=False, connection_success=False, packet_fragments=False, sync_mismatches=False, redraw_triggers=False, form_deletion=False, sync_start=False, sync_completion=False, form_exit=False, key_context=False, mode_switch=False, packet_queue=False, listener_queue=False, ui_packet_handling=False, queue_state=False, connection_attempts=False, packet_drop=False, thread_state=False, column_navigation=False, form_layout=False, row_movement=False, form_display_error=False, ui_render=False, socket_errors=False, form_ui_layout=False, input_field_state=False, kiss_framing=False, ax25_state=False, ax25_packet=False, ax25_parse_error=False, kiss_packet_received=False, packet_validation=False, md5_comparison=False, packet_relay=False, ui_redraw=False, socket_send_bytes=False, socket_send_failure=False, socket_reconnect=False, socket_status=False, socket_send_raw=False, socket_buffer=False, ui_comms_log=False, packet_send_time=False, packet_enqueue_time=False, packet_dequeue_time=False, queue_size=False, redraw_timing=False, kiss_receive_buffer=False, kiss_frame_timing=False, packet_content=False, socket_send_attempt=False, ui_packet_display=False, packet_structure=False, socket_validation=False, packet_transmission=False, ax25_build=False, ax25_validation=False, kiss_validation=False, fcs_calculation=False, json_rebuild=False, diff_state=False, delimiter_usage=False, sync_index=False, packet_format=False, packet_raw_decode=False, form_file_write=False, form_field_parse=False, newline_handling=False, file_content=False, command_validation=False, packet_handling=False, file_io=False, multi_packet=False, buffer_management=False, cms_sync=False, cms_operations=False, cms_packet_build=False, cms_ui_state=False):  # CHANGE v5.0.0: Added CMS logging
    global screen_dirty
    timestamp = time.ctime()
    log_line = f"{timestamp}: {message}"
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')
    if ui:
        comms_log.append((message, timestamp))
        if len(comms_log) > 20:
            comms_log.pop(0)
        screen_dirty = True
    # Existing logging (abridged)
    if submission and LOG_SUBMISSION: debug_log.append((message, timestamp))
    # New CMS logging
    if cms_sync and LOG_CMS_SYNC: debug_log.append(("CMS Sync: " + message, timestamp))
    if cms_operations and LOG_CMS_OPERATIONS: debug_log.append(("CMS Operation: " + message, timestamp))
    if cms_packet_build and LOG_CMS_PACKET_BUILD: debug_log.append(("CMS Packet Build: " + message, timestamp))
    if cms_ui_state and LOG_CMS_UI_STATE: debug_log.append(("CMS UI State: " + message, timestamp))
    # ... other existing logging ...

def log_comms(message):
    if not message.endswith(":M|SVR001|NONE|") and not message.endswith(":M|SVR001|PUSH|"):
        log_event(message, ui=True)

def backup_script():
    script_path = os.path.realpath(__file__)
    base_name = os.path.basename(script_path)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{base_name.rsplit('.', 1)[0]}_{timestamp}.{base_name.rsplit('.', 1)[1]}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    try:
        shutil.copy2(script_path, backup_path)
        log_event(f"Backed up to {backup_path}", ui=False)  # Always on
    except PermissionError as e:
        log_event(f"Backup failed: {str(e)} - proceeding without backup", ui=False, error_details=True)

def build_ax25_packet(source, dest, payload, source_ssid=0, dest_ssid=0, compress=False):
    crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    def encode_callsign(callsign, ssid, last=False):
        callsign = callsign.ljust(6)[:6].upper()
        ssid_byte = (0x60 | (ssid << 1) | (1 if last else 0))
        return bytes([ord(c) << 1 for c in callsign]) + bytes([ssid_byte])
    payload_bytes = payload.encode('ascii')
    if compress:
        payload_bytes = zlib.compress(payload_bytes)
        payload = f"C|{payload_bytes.hex()}"
    max_payload = PACLEN - 32
    if len(payload) > max_payload:
        log_event(f"Payload exceeds max ({max_payload}): {len(payload)} bytes, splitting", error_details=True, multi_packet=True)
        parts = [payload[i:i + max_payload] for i in range(0, len(payload), max_payload)]
        packets = []
        for i, part in enumerate(parts):
            tagged_payload = f"{i+1}:{len(parts)}|{part}"
            dest_addr = encode_callsign(dest, dest_ssid, last=False)
            src_addr = encode_callsign(source, source_ssid, last=True)
            address = dest_addr + src_addr
            frame = address + b'\x03\xF0' + tagged_payload.encode('ascii')
            fcs = crc16(frame).to_bytes(2, 'little')
            ax25_packet = b'\x7e' + frame + fcs + b'\x7e'
            packets.append(ax25_packet)
        return packets
    dest_addr = encode_callsign(dest, dest_ssid, last=False)
    src_addr = encode_callsign(source, source_ssid, last=True)
    address = dest_addr + src_addr
    frame = address + b'\x03\xF0' + payload.encode('ascii')
    fcs = crc16(frame).to_bytes(2, 'little')
    ax25_packet = b'\x7e' + frame + fcs + b'\x7e'
    return [ax25_packet]

# CMS Functions
def build_cms_push_index():
    push_index_path = CMS_DIR / 'push_index.json'
    push_dict = {"push": {}}
    now = time.time()
    for fname in CMS_PUSH_DIR.rglob('*.txt'):
        if now - os.path.getmtime(fname) <= CMS_SYNC_MAX_AGE:
            rel_path = fname.relative_to(CMS_PUSH_DIR).as_posix()
            with open(fname, 'rb') as f:
                content = f.read()
                md5 = hashlib.md5(content).hexdigest()
            push_dict["push"][rel_path] = {"md5": md5}
    with open(push_index_path, 'w') as f:
        json.dump(push_dict, f, indent=2)
    with open(push_index_path, 'r') as f:
        push_index_content = f.read()
    client_hash = hashlib.md5(push_index_content.encode()).hexdigest()
    if LOG_CMS_SYNC:
        log_event(f"Computed client push MD5: {client_hash}", cms_sync=True)
    return client_hash

def clean_push_cache():
    now = time.time()
    for fname in CMS_PUSH_DIR.rglob('*.txt'):
        if now - os.path.getmtime(fname) > CMS_SYNC_MAX_AGE:
            os.remove(fname)
            if LOG_CMS_OPERATIONS:
                log_event(f"Removed expired CMS push item: {fname}", cms_operations=True)

# Existing Utility Functions (abridged)
def init_colors():
    # ... unchanged ...

def get_callsign():
    # ... unchanged ...

def load_form_data(form_id):
    # ... unchanged ...

def build_forms_index():
    # ... unchanged ...

if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)
    log_event("Deleted old log file", ui=False, file_io=True)
backup_script()
CALLSIGN = get_callsign()

# Chunk 4 v5.0.0 - Core Display Functions
def redraw_screen(stdscr, sending=False):
    global screen_dirty, form_id, selecting_mode, form_fields, current_field, show_menu, menu_selection, cursor_offset, unread_messages, mode, submission_result, socket_connected
    if not screen_dirty:
        return
    stdscr.erase()
    stdscr.clear()
    RED, GREEN, YELLOW, LIGHT_BLUE = init_colors()
    border = "=" * (COLS - 2)
    max_y, max_x = stdscr.getmaxyx()
    stdscr.addstr(0, 0, border, curses.color_pair(RED))
    if form_fields and mode in ('I', 'S'):
        # ... unchanged form rendering ...
    elif selecting_mode and form_id:
        # ... unchanged mode prompt ...
    elif show_menu and menu_selection == 3:
        # ... unchanged messages screen ...
    elif show_menu and menu_selection == 2:  # CMS Browser
        stdscr.addstr(1, 2, "CMS Browser", curses.color_pair(LIGHT_BLUE))
        categories = [str(Path(d).relative_to(CMS_DIR)) for d, _, _ in os.walk(CMS_DIR) if d != str(CMS_DIR)]
        for i, cat in enumerate(categories[:15], start=3):
            stdscr.addstr(i, 4, cat, curses.color_pair(GREEN))
        stdscr.addstr(21, 2, "= Esc=Back =", curses.color_pair(GREEN))
        if LOG_CMS_UI_STATE:
            log_event(f"CMS Browser rendered: categories={categories[:15]}", cms_ui_state=True)
    else:
        stdscr.addstr(1, 2, "Packet Radio Client", curses.color_pair(LIGHT_BLUE))
        stdscr.addstr(2, 2, f"Callsign: {CALLSIGN}", curses.color_pair(GREEN))
        form_files = set(f[:-4] for f in os.listdir(FORMS_DIR) if f.endswith('.txt'))
        form_list = sorted(form_files)
        stdscr.addstr(3, 2, "Select a form:" + (" *" if unread_messages else ""), curses.color_pair(GREEN))
        for i, local_form_id in enumerate(form_list[:15], 1):
            form_data = load_form_data(local_form_id)
            desc = form_data['desc'].split('~')[0][:30] if form_data else 'Unknown'
            stdscr.addstr(i + 3, 4, f"{i}: {local_form_id} - {desc}", curses.color_pair(GREEN))
        stdscr.addstr(2, 40, f"Direwolf [{'Connected' if socket_connected else 'Disconnected'}]", curses.color_pair(LIGHT_BLUE))
        stdscr.addstr(3, 40, "Comms Log", curses.color_pair(LIGHT_BLUE))
        stdscr.addstr(4, 40, "=" * 15, curses.color_pair(RED))
        for i, (msg, ts) in enumerate(comms_log[-(max_y-6):], start=5):
            if i < max_y-2:
                stdscr.addstr(i, 40, f"{msg[:38]}", curses.color_pair(GREEN))
        if submission_result:
            msg = f"Submission: {submission_result}"
            stdscr.addstr(max_y-3, (max_x - len(msg)) // 2, msg, curses.color_pair(YELLOW) | curses.A_BOLD)
            time.sleep(2)
            submission_result = None
            screen_dirty = True
        if show_menu:
            menu_options = [
                ("Main Screen", True),
                ("Debug Control", True),
                ("CMS Browser", True),  # Added CMS option
                ("Messages", True),
                ("Group Chat", True),
                ("Quit", True)
            ]
            stdscr.addstr(6, 20, "+====================+", curses.color_pair(RED))
            for i, (option, active) in enumerate(menu_options):
                color = GREEN if active else RED
                if i == menu_selection:
                    stdscr.addstr(7 + i, 20, f"| {option:<18} |", curses.color_pair(color) | curses.A_REVERSE)
                else:
                    stdscr.addstr(7 + i, 20, f"| {option:<18} |", curses.color_pair(color))
            stdscr.addstr(13, 20, "| Up/Down=Move       |", curses.color_pair(GREEN))
            stdscr.addstr(14, 20, "| Enter=Sel Esc=Back |", curses.color_pair(GREEN))
            stdscr.addstr(15, 20, "+====================+", curses.color_pair(RED))
        stdscr.addstr(max_y-2, 2, f"-= Commands: D=Menu R=Reconnect 1-{min(len(form_list), 15)}=Select =-", curses.color_pair(GREEN))
    stdscr.addstr(max_y-1, 0, border, curses.color_pair(RED))
    stdscr.refresh()
    screen_dirty = False

# Chunk 5 v5.0.0 - Screen Transition Functions
def display_form_list(stdscr):
    # ... unchanged ...

def display_mode_prompt(stdscr, selected_form_id):
    # ... unchanged ...

def load_form(stdscr, form_id):
    # ... unchanged ...

# Chunk 6 v5.0.0 - AX.25 Communication
def send_to_kiss(stdscr, override_packet):
    global sending, packet_queue, kiss_socket, socket_connected
    sending = True
    packet = override_packet
    if not packet:
        packet = f"{mode.upper()}|{CALLSIGN}|{form_id}|"
        for fid in sorted(form_fields.keys()):
            if fid not in ('L01', 'R01', 'submit', 'cancel'):
                packet += f"{fid}={field_values.get(fid, '')}|"
        packet = packet.rstrip('|')
    ax25_packets = build_ax25_packet(CALLSIGN, "SVR001", packet, source_ssid=CALLSIGN_SSID, dest_ssid=0, compress=(mode in ('G', 'P')))
    for ax25_packet in ax25_packets:
        kiss_frame = b'\xc0\x00' + ax25_packet + b'\xc0'
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                if not kiss_socket or not socket_connected:
                    connect_kiss_socket()
                kiss_socket.send(kiss_frame)
                log_comms(f"{CALLSIGN}>SVR001:{packet}")
                break
            except Exception as e:
                attempts += 1
                if attempts == MAX_RETRIES:
                    log_comms(f"Send failed after {MAX_RETRIES} attempts: {str(e)}")
                    sending = False
                    return
                if kiss_socket:
                    kiss_socket.close()
                    kiss_socket = None
                    socket_connected = False
                time.sleep(1)
    sending = False

def connect_kiss_socket():
    # ... unchanged ...

def kiss_listener(stdscr, stop_event):
    global comms_log, screen_dirty, messages, unread_messages, kiss_socket, last_no_data, sending, submission_result, syncing, packet_queue, socket_connected, form_parts, cms_parts
    log_event(f"Starting KISS listener, connecting to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", debug=True, listener_state=True, thread_state=True)
    buffer = b""
    while not stop_event.is_set():
        try:
            if not kiss_socket or kiss_socket.fileno() < 0:
                connect_kiss_socket()
            while not stop_event.is_set():
                try:
                    data = kiss_socket.recv(512)
                    if data:
                        buffer += data
                        while b'\xC0' in buffer[1:]:
                            start = buffer.find(b'\xC0')
                            end = buffer.find(b'\xC0', start + 1)
                            if end == -1:
                                break
                            frame = buffer[start:end + 1]
                            buffer = buffer[end + 1:]
                            if not frame.startswith(b'\xC0\x00') or not frame.endswith(b'\xC0'):
                                continue
                            ax25_packet = frame[2:-1]
                            dest = ax25_packet[0:7].decode('ascii', errors='ignore').strip()
                            src = ax25_packet[7:14].decode('ascii', errors='ignore').strip()
                            payload_start = 17
                            payload_end = ax25_packet.rfind(b'\x7e') - 2
                            raw_payload = ax25_packet[payload_start:payload_end]
                            payload = raw_payload.decode('ascii', errors='replace').strip()
                            if payload.startswith("C|"):
                                payload = zlib.decompress(bytes.fromhex(payload[2:])).decode('ascii', errors='replace')
                            packet = f"{src}>{dest}:{payload}"
                            log_comms(packet)
                            parts = payload.split('|', 3)
                            if len(parts) != 4:
                                continue
                            function, callsign, form_id, payload_content = parts
                            if ':' in payload_content[:5] and function in ['U', 'R', 'G']:
                                seq_total, content = payload_content.split('|', 1)
                                seq, total = map(int, seq_total.split(':'))
                                key = f"{form_id}"
                                buffer_dict = form_parts if function in ['U', 'R'] else cms_parts
                                buffer_dict.setdefault(key, {})[seq] = content
                                if len(buffer_dict[key]) == total:
                                    full_payload = ''.join(buffer_dict[key][i] for i in range(1, total + 1))
                                    packet_data = (function, callsign, form_id, full_payload)
                                    packet_queue.put_nowait(packet_data)
                                    del buffer_dict[key]
                                continue
                            packet_data = (function, callsign, form_id, payload_content)
                            packet_queue.put_nowait(packet_data)
                            if function == 'U' and CMS_SYNC_ENABLED and form_id.startswith("push/"):
                                file_path = CMS_PUSH_DIR / form_id
                                file_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(file_path, 'w') as f:
                                    f.write(payload_content.replace('~', '\n'))
                                if LOG_CMS_SYNC:
                                    log_event(f"Updated CMS push file {file_path}", cms_sync=True)
                            elif function == 'D' and CMS_SYNC_ENABLED and form_id.startswith("push/"):
                                file_path = CMS_PUSH_DIR / form_id
                                if file_path.exists():
                                    file_path.unlink()
                                    if LOG_CMS_SYNC:
                                        log_event(f"Deleted CMS push file {file_path}", cms_sync=True)
                    else:
                        raise ConnectionError("Fake Direwolf disconnected")
                except socket.timeout:
                    pass
                except Exception as e:
                    log_event(f"Socket error: {str(e)}, closing socket", debug=True, socket_errors=True)
                    if kiss_socket:
                        kiss_socket.close()
                        kiss_socket = None
                        socket_connected = False
                    buffer = b""
                    break
            time.sleep(0.1)
        except Exception as e:
            log_event(f"Listener error: {str(e)}", debug=True, socket_errors=True)
            if kiss_socket:
                kiss_socket.close()
                kiss_socket = None
                socket_connected = False
            buffer = b""
            time.sleep(RETRY_DELAY)

# Chunk 7 v5.0.0 - Main Loop (Navigation & Submit)
def main(stdscr):
    global cursor_offset, current_field, cursor_row, cursor_col, comms_log, screen_dirty, form_id, selecting_mode, field_values, form_fields, show_menu, menu_selection, mode, sending, submission_result, syncing, packet_queue, kiss_socket, socket_connected
    log_event(f"Script v5.0.0 started", debug=True)
    stdscr.resize(ROWS, COLS)
    curses.curs_set(0)
    stdscr.nodelay(True)
    RED, GREEN, YELLOW, LIGHT_BLUE = init_colors()
    cursor_offset = 0
    current_field = None
    cursor_row = None
    cursor_col = None
    comms_log = []
    debug_log = []
    screen_dirty = True
    form_id = None
    selecting_mode = False
    show_menu = False
    menu_selection = 0
    mode = None
    form_fields = {}
    field_values = {}
    sending = False
    submission_result = None
    syncing = False
    socket_connected = False

    stop_event = threading.Event()
    listener_thread = threading.Thread(target=kiss_listener, args=(stdscr, stop_event))
    listener_thread.daemon = True
    listener_thread.start()

    display_form_list(stdscr)
    while True:
        char = stdscr.getch()
        if char == -1:
            time.sleep(0.05)
        else:
            if not form_id and not selecting_mode and not any(form_fields):
                if show_menu:
                    if char == curses.KEY_UP and menu_selection > 0:
                        menu_selection -= 1
                        screen_dirty = True
                    elif char == curses.KEY_DOWN and menu_selection < 5:
                        menu_selection += 1
                        screen_dirty = True
                    elif char == 10:
                        if menu_selection == 0:
                            show_menu = False
                            screen_dirty = True
                        elif menu_selection == 1:
                            # Debug Control TBD
                            show_menu = False
                            screen_dirty = True
                            stdscr.addstr(1, 2, "Debug Control Screen - TBD", curses.color_pair(GREEN))
                            stdscr.refresh()
                            time.sleep(1)
                        elif menu_selection == 2:
                            show_menu = True  # Stay in menu for CMS Browser
                            screen_dirty = True
                        elif menu_selection == 3:
                            show_menu = True
                            screen_dirty = True
                        elif menu_selection == 4:
                            # Group Chat TBD
                            show_menu = False
                            screen_dirty = True
                            stdscr.addstr(1, 2, "Group Chat Screen - TBD", curses.color_pair(GREEN))
                            stdscr.refresh()
                            time.sleep(1)
                        elif menu_selection == 5:
                            stop_event.set()
                            if kiss_socket:
                                kiss_socket.close()
                            break
                    elif char == 27:
                        show_menu = False
                        screen_dirty = True
                else:
                    form_files = [f[:-4] for f in os.listdir(FORMS_DIR) if f.endswith('.txt')]
                    form_files.sort()
                    if chr(char).isdigit() and 1 <= int(chr(char)) <= len(form_files):
                        form_id = form_files[int(chr(char)) - 1]
                        selecting_mode = True
                        display_mode_prompt(stdscr, form_id)
                    elif char == ord('d') or char == ord('D'):
                        show_menu = True
                        menu_selection = 0
                        screen_dirty = True
                    elif char == ord('r') or char == ord('R'):
                        if kiss_socket:
                            kiss_socket.close()
                            kiss_socket = None
                            socket_connected = False
                        screen_dirty = True
            elif selecting_mode:
                # ... unchanged mode selection ...
            elif char == 27 and form_fields:
                # ... unchanged form exit ...
            elif char == 27 and show_menu and menu_selection in (2, 3):  # CMS or Messages
                show_menu = False
                screen_dirty = True
            elif char == 10 and current_field is not None and form_fields:
                # ... unchanged form navigation/submit ...
            # ... other key handling unchanged ...

        while not packet_queue.empty():
            try:
                function, callsign, form_id, payload = packet_queue.get_nowait()
                if function == 'M' and not syncing:
                    if form_id == "PUSH" and CMS_SYNC_ENABLED:
                        server_hash = payload.strip()
                        clean_push_cache()
                        client_hash = build_cms_push_index()
                        if server_hash != client_hash:
                            syncing = True
                            push_index_path = CMS_DIR / 'push_index.json'
                            try:
                                with open(push_index_path, 'r') as f:
                                    push_dict = json.load(f)['push']
                            except FileNotFoundError:
                                push_dict = {}
                            index_parts = [f"{fname}:{md5}" for fname, data in push_dict.items() for md5 in [data['md5']]]
                            index = "|".join(index_parts)
                            update_packet = f"X|{callsign}|PUSH|{index}"
                            send_to_kiss(stdscr, update_packet)
                        else:
                            syncing = False
                    else:
                        # ... unchanged forms M handling ...
                elif function == 'U':
                    screen_dirty = True
                    display_form_list(stdscr)
                    if form_id.startswith("push/"):
                        build_cms_push_index()
                    else:
                        build_forms_index()
                    syncing = False
                elif function == 'D':
                    screen_dirty = True
                    display_form_list(stdscr)
                    if form_id.startswith("push/"):
                        build_cms_push_index()
                    else:
                        build_forms_index()
                    syncing = False
                elif function == 'R':
                    # ... unchanged search results ...
                elif function == 'A':
                    # ... unchanged ACK handling ...
                elif function == 'G':
                    if LOG_CMS_OPERATIONS:
                        log_event(f"Received G (GET): {payload[:50]}", cms_operations=True)
                    # Placeholder for CMS content display (TBD in UI)
                elif function == 'L':
                    if LOG_CMS_OPERATIONS:
                        log_event(f"Received L (LIST): {payload}", cms_operations=True)
                    # Placeholder for CMS list display (TBD in UI)
                packet_queue.task_done()
            except queue.Empty:
                break

        if screen_dirty:
            redraw_screen(stdscr)
        time.sleep(0.05)

# Chunk 8 v5.0.0 - Search Screen
def display_search_screen(stdscr, form_id):
    # ... unchanged ...

# Chunk 9 v5.0.0 - Results Screen
def display_results_screen(stdscr, form_id, payload):
    # ... unchanged ...

# Chunk 10 v5.0.0 - Main Loop (Exit Only)
if __name__ == "__main__":
    print("Starting terminal client...")
    try:
        log_event("Client startup initiated", debug=True)
        curses.wrapper(main)
    except Exception as e:
        log_event(f"Curses failed: {str(e)}", debug=True, socket_errors=True)
        raise

# Chunk 11 v5.0.0 - Design Goals and Statuses
# DESIGN GOALS AND CHANGES:
# - See client_mini_revisions_20250322_v5.0.0.txt for this update (v5.0.0)
# - Full history in PacketRadioTerminalServiceManual [REVISION_SUMMARY]
