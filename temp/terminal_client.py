#!/usr/bin/env python3
# terminal_client.py
# Version 5.0.0 - 2025-03-22  # CHANGE v5.0.0: Added CMS with push sync, compression, menu access

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
AGW_HOST = '127.0.0.1'
AGW_PORT = 8000
LOG_FILE = os.path.join(INSTALL_DIR, "skippys_messups.log")
FORMS_DIR = os.path.join(INSTALL_DIR, "forms")
BACKUP_DIR = os.path.join(INSTALL_DIR, "backups")
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds
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
        'log_callsign_prompt': 'True',
        'log_connectivity': 'True',
        'log_debug': 'True',
        'log_comm_details': 'False',
        'log_form_updates': 'False',
        'log_submission': 'True',
        'log_ui_state': 'False',
        'log_packet_details': 'False',
        'log_segment_status': 'True',
        'log_submission_details': 'True',
        'log_submission_payload': 'True',
        'log_segment_failure': 'True',
        'log_socket_state': 'True',
        'log_retries': 'True',
        'log_ui_transitions': 'False',
        'log_ack_processing': 'True',
        'log_send_state': 'True',
        'log_listener_state': 'True',
        'log_search_query': 'True',
        'log_search_results': 'True',
        'log_screen_state': 'True',
        'log_field_state': 'False',
        'log_submission_flow': 'True',
        'log_debug_forms': 'False',
        'log_debug_sync': 'True',
        'log_cursor_movement': 'False',
        'log_packet_timing': 'False',
        'log_error_details': 'True',
        'log_packet_build': 'True',
        'log_packet_parse': 'False',
        'log_sync_state': 'True',
        'log_sync_md5': 'False',
        'log_sync_forms': 'False',
        'log_sync_packets': 'True',
        'log_packet_integrity': 'True',
        'log_listener_retries': 'True',
        'log_socket_reset': 'True',
        'log_connection_success': 'True',
        'log_packet_fragments': 'True',
        'log_sync_mismatches': 'True',
        'log_redraw_triggers': 'False',
        'log_form_deletion': 'True',
        'log_sync_start': 'True',
        'log_sync_completion': 'True',
        'log_form_exit': 'True',
        'log_key_context': 'False',
        'log_mode_switch': 'True',
        'log_packet_queue': 'True',
        'log_listener_queue': 'True',
        'log_ui_packet_handling': 'True',
        'log_queue_state': 'False',
        'log_connection_attempts': 'True',
        'log_packet_drop': 'True',
        'log_thread_state': 'True',
        'log_column_navigation': 'True',
        'log_form_layout': 'True',
        'log_row_movement': 'True',
        'log_form_display_error': 'True',
        'log_ui_render': 'False',
        'log_socket_errors': 'True',
        'log_form_ui_layout': 'True',
        'log_input_field_state': 'True',
        'log_kiss_framing': 'True',
        'log_ax25_state': 'True',
        'log_ax25_packet': 'True',
        'log_ax25_parse_error': 'True',
        'log_kiss_packet_received': 'True',
        'log_packet_validation': 'True',
        'log_md5_comparison': 'True',
        'log_packet_relay': 'True',
        'log_ui_redraw': 'True',
        'log_socket_send_bytes': 'False',
        'log_socket_send_failure': 'True',
        'log_socket_reconnect': 'True',
        'log_socket_status': 'True',
        'log_socket_send_raw': 'True',
        'log_socket_buffer': 'True',
        'log_ui_comms_log': 'True',
        'log_packet_send_time': 'True',
        'log_packet_enqueue_time': 'True',
        'log_packet_dequeue_time': 'True',
        'log_queue_size': 'True',
        'log_redraw_timing': 'True',
        'log_kiss_receive_buffer': 'True',
        'log_kiss_frame_timing': 'True',
        'log_packet_content': 'True',
        'log_socket_send_attempt': 'True',
        'log_ui_packet_display': 'True',
        'log_packet_structure': 'True',
        'log_socket_validation': 'True',
        'log_packet_transmission': 'True',
        'log_ax25_build': 'True',
        'log_ax25_validation': 'True',
        'log_kiss_validation': 'True',
        'log_fcs_calculation': 'True',
        'log_json_rebuild': 'True',
        'log_diff_state': 'True',
        'log_delimiter_usage': 'True',
        'log_sync_index': 'True',
        'log_packet_format': 'True',
        'log_packet_raw_decode': 'True',
        'log_form_file_write': 'True',
        'log_form_field_parse': 'True',
        'log_newline_handling': 'True',
        'log_file_content': 'True',
        'log_command_validation': 'True',
        'log_packet_handling': 'True',
        'log_file_io': 'True',
        'log_multi_packet': 'True',
        'log_buffer_management': 'True',
        # New CMS logging toggles
        'log_cms_sync': 'True',
        'log_cms_operations': 'True',
        'log_cms_packet_build': 'True',
        'log_cms_ui_state': 'False'  # Off to reduce spam
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
LOG_CALLSIGN_PROMPT = config.getboolean('Settings', 'log_callsign_prompt', fallback=True)
LOG_CONNECTIVITY = config.getboolean('Settings', 'log_connectivity', fallback=True)
LOG_DEBUG = config.getboolean('Settings', 'log_debug', fallback=True)
LOG_COMM_DETAILS = config.getboolean('Settings', 'log_comm_details', fallback=False)
LOG_FORM_UPDATES = config.getboolean('Settings', 'log_form_updates', fallback=False)
LOG_SUBMISSION = config.getboolean('Settings', 'log_submission', fallback=True)
LOG_UI_STATE = config.getboolean('Settings', 'log_ui_state', fallback=False)
LOG_PACKET_DETAILS = config.getboolean('Settings', 'log_packet_details', fallback=False)
LOG_SEGMENT_STATUS = config.getboolean('Settings', 'log_segment_status', fallback=True)
LOG_SUBMISSION_DETAILS = config.getboolean('Settings', 'log_submission_details', fallback=True)
LOG_SUBMISSION_PAYLOAD = config.getboolean('Settings', 'log_submission_payload', fallback=True)
LOG_SEGMENT_FAILURE = config.getboolean('Settings', 'log_segment_failure', fallback=True)
LOG_SOCKET_STATE = config.getboolean('Settings', 'log_socket_state', fallback=True)
LOG_RETRIES = config.getboolean('Settings', 'log_retries', fallback=True)
LOG_UI_TRANSITIONS = config.getboolean('Settings', 'log_ui_transitions', fallback=False)
LOG_ACK_PROCESSING = config.getboolean('Settings', 'log_ack_processing', fallback=True)
LOG_SEND_STATE = config.getboolean('Settings', 'log_send_state', fallback=True)
LOG_LISTENER_STATE = config.getboolean('Settings', 'log_listener_state', fallback=True)
LOG_SEARCH_QUERY = config.getboolean('Settings', 'log_search_query', fallback=True)
LOG_SEARCH_RESULTS = config.getboolean('Settings', 'log_search_results', fallback=True)
LOG_SCREEN_STATE = config.getboolean('Settings', 'log_screen_state', fallback=True)
LOG_FIELD_STATE = config.getboolean('Settings', 'log_field_state', fallback=False)
LOG_SUBMISSION_FLOW = config.getboolean('Settings', 'log_submission_flow', fallback=True)
LOG_DEBUG_FORMS = config.getboolean('Settings', 'log_debug_forms', fallback=False)
LOG_DEBUG_SYNC = config.getboolean('Settings', 'log_debug_sync', fallback=True)
LOG_CURSOR_MOVEMENT = config.getboolean('Settings', 'log_cursor_movement', fallback=False)
LOG_PACKET_TIMING = config.getboolean('Settings', 'log_packet_timing', fallback=False)
LOG_ERROR_DETAILS = config.getboolean('Settings', 'log_error_details', fallback=True)
LOG_PACKET_BUILD = config.getboolean('Settings', 'log_packet_build', fallback=True)
LOG_PACKET_PARSE = config.getboolean('Settings', 'log_packet_parse', fallback=False)
LOG_SYNC_STATE = config.getboolean('Settings', 'log_sync_state', fallback=True)
LOG_SYNC_MD5 = config.getboolean('Settings', 'log_sync_md5', fallback=False)
LOG_SYNC_FORMS = config.getboolean('Settings', 'log_sync_forms', fallback=False)
LOG_SYNC_PACKETS = config.getboolean('Settings', 'log_sync_packets', fallback=True)
LOG_PACKET_INTEGRITY = config.getboolean('Settings', 'log_packet_integrity', fallback=True)
LOG_LISTENER_RETRIES = config.getboolean('Settings', 'log_listener_retries', fallback=True)
LOG_SOCKET_RESET = config.getboolean('Settings', 'log_socket_reset', fallback=True)
LOG_CONNECTION_SUCCESS = config.getboolean('Settings', 'log_connection_success', fallback=True)
LOG_PACKET_FRAGMENTS = config.getboolean('Settings', 'log_packet_fragments', fallback=True)
LOG_SYNC_MISMATCHES = config.getboolean('Settings', 'log_sync_mismatches', fallback=True)
LOG_REDRAW_TRIGGERS = config.getboolean('Settings', 'log_redraw_triggers', fallback=False)
LOG_FORM_DELETION = config.getboolean('Settings', 'log_form_deletion', fallback=True)
LOG_SYNC_START = config.getboolean('Settings', 'log_sync_start', fallback=True)
LOG_SYNC_COMPLETION = config.getboolean('Settings', 'log_sync_completion', fallback=True)
LOG_FORM_EXIT = config.getboolean('Settings', 'log_form_exit', fallback=True)
LOG_KEY_CONTEXT = config.getboolean('Settings', 'log_key_context', fallback=False)
LOG_MODE_SWITCH = config.getboolean('Settings', 'log_mode_switch', fallback=True)
LOG_PACKET_QUEUE = config.getboolean('Settings', 'log_packet_queue', fallback=True)
LOG_LISTENER_QUEUE = config.getboolean('Settings', 'log_listener_queue', fallback=True)
LOG_UI_PACKET_HANDLING = config.getboolean('Settings', 'log_ui_packet_handling', fallback=True)
LOG_QUEUE_STATE = config.getboolean('Settings', 'log_queue_state', fallback=False)
LOG_CONNECTION_ATTEMPTS = config.getboolean('Settings', 'log_connection_attempts', fallback=True)
LOG_PACKET_DROP = config.getboolean('Settings', 'log_packet_drop', fallback=True)
LOG_THREAD_STATE = config.getboolean('Settings', 'log_thread_state', fallback=True)
LOG_COLUMN_NAVIGATION = config.getboolean('Settings', 'log_column_navigation', fallback=True)
LOG_FORM_LAYOUT = config.getboolean('Settings', 'log_form_layout', fallback=True)
LOG_ROW_MOVEMENT = config.getboolean('Settings', 'log_row_movement', fallback=True)
LOG_FORM_DISPLAY_ERROR = config.getboolean('Settings', 'log_form_display_error', fallback=True)
LOG_UI_RENDER = config.getboolean('Settings', 'log_ui_render', fallback=False)
LOG_SOCKET_ERRORS = config.getboolean('Settings', 'log_socket_errors', fallback=True)
LOG_FORM_UI_LAYOUT = config.getboolean('Settings', 'log_form_ui_layout', fallback=True)
LOG_INPUT_FIELD_STATE = config.getboolean('Settings', 'log_input_field_state', fallback=True)
LOG_KISS_FRAMING = config.getboolean('Settings', 'log_kiss_framing', fallback=True)
LOG_AX25_STATE = config.getboolean('Settings', 'log_ax25_state', fallback=True)
LOG_AX25_PACKET = config.getboolean('Settings', 'log_ax25_packet', fallback=True)
LOG_AX25_PARSE_ERROR = config.getboolean('Settings', 'log_ax25_parse_error', fallback=True)
LOG_KISS_PACKET_RECEIVED = config.getboolean('Settings', 'log_kiss_packet_received', fallback=True)
LOG_PACKET_VALIDATION = config.getboolean('Settings', 'log_packet_validation', fallback=True)
LOG_MD5_COMPARISON = config.getboolean('Settings', 'log_md5_comparison', fallback=True)
LOG_PACKET_RELAY = config.getboolean('Settings', 'log_packet_relay', fallback=True)
LOG_UI_REDRAW = config.getboolean('Settings', 'log_ui_redraw', fallback=True)
LOG_SOCKET_SEND_BYTES = config.getboolean('Settings', 'log_socket_send_bytes', fallback=False)
LOG_SOCKET_SEND_FAILURE = config.getboolean('Settings', 'log_socket_send_failure', fallback=True)
LOG_SOCKET_RECONNECT = config.getboolean('Settings', 'log_socket_reconnect', fallback=True)
LOG_SOCKET_STATUS = config.getboolean('Settings', 'log_socket_status', fallback=True)
LOG_SOCKET_SEND_RAW = config.getboolean('Settings', 'log_socket_send_raw', fallback=True)
LOG_SOCKET_BUFFER = config.getboolean('Settings', 'log_socket_buffer', fallback=True)
LOG_UI_COMMS_LOG = config.getboolean('Settings', 'log_ui_comms_log', fallback=True)
LOG_PACKET_SEND_TIME = config.getboolean('Settings', 'log_packet_send_time', fallback=True)
LOG_PACKET_ENQUEUE_TIME = config.getboolean('Settings', 'log_packet_enqueue_time', fallback=True)
LOG_PACKET_DEQUEUE_TIME = config.getboolean('Settings', 'log_packet_dequeue_time', fallback=True)
LOG_QUEUE_SIZE = config.getboolean('Settings', 'log_queue_size', fallback=True)
LOG_REDRAW_TIMING = config.getboolean('Settings', 'log_redraw_timing', fallback=True)
LOG_KISS_RECEIVE_BUFFER = config.getboolean('Settings', 'log_kiss_receive_buffer', fallback=True)
LOG_KISS_FRAME_TIMING = config.getboolean('Settings', 'log_kiss_frame_timing', fallback=True)
LOG_PACKET_CONTENT = config.getboolean('Settings', 'log_packet_content', fallback=True)
LOG_SOCKET_SEND_ATTEMPT = config.getboolean('Settings', 'log_socket_send_attempt', fallback=True)
LOG_UI_PACKET_DISPLAY = config.getboolean('Settings', 'log_ui_packet_display', fallback=True)
LOG_PACKET_STRUCTURE = config.getboolean('Settings', 'log_packet_structure', fallback=True)
LOG_SOCKET_VALIDATION = config.getboolean('Settings', 'log_socket_validation', fallback=True)
LOG_PACKET_TRANSMISSION = config.getboolean('Settings', 'log_packet_transmission', fallback=True)
LOG_AX25_BUILD = config.getboolean('Settings', 'log_ax25_build', fallback=True)
LOG_AX25_VALIDATION = config.getboolean('Settings', 'log_ax25_validation', fallback=True)
LOG_KISS_VALIDATION = config.getboolean('Settings', 'log_kiss_validation', fallback=True)
LOG_FCS_CALCULATION = config.getboolean('Settings', 'log_fcs_calculation', fallback=True)
LOG_JSON_REBUILD = config.getboolean('Settings', 'log_json_rebuild', fallback=True)
LOG_DIFF_STATE = config.getboolean('Settings', 'log_diff_state', fallback=True)
LOG_DELIMITER_USAGE = config.getboolean('Settings', 'log_delimiter_usage', fallback=True)
LOG_SYNC_INDEX = config.getboolean('Settings', 'log_sync_index', fallback=True)
LOG_PACKET_FORMAT = config.getboolean('Settings', 'log_packet_format', fallback=True)
LOG_PACKET_RAW_DECODE = config.getboolean('Settings', 'log_packet_raw_decode', fallback=True)
LOG_FORM_FILE_WRITE = config.getboolean('Settings', 'log_form_file_write', fallback=True)
LOG_FORM_FIELD_PARSE = config.getboolean('Settings', 'log_form_field_parse', fallback=True)
LOG_NEWLINE_HANDLING = config.getboolean('Settings', 'log_newline_handling', fallback=True)
LOG_FILE_CONTENT = config.getboolean('Settings', 'log_file_content', fallback=True)
LOG_COMMAND_VALIDATION = config.getboolean('Settings', 'log_command_validation', fallback=True)
LOG_PACKET_HANDLING = config.getboolean('Settings', 'log_packet_handling', fallback=True)
LOG_FILE_IO = config.getboolean('Settings', 'log_file_io', fallback=True)
LOG_MULTI_PACKET = config.getboolean('Settings', 'log_multi_packet', fallback=True)
LOG_BUFFER_MANAGEMENT = config.getboolean('Settings', 'log_buffer_management', fallback=True)
LOG_CMS_SYNC = config.getboolean('Settings', 'log_cms_sync', fallback=True)
LOG_CMS_OPERATIONS = config.getboolean('Settings', 'log_cms_operations', fallback=True)
LOG_CMS_PACKET_BUILD = config.getboolean('Settings', 'log_cms_packet_build', fallback=True)
LOG_CMS_UI_STATE = config.getboolean('Settings', 'log_cms_ui_state', fallback=False)

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
        if LOG_REDRAW_TRIGGERS:
            log_event("screen_dirty set by log_event (UI log)", redraw_triggers=True)
        if LOG_UI_COMMS_LOG:
            log_event(f"Comms Log updated: {message}", ui_comms_log=True)
    if debug and LOG_DEBUG: debug_log.append((message, timestamp))
    if submission and LOG_SUBMISSION: debug_log.append((message, timestamp))
    if ui_state and LOG_UI_STATE: debug_log.append((message, timestamp))
    if packet and LOG_PACKET_DETAILS: debug_log.append((message, timestamp))
    if segment and LOG_SEGMENT_STATUS: debug_log.append((message, timestamp))
    if submission_details and LOG_SUBMISSION_DETAILS: debug_log.append((message, timestamp))
    if payload and LOG_SUBMISSION_PAYLOAD: debug_log.append((message, timestamp))
    if segment_failure and LOG_SEGMENT_FAILURE: debug_log.append((message, timestamp))
    if socket_state and LOG_SOCKET_STATE: debug_log.append((message, timestamp))
    if retries and LOG_RETRIES: debug_log.append((message, timestamp))
    if ui_transitions and LOG_UI_TRANSITIONS: debug_log.append((message, timestamp))
    if ack_processing and LOG_ACK_PROCESSING: debug_log.append((message, timestamp))
    if send_state and LOG_SEND_STATE: debug_log.append((message, timestamp))
    if listener_state and LOG_LISTENER_STATE: debug_log.append((message, timestamp))
    if search_query and LOG_SEARCH_QUERY: debug_log.append((message, timestamp))
    if search_results and LOG_SEARCH_RESULTS: debug_log.append((message, timestamp))
    if screen_state and LOG_SCREEN_STATE: debug_log.append((message, timestamp))
    if field_state and LOG_FIELD_STATE: debug_log.append((message, timestamp))
    if submission_flow and LOG_SUBMISSION_FLOW: debug_log.append((message, timestamp))
    if cursor_movement and LOG_CURSOR_MOVEMENT: debug_log.append((message, timestamp))
    if packet_timing and LOG_PACKET_TIMING: debug_log.append((message, timestamp))
    if error_details and LOG_ERROR_DETAILS: debug_log.append((message, timestamp))
    if packet_build and LOG_PACKET_BUILD: debug_log.append((message, timestamp))
    if packet_parse and LOG_PACKET_PARSE: debug_log.append((message, timestamp))
    if sync_state and LOG_SYNC_STATE: debug_log.append((message, timestamp))
    if sync_md5 and LOG_SYNC_MD5: debug_log.append((message, timestamp))
    if sync_forms and LOG_SYNC_FORMS: debug_log.append((message, timestamp))
    if sync_packets and LOG_SYNC_PACKETS: debug_log.append((message, timestamp))
    if packet_integrity and LOG_PACKET_INTEGRITY: debug_log.append((message, timestamp))
    if listener_retries and LOG_LISTENER_RETRIES: debug_log.append((message, timestamp))
    if socket_reset and LOG_SOCKET_RESET: debug_log.append((message, timestamp))
    if connection_success and LOG_CONNECTION_SUCCESS: debug_log.append((message, timestamp))
    if packet_fragments and LOG_PACKET_FRAGMENTS: debug_log.append((message, timestamp))
    if sync_mismatches and LOG_SYNC_MISMATCHES: debug_log.append((message, timestamp))
    if redraw_triggers and LOG_REDRAW_TRIGGERS: debug_log.append((message, timestamp))
    if form_deletion and LOG_FORM_DELETION: debug_log.append((message, timestamp))
    if sync_start and LOG_SYNC_START: debug_log.append((message, timestamp))
    if sync_completion and LOG_SYNC_COMPLETION: debug_log.append((message, timestamp))
    if form_exit and LOG_FORM_EXIT: debug_log.append((message, timestamp))
    if key_context and LOG_KEY_CONTEXT: debug_log.append((message, timestamp))
    if mode_switch and LOG_MODE_SWITCH: debug_log.append((message, timestamp))
    if packet_queue and LOG_PACKET_QUEUE: debug_log.append((message, timestamp))
    if listener_queue and LOG_LISTENER_QUEUE: debug_log.append((message, timestamp))
    if ui_packet_handling and LOG_UI_PACKET_HANDLING: debug_log.append((message, timestamp))
    if queue_state and LOG_QUEUE_STATE: debug_log.append((message, timestamp))
    if connection_attempts and LOG_CONNECTION_ATTEMPTS: debug_log.append((message, timestamp))
    if packet_drop and LOG_PACKET_DROP: debug_log.append((message, timestamp))
    if thread_state and LOG_THREAD_STATE: debug_log.append((message, timestamp))
    if column_navigation and LOG_COLUMN_NAVIGATION: debug_log.append((message, timestamp))
    if form_layout and LOG_FORM_LAYOUT: debug_log.append((message, timestamp))
    if row_movement and LOG_ROW_MOVEMENT: debug_log.append((message, timestamp))
    if form_display_error and LOG_FORM_DISPLAY_ERROR: debug_log.append((message, timestamp))
    if ui_render and LOG_UI_RENDER: debug_log.append((message, timestamp))
    if socket_errors and LOG_SOCKET_ERRORS: debug_log.append((message, timestamp))
    if form_ui_layout and LOG_FORM_UI_LAYOUT: debug_log.append((message, timestamp))
    if input_field_state and LOG_INPUT_FIELD_STATE: debug_log.append((message, timestamp))
    if kiss_framing and LOG_KISS_FRAMING: debug_log.append((message, timestamp))
    if ax25_state and LOG_AX25_STATE: debug_log.append((message, timestamp))
    if ax25_packet and LOG_AX25_PACKET: debug_log.append((message, timestamp))
    if ax25_parse_error and LOG_AX25_PARSE_ERROR: debug_log.append((message, timestamp))
    if kiss_packet_received and LOG_KISS_PACKET_RECEIVED: debug_log.append((message, timestamp))
    if packet_validation and LOG_PACKET_VALIDATION: debug_log.append((message, timestamp))
    if md5_comparison and LOG_MD5_COMPARISON: debug_log.append((message, timestamp))
    if packet_relay and LOG_PACKET_RELAY: debug_log.append((message, timestamp))
    if ui_redraw and LOG_UI_REDRAW: debug_log.append((message, timestamp))
    if socket_send_bytes and LOG_SOCKET_SEND_BYTES: debug_log.append((message, timestamp))
    if socket_send_failure and LOG_SOCKET_SEND_FAILURE: debug_log.append((message, timestamp))
    if socket_reconnect and LOG_SOCKET_RECONNECT: debug_log.append((message, timestamp))
    if socket_status and LOG_SOCKET_STATUS: debug_log.append((message, timestamp))
    if socket_send_raw and LOG_SOCKET_SEND_RAW: debug_log.append((message, timestamp))
    if socket_buffer and LOG_SOCKET_BUFFER: debug_log.append((message, timestamp))
    if ui_comms_log and LOG_UI_COMMS_LOG: debug_log.append((message, timestamp))
    if packet_send_time and LOG_PACKET_SEND_TIME: debug_log.append((message, timestamp))
    if packet_enqueue_time and LOG_PACKET_ENQUEUE_TIME: debug_log.append((message, timestamp))
    if packet_dequeue_time and LOG_PACKET_DEQUEUE_TIME: debug_log.append((message, timestamp))
    if queue_size and LOG_QUEUE_SIZE: debug_log.append((message, timestamp))
    if redraw_timing and LOG_REDRAW_TIMING: debug_log.append((message, timestamp))
    if kiss_receive_buffer and LOG_KISS_RECEIVE_BUFFER: debug_log.append((message, timestamp))
    if kiss_frame_timing and LOG_KISS_FRAME_TIMING: debug_log.append((message, timestamp))
    if packet_content and LOG_PACKET_CONTENT: debug_log.append((message, timestamp))
    if socket_send_attempt and LOG_SOCKET_SEND_ATTEMPT: debug_log.append((message, timestamp))
    if ui_packet_display and LOG_UI_PACKET_DISPLAY: debug_log.append((message, timestamp))
    if packet_structure and LOG_PACKET_STRUCTURE: debug_log.append((message, timestamp))
    if socket_validation and LOG_SOCKET_VALIDATION: debug_log.append((message, timestamp))
    if packet_transmission and LOG_PACKET_TRANSMISSION: debug_log.append((message, timestamp))
    if ax25_build and LOG_AX25_BUILD: debug_log.append((message, timestamp))
    if ax25_validation and LOG_AX25_VALIDATION: debug_log.append((message, timestamp))
    if kiss_validation and LOG_KISS_VALIDATION: debug_log.append((message, timestamp))
    if fcs_calculation and LOG_FCS_CALCULATION: debug_log.append((message, timestamp))
    if json_rebuild and LOG_JSON_REBUILD: debug_log.append((message, timestamp))
    if diff_state and LOG_DIFF_STATE: debug_log.append((message, timestamp))
    if delimiter_usage and LOG_DELIMITER_USAGE: debug_log.append((message, timestamp))
    if sync_index and LOG_SYNC_INDEX: debug_log.append((message, timestamp))
    if packet_format and LOG_PACKET_FORMAT: debug_log.append((message, timestamp))
    if packet_raw_decode and LOG_PACKET_RAW_DECODE: debug_log.append((message, timestamp))
    if form_file_write and LOG_FORM_FILE_WRITE: debug_log.append((message, timestamp))
    if form_field_parse and LOG_FORM_FIELD_PARSE: debug_log.append((message, timestamp))
    if newline_handling and LOG_NEWLINE_HANDLING: debug_log.append((message, timestamp))
    if file_content and LOG_FILE_CONTENT: debug_log.append((message, timestamp))
    if command_validation and LOG_COMMAND_VALIDATION: debug_log.append((message, timestamp))
    if packet_handling and LOG_PACKET_HANDLING: debug_log.append((message, timestamp))
    if file_io and LOG_FILE_IO: debug_log.append((message, timestamp))
    if multi_packet and LOG_MULTI_PACKET: debug_log.append((message, timestamp))
    if buffer_management and LOG_BUFFER_MANAGEMENT: debug_log.append((message, timestamp))
    if cms_sync and LOG_CMS_SYNC: debug_log.append(("CMS Sync: " + message, timestamp))
    if cms_operations and LOG_CMS_OPERATIONS: debug_log.append(("CMS Operation: " + message, timestamp))
    if cms_packet_build and LOG_CMS_PACKET_BUILD: debug_log.append(("CMS Packet Build: " + message, timestamp))
    if cms_ui_state and LOG_CMS_UI_STATE: debug_log.append(("CMS UI State: " + message, timestamp))

def log_comms(message):
    if not message.endswith(":M|SVR001|NONE|") and not message.endswith(":M|SVR001|PUSH|"):
        log_event(message, ui=True)
    if LOG_PACKET_CONTENT:
        log_event(f"Packet content logged: {message}", packet_content=True)

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
        encoded = bytes([ord(c) << 1 for c in callsign]) + bytes([ssid_byte])
        if LOG_AX25_BUILD:
            log_event(f"Encoded callsign {callsign} (SSID={ssid}, last={last}): {encoded.hex()}", ax25_build=True)
        return encoded
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
            if LOG_PAYLOAD_VALIDATION:
                log_event(f"Payload part {i+1}/{len(parts)}: {tagged_payload}", payload_validation=True, multi_packet=True)
            dest_addr = encode_callsign(dest, dest_ssid, last=False)
            src_addr = encode_callsign(source, source_ssid, last=True)
            address = dest_addr + src_addr
            frame = address + b'\x03\xF0' + tagged_payload.encode('ascii')
            fcs = crc16(frame).to_bytes(2, 'little')
            ax25_packet = b'\x7e' + frame + fcs + b'\x7e'
            if LOG_AX25_PACKET:
                log_event(f"Built AX.25 packet {i+1}/{len(parts)}: {ax25_packet.hex()}", ax25_packet=True, multi_packet=True)
            packets.append(ax25_packet)
        return packets
    dest_addr = encode_callsign(dest, dest_ssid, last=False)
    src_addr = encode_callsign(source, source_ssid, last=True)
    address = dest_addr + src_addr
    frame = address + b'\x03\xF0' + payload.encode('ascii')
    fcs = crc16(frame).to_bytes(2, 'little')
    ax25_packet = b'\x7e' + frame + fcs + b'\x7e'
    if LOG_AX25_PACKET:
        log_event(f"Built AX.25 packet: {ax25_packet.hex()}", ax25_packet=True)
    if LOG_DELIMITER_USAGE:
        log_event(f"Payload delimiters in AX.25 packet: {payload.count('|')} pipes", delimiter_usage=True)
    if len(ax25_packet) < 20:
        log_event(f"AX.25 packet too short: {len(ax25_packet)} bytes", ax25_validation=True, error_details=True)
    if LOG_AX25_VALIDATION:
        log_event(f"AX.25 packet validated: len={len(ax25_packet)}, flags={ax25_packet[0]:02x}/{ax25_packet[-1]:02x}", ax25_validation=True)
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

def init_colors():
    log_event("Initializing colors", debug=True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
    return 1, 2, 3, 4

def get_callsign():
    global CALLSIGN, CALLSIGN_SSID
    CALLSIGN = config.get('Settings', 'callsign', fallback='CLT001')
    CALLSIGN_SSID = config.getint('Settings', 'callsign_ssid', fallback=0)
    while not CALLSIGN:
        if LOG_CALLSIGN_PROMPT:
            log_event("Prompting for callsign", ui=False)
        print("Enter Your Callsign (e.g., KB8XYZ, required): ", end='', flush=True)
        CALLSIGN = input().strip().upper()
        if not CALLSIGN:
            print("Callsign cannot be empty—try again")
            time.sleep(1)
        else:
            config['Settings']['callsign'] = CALLSIGN
            config['Settings']['callsign_ssid'] = str(CALLSIGN_SSID)
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
            log_event(f"Callsign set to {CALLSIGN} with SSID {CALLSIGN_SSID}", ui=False, file_io=True)
    return CALLSIGN

def load_form_data(form_id):
    file_path = os.path.join(FORMS_DIR, f"{form_id}.txt")
    if not os.path.exists(file_path):
        log_event(f"Form file not found: {file_path}", debug=True, file_io=True)
        return None
    form_data = {'desc': '', 'fields': {}}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('desc:'):
                form_data['desc'] = line.split(':', 1)[1]
            elif ',' in line and len(line.split(',')) == 5:
                fid, label, row, col, length = line.split(',')
                length_cleaned = re.sub(r'[^0-9]', '', length) or '256'
                if length != length_cleaned:
                    if LOG_FORM_FIELD_PARSE:
                        log_event(f"Parsed field in {form_id}: {line} -> length cleaned to {length_cleaned}", form_field_parse=True)
                try:
                    form_data['fields'][fid] = {
                        'label': label,
                        'row': int(row),
                        'col': int(col),
                        'len': int(length_cleaned)
                    }
                except ValueError as e:
                    log_event(f"Invalid field in {form_id}: {line}, error: {e}", debug=True, form_field_parse=True)
            else:
                log_event(f"Invalid line in {form_id}.txt: {line}", debug=True)
    if LOG_FORM_LAYOUT:
        log_event(f"Loaded form {form_id}: {form_data['fields']}", form_layout=True)
    if LOG_FILE_IO:
        log_event(f"Loaded form data from {file_path}", file_io=True)
    return form_data

def update_form_lengths():
    if not os.path.exists(FORMS_DIR) or not os.listdir(FORMS_DIR):
        log_event("No forms yet—awaiting server", debug=True)
        return
    log_event("TEMPORARY: Starting form length update to 256", debug=True)
    for form_file in os.listdir(FORMS_DIR):
        if form_file.endswith('.txt'):
            file_path = os.path.join(FORMS_DIR, form_file)
            lines = []
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('desc:'):
                        lines.append(line.strip())
                    elif ',' in line and len(line.split(',')) == 5:
                        fid, label, row, col, _ = line.strip().split(',')
                        lines.append(f"{fid},{label},{row},{col},256")
                    else:
                        log_event(f"Skipping invalid line in {form_file}: {line.strip()}", debug=True)
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines) + '\n')
            if LOG_DEBUG_FORMS:
                log_event(f"TEMPORARY: Updated {form_file} fields to len=256", debug=True)
            if LOG_FILE_IO:
                log_event(f"Updated form lengths in {file_path}", file_io=True)
    log_event("TEMPORARY: Form length update complete", debug=True)

def build_forms_index():
    forms_index_path = os.path.join(FORMS_DIR, 'forms_index.json')
    forms_dict = {"forms": {}}
    if os.path.exists(FORMS_DIR):
        for fname in sorted(os.listdir(FORMS_DIR)):
            if fname.endswith('.txt'):
                file_path = os.path.join(FORMS_DIR, fname)
                with open(file_path, 'rb') as f:
                    content = f.read()
                    md5 = hashlib.md5(content).hexdigest()
                form_id = fname[:-4]
                forms_dict["forms"][form_id] = {"md5": md5}
                if LOG_SYNC_FORMS:
                    log_event(f"Indexed {form_id} with MD5: {md5}", sync_forms=True)
    with open(forms_index_path, 'w') as f:
        json.dump(forms_dict, f, indent=2)
    if LOG_JSON_REBUILD:
        log_event(f"Rebuilt forms_index.json at {forms_index_path}", json_rebuild=True)
    if LOG_FILE_IO:
        log_event(f"Wrote forms_index.json to {forms_index_path}", file_io=True)
    with open(forms_index_path, 'r') as f:
        forms_index_content = f.read()
    client_hash = hashlib.md5(forms_index_content.encode()).hexdigest()
    if LOG_SYNC_MD5:
        log_event(f"Computed client MD5 from forms_index.json: {client_hash}", sync_md5=True)
    if LOG_FILE_IO:
        log_event(f"Read forms_index.json from {forms_index_path}", file_io=True)
    return client_hash

if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)
    log_event("Deleted old log file", ui=False, file_io=True)
backup_script()
CALLSIGN = get_callsign()


# Chunk 4 v5.0.0 - Core Display Functions
def move_cursor(stdscr, row, col):
    global cursor_row, cursor_col, screen_dirty
    cursor_row, cursor_col = min(max(row, 0), ROWS-1), min(max(col, 0), COLS-1)
    screen_dirty = True
    if LOG_REDRAW_TRIGGERS:
        log_event("screen_dirty set by move_cursor", redraw_triggers=True)
    redraw_screen(stdscr)

def redraw_screen(stdscr, sending=False):
    global screen_dirty, form_id, selecting_mode, form_fields, current_field, show_menu, menu_selection, cursor_offset, unread_messages, mode, submission_result, socket_connected
    if not screen_dirty:
        return
    redraw_start = time.time()
    stdscr.erase()
    stdscr.clear()
    RED, GREEN, YELLOW, LIGHT_BLUE = init_colors()
    border = "=" * (COLS - 2)
    max_y, max_x = stdscr.getmaxyx()
    stdscr.addstr(0, 0, border, curses.color_pair(RED))
    if form_fields and any(form_fields) and mode in ('I', 'S'):
        max_form_row = 18
        form_id_display = form_fields.get(next(iter(form_fields), None), {}).get('form_id', '')
        form_data = load_form_data(form_id_display)
        stdscr.addstr(1, 2, f"{'Insert' if mode == 'I' else 'Search'} Form: {form_data['desc'].split('~')[0][:COLS-14]}" if form_data else '', curses.color_pair(LIGHT_BLUE))
        stdscr.addstr(2, 3, form_id_display, curses.color_pair(GREEN))
        stdscr.addstr(2, 41, form_data['desc'].split('~')[0][:COLS-42] if form_data else '', curses.color_pair(GREEN))
        sorted_fields = sorted([fid for fid in form_fields.keys() if fid != 'L01' and fid != 'R01'], key=lambda x: (form_fields[x]['row'], form_fields[x]['col']))
        for fid in sorted_fields:
            info = form_fields[fid]
            label = info['label']
            text = field_values.get(fid, '')
            color = YELLOW if fid == current_field else GREEN
            col = 14 if fid.startswith('L') else 52
            label_col = 3 if fid.startswith('L') else 41
            max_len = 25
            try:
                stdscr.addstr(info['row'], label_col, label[:10], curses.color_pair(GREEN))
                stdscr.addstr(info['row'], col, "[", curses.color_pair(GREEN))
                stdscr.addstr(info['row'], col + 1, text.ljust(max_len)[:max_len], curses.color_pair(color))
                stdscr.addstr(info['row'], col + max_len + 1, "]", curses.color_pair(GREEN))
                if fid == current_field and current_field not in ('submit', 'cancel'):
                    cursor_x = col + 1 + min(cursor_offset, max_len)
                    if info['row'] < max_form_row and cursor_x < (38 if col == 14 else 76):
                        stdscr.addstr(info['row'], cursor_x, '■', curses.color_pair(YELLOW))
                if LOG_INPUT_FIELD_STATE and fid == current_field:
                    log_event(f"Field {fid}: label={label}, value={text}, cursor_offset={cursor_offset}", input_field_state=True)
            except Exception as e:
                if LOG_FORM_DISPLAY_ERROR:
                    log_event(f"Display error for {fid} at row {info['row']}, col {col}: {str(e)}", form_display_error=True)
        submit_text = "(S)ubmit"
        cancel_text = "(C)ancel"
        total_width = len(submit_text) + len(cancel_text) + 2
        start_x = (max_x - total_width) // 2
        stdscr.addstr(19, start_x, submit_text, curses.color_pair(LIGHT_BLUE if current_field != 'submit' else LIGHT_BLUE | curses.A_REVERSE))
        stdscr.addstr(19, start_x + len(submit_text) + 2, cancel_text, curses.color_pair(LIGHT_BLUE if current_field != 'cancel' else LIGHT_BLUE | curses.A_REVERSE))
        if current_field == 'submit':
            stdscr.addstr(19, start_x + 1, '■', curses.color_pair(LIGHT_BLUE))
        elif current_field == 'cancel':
            stdscr.addstr(19, start_x + len(submit_text) + 3, '■', curses.color_pair(LIGHT_BLUE))
        stdscr.addstr(21, 2, "= Enter=Next Esc=Back Navigate=Use arrow keys =", curses.color_pair(GREEN))
        if sending:
            msg = "Sending. Please wait."
            y = max_y // 2
            x = (max_x - len(msg)) // 2
            stdscr.addstr(y, x, msg, curses.color_pair(YELLOW) | curses.A_BOLD)
        if LOG_FORM_UI_LAYOUT:
            log_event(f"Form UI layout: top={form_id_display} {form_data['desc'] if form_data else ''}, fields={[(fid, info['row'], info['col']) for fid, info in form_fields.items()]}", form_ui_layout=True)
    elif selecting_mode and form_id:
        stdscr.addstr(1, 2, f"Selected {form_id}", curses.color_pair(GREEN))
        stdscr.addstr(2, 2, "S=Search, I=Insert", curses.color_pair(GREEN))
        stdscr.addstr(21, 2, "= Commands: S=Search I=Insert Esc=Back =", curses.color_pair(GREEN))
    elif show_menu and menu_selection == 3:
        stdscr.addstr(1, 2, "Messages", curses.color_pair(GREEN))
        line = 3
        for msg in messages[-18:]:
            if line < 19:
                prefix, from_call, text = msg.split(':', 2)
                if prefix == 'G':
                    _, to_call = from_call, text.split(':', 1)[0]
                    text = text.split(':', 1)[1]
                    if to_call == CALLSIGN:
                        stdscr.addstr(line, 2, f"{from_call} -> {text[:40]}", curses.color_pair(GREEN))
                elif prefix == 'C':
                    stdscr.addstr(line, 2, f"{from_call}: {text[:40]}", curses.color_pair(GREEN))
                line += 1
        stdscr.addstr(21, 2, "= Commands: Esc=Back =", curses.color_pair(GREEN))
        unread_messages = False
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
        form_count = len(form_list)
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
                if LOG_UI_PACKET_DISPLAY:
                    log_event(f"Packet displayed in Comms Log: {msg}", ui_packet_display=True)
        if submission_result:
            msg = f"Submission: {submission_result}"
            stdscr.addstr(max_y-3, (max_x - len(msg)) // 2, msg, curses.color_pair(YELLOW) | curses.A_BOLD)
            time.sleep(2)
            submission_result = None
            screen_dirty = True
            if LOG_REDRAW_TRIGGERS:
                log_event("screen_dirty set by submission_result clear", redraw_triggers=True)
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
        stdscr.addstr(max_y-2, 2, f"-= Commands: D=Menu R=Reconnect 1-{min(form_count, 15)}=Select =-", curses.color_pair(GREEN))
    stdscr.addstr(max_y-1, 0, border, curses.color_pair(RED))
    stdscr.refresh()
    screen_dirty = False
    if LOG_UI_REDRAW:
        log_event(f"Full UI redraw: form_id={form_id}, mode={mode}, fields={list(form_fields.keys())}", ui_redraw=True)
    if LOG_REDRAW_TIMING:
        log_event(f"Redraw took {time.time() - redraw_start:.3f}s", redraw_timing=True)
    if LOG_FORM_LAYOUT and form_fields:
        log_event(f"Form {form_id} layout rendered: {form_fields}", form_layout=True)

# Chunk 5 v5.0.0 - Screen Transition Functions
def display_form_list(stdscr):
    global comms_log, screen_dirty, form_id, selecting_mode, form_fields, current_field, show_menu, mode, submission_result
    if LOG_UI_TRANSITIONS:
        log_event("Transition to form list", ui_transitions=True)
    if LOG_SCREEN_STATE:
        log_event("Screen state: Displaying form list", screen_state=True)
    form_id = None
    selecting_mode = False
    form_fields = {}
    current_field = None
    show_menu = False
    mode = None
    submission_result = None
    screen_dirty = True
    if LOG_REDRAW_TRIGGERS:
        log_event("screen_dirty set by display_form_list", redraw_triggers=True)
    redraw_screen(stdscr)

def display_mode_prompt(stdscr, selected_form_id):
    global comms_log, screen_dirty, form_id, selecting_mode
    if LOG_UI_TRANSITIONS:
        log_event(f"Transition to mode prompt for {selected_form_id}", ui_transitions=True)
    if LOG_SCREEN_STATE:
        log_event(f"Screen state: Displaying mode prompt for {selected_form_id}", screen_state=True)
    form_id = selected_form_id
    selecting_mode = True
    screen_dirty = True
    if LOG_REDRAW_TRIGGERS:
        log_event("screen_dirty set by display_mode_prompt", redraw_triggers=True)
    redraw_screen(stdscr)

def load_form(stdscr, form_id):
    global form_fields, field_values, cursor_row, cursor_col, cursor_offset, current_field, screen_dirty, selecting_mode, mode
    if LOG_UI_TRANSITIONS:
        log_event(f"Transition to form {form_id}", ui_transitions=True)
    if LOG_SCREEN_STATE:
        log_event(f"Screen state: Loading form {form_id} in mode {mode}", screen_state=True)
    stdscr.erase()
    stdscr.clear()
    form_data = load_form_data(form_id)
    if form_data:
        form_fields = form_data['fields']
        for fid in form_fields:
            form_fields[fid]['form_id'] = form_id
        field_values = {fid: '' for fid in form_fields}
        first_field = min(form_fields.keys(), key=lambda x: (form_fields[x]['row'], form_fields[x]['col']))
        current_field = first_field
        cursor_row, cursor_col = form_fields[first_field]['row'], form_fields[first_field]['col'] + 1
        cursor_offset = 0
        selecting_mode = False
        screen_dirty = True
        if LOG_REDRAW_TRIGGERS:
            log_event("screen_dirty set by load_form", redraw_triggers=True)
        redraw_screen(stdscr)

# Chunk 6 v5.0.0 - AX.25 Communication
def send_to_kiss(stdscr, override_packet):
    global sending, packet_queue, kiss_socket, socket_connected
    if LOG_SUBMISSION_FLOW:
        log_event("Send initiated", submission_flow=True)
    sending = True
    if LOG_SUBMISSION_FLOW:
        log_event("Starting submission process", submission_flow=True)
    packet = override_packet
    if not packet:
        packet = f"{mode.upper()}|{CALLSIGN}|{form_id}|"
        for fid in sorted(form_fields.keys()):
            if fid not in ('L01', 'R01', 'submit', 'cancel'):
                packet += f"{fid}={field_values.get(fid, '')}|"
        packet = packet.rstrip('|')
    else:
        if LOG_SYNC_STATE:
            log_event(f"Preparing sync X (INDEX) packet: {packet}", sync_state=True)
        packet = packet.replace('INDEX', 'X')
    if LOG_PACKET_CONTENT:
        log_event(f"Packet payload: {packet}", packet_content=True)
    if LOG_DELIMITER_USAGE:
        log_event(f"Packet uses {packet.count('|')} pipe delimiters", delimiter_usage=True)
    if LOG_COMMAND_VALIDATION:
        log_event(f"Sending command: {packet.split('|')[0]}", command_validation=True)
    compress = mode in ('G', 'P')  # Compress CMS GET/POST packets
    ax25_packets = build_ax25_packet(CALLSIGN, "SVR001", packet, source_ssid=CALLSIGN_SSID, dest_ssid=0, compress=compress)
    if LOG_AX25_PACKET:
        log_event(f"AX.25 packets built: {len(ax25_packets)} parts", ax25_packet=True)
    for ax25_packet in ax25_packets:
        try:
            kiss_frame = b'\xc0\x00' + ax25_packet + b'\xc0'
            if LOG_KISS_FRAMING:
                log_event(f"KISS frame built: {kiss_frame.hex()}", kiss_framing=True)
            if LOG_KISS_VALIDATION:
                log_event(f"KISS frame validated: len={len(kiss_frame)}, start={kiss_frame[0]:02x}, cmd={kiss_frame[1]:02x}, end={kiss_frame[-1]:02x}", kiss_validation=True)
        except Exception as e:
            log_event(f"Failed to build KISS frame: {str(e)}", kiss_framing=True, error_details=True)
            sending = False
            return
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                if not kiss_socket or not socket_connected:
                    if LOG_SOCKET_STATE:
                        log_event("Socket state: Not connected, attempting reconnect", socket_state=True)
                    connect_kiss_socket()
                if LOG_SOCKET_VALIDATION:
                    log_event(f"Socket validated: connected={socket_connected}, fileno={kiss_socket.fileno()}", socket_validation=True)
                if LOG_SOCKET_SEND_ATTEMPT:
                    log_event(f"Attempting to send packet (attempt {attempts + 1}/{MAX_RETRIES})", socket_send_attempt=True)
                if LOG_SOCKET_SEND_RAW:
                    log_event(f"Raw bytes to send: {kiss_frame.hex()}", socket_send_raw=True)
                bytes_sent = kiss_socket.send(kiss_frame)
                if LOG_SOCKET_SEND_BYTES:
                    log_event(f"Sent {bytes_sent} bytes via socket", socket_send_bytes=True)
                if bytes_sent != len(kiss_frame):
                    raise socket.error(f"Partial send: {bytes_sent}/{len(kiss_frame)} bytes")
                if LOG_PACKET_TRANSMISSION:
                    log_event(f"Packet transmission complete: {packet[:50]}", packet_transmission=True)
                log_comms(f"{CALLSIGN}>SVR001:{packet}")
                break
            except Exception as e:
                attempts += 1
                if LOG_SOCKET_SEND_FAILURE:
                    log_event(f"Socket send failed: {str(e)} (attempt {attempts}/{MAX_RETRIES})", socket_send_failure=True)
                if attempts == MAX_RETRIES:
                    log_comms(f"Send failed after {MAX_RETRIES} attempts: {str(e)}")
                    sending = False
                    return
                if kiss_socket:
                    kiss_socket.close()
                    kiss_socket = None
                    socket_connected = False
                    if LOG_SOCKET_STATE:
                        log_event("Socket state: Closed due to send failure", socket_state=True)
                time.sleep(1)
    sending = False

def connect_kiss_socket():
    global kiss_socket, socket_connected
    if kiss_socket:
        kiss_socket.close()
    kiss_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    kiss_socket.settimeout(10)
    try:
        kiss_socket.connect((FAKE_DIREWOLF_HOST, FAKE_DIREWOLF_PORT))
        socket_connected = True
        if LOG_CONNECTION_SUCCESS:
            log_event(f"Connected to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", connection_success=True)
    except Exception as e:
        socket_connected = False
        if LOG_SOCKET_ERRORS:
            log_event(f"Failed to connect KISS socket: {str(e)}", socket_errors=True)

def kiss_listener(stdscr, stop_event):
    global comms_log, screen_dirty, messages, unread_messages, kiss_socket, last_no_data, sending, submission_result, syncing, packet_queue, socket_connected, form_parts, cms_parts
    log_event(f"Starting KISS listener, connecting to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", debug=True, listener_state=True, thread_state=True)
    buffer = b""
    last_timeout_log = 0
    retry_delay = RETRY_DELAY
    max_delay = 60
    while not stop_event.is_set():
        try:
            if not kiss_socket or kiss_socket.fileno() < 0:
                log_event("KISS socket invalid, creating new one", debug=True, socket_state=True)
                kiss_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                kiss_socket.settimeout(5)
                if LOG_CONNECTIVITY:
                    log_event(f"KISS connecting to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", debug=True)
                if LOG_SOCKET_STATE:
                    log_event(f"Socket state: Creating new socket for {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", socket_state=True)
                if LOG_LISTENER_STATE:
                    log_event("KISS listener socket created", listener_state=True)
                for attempt in range(MAX_RETRIES):
                    try:
                        log_event(f"Attempting connection to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT} (attempt {attempt + 1}/{MAX_RETRIES})", connection_attempts=True)
                        kiss_socket.connect((FAKE_DIREWOLF_HOST, FAKE_DIREWOLF_PORT))
                        socket_connected = True
                        if LOG_CONNECTIVITY:
                            log_event(f"Connected to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", connection_success=True)
                        if LOG_RETRIES:
                            log_event(f"Retry {attempt + 1}/{MAX_RETRIES} succeeded", retries=True)
                        if LOG_LISTENER_RETRIES:
                            log_event(f"Listener connected on attempt {attempt + 1}", listener_retries=True)
                        if LOG_SOCKET_STATE:
                            log_event(f"Socket state: Connected on attempt {attempt + 1}", socket_state=True)
                        if LOG_CONNECTION_SUCCESS:
                            log_event(f"Successfully connected to {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", connection_success=True)
                        if LOG_AX25_STATE:
                            log_event("AX.25 state: Connected to Fake Direwolf", ax25_state=True)
                        if LOG_SOCKET_STATUS:
                            log_event("Socket status: Connected", socket_status=True)
                        retry_delay = RETRY_DELAY
                        break
                    except ConnectionRefusedError:
                        if LOG_CONNECTIVITY:
                            log_event(f"Connection failed, retrying ({attempt + 1}/{MAX_RETRIES})", debug=True)
                        if LOG_RETRIES:
                            log_event(f"Connection refused, retry {attempt + 1}/{MAX_RETRIES}", retries=True)
                        if attempt == MAX_RETRIES - 1:
                            if LOG_CONNECTIVITY:
                                log_event(f"Max retries reached, backing off for {retry_delay}s", debug=True)
                            socket_connected = False
                            if LOG_SOCKET_STATUS:
                                log_event("Socket status: Disconnected after max retries", socket_status=True)
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, max_delay)
                        else:
                            time.sleep(1)
                    except Exception as e:
                        log_event(f"Unexpected connect error: {str(e)}", debug=True, socket_errors=True)
                        kiss_socket.close()
                        kiss_socket = None
                        socket_connected = False
                        if LOG_SOCKET_STATUS:
                            log_event("Socket status: Disconnected due to error", socket_status=True)
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, max_delay)
                        break
                else:
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_delay)
                    continue
            while not stop_event.is_set():
                try:
                    if kiss_socket:
                        data = kiss_socket.recv(512)
                        if data:
                            buffer += data
                            if LOG_KISS_PACKET_RECEIVED:
                                log_event(f"KISS data received: {data.hex()[:50]}...", kiss_packet_received=True)
                            if LOG_KISS_RECEIVE_BUFFER:
                                log_event(f"Receive buffer updated: {buffer.hex()} (len={len(buffer)})", kiss_receive_buffer=True)
                            while b'\xC0' in buffer[1:]:
                                start = buffer.find(b'\xC0')
                                end = buffer.find(b'\xC0', start + 1)
                                if end == -1:
                                    break
                                frame_start_time = time.time()
                                frame = buffer[start:end + 1]
                                buffer = buffer[end + 1:]
                                if LOG_KISS_FRAMING:
                                    log_event(f"KISS frame extracted: {frame.hex()}", kiss_framing=True)
                                if LOG_KISS_FRAME_TIMING:
                                    log_event(f"Frame extracted in {time.time() - frame_start_time:.3f}s", kiss_frame_timing=True)
                                if LOG_KISS_RECEIVE_BUFFER:
                                    log_event(f"Buffer after frame split: {buffer.hex()} (len={len(buffer)})", kiss_receive_buffer=True)
                                if not frame.startswith(b'\xC0\x00') or not frame.endswith(b'\xC0'):
                                    if LOG_AX25_PARSE_ERROR:
                                        log_event(f"Invalid KISS frame: {frame.hex()}", ax25_parse_error=True)
                                    continue
                                ax25_packet = frame[2:-1]
                                if LOG_AX25_PACKET:
                                    log_event(f"AX.25 packet: {ax25_packet.hex()}", ax25_packet=True)
                                try:
                                    dest = ax25_packet[0:7].decode('ascii', errors='ignore').strip()
                                    src = ax25_packet[7:14].decode('ascii', errors='ignore').strip()
                                    payload_start = 17
                                    payload_end = ax25_packet.rfind(b'\x7e') - 2
                                    if len(ax25_packet) < payload_start + 1:
                                        if LOG_AX25_PARSE_ERROR:
                                            log_event(f"AX.25 packet too short: {ax25_packet.hex()}", ax25_parse_error=True)
                                        continue
                                    raw_payload = ax25_packet[payload_start:payload_end]
                                    if LOG_PACKET_RAW_DECODE:
                                        log_event(f"Raw payload before decode: {raw_payload.hex()}", packet_raw_decode=True)
                                    payload = raw_payload.decode('ascii', errors='replace').strip()
                                    if payload.startswith("C|"):
                                        payload = zlib.decompress(bytes.fromhex(payload[2:])).decode('ascii', errors='replace')
                                    packet = f"{src}>{dest}:{payload}"
                                    if LOG_KISS_PACKET_RECEIVED:
                                        log_event(f"Decoded packet: {packet}", kiss_packet_received=True)
                                    log_comms(packet)
                                    if LOG_PACKET_VALIDATION:
                                        log_event(f"Packet validated: src={src}, dest={dest}, payload_len={len(payload)}", packet_validation=True)
                                    header, payload = packet.split(':', 1)
                                    parts = payload.split('|', 3)
                                    if LOG_DELIMITER_USAGE:
                                        log_event(f"Received packet uses {payload.count('|')} pipe delimiters", delimiter_usage=True)
                                    if LOG_PACKET_FORMAT:
                                        log_event(f"Packet format check: {len(parts)} parts (expected 4)", packet_format=True)
                                    if len(parts) != 4:
                                        if LOG_AX25_PARSE_ERROR:
                                            log_event(f"Malformed payload: {payload[:50]}", ax25_parse_error=True)
                                        continue
                                    function, callsign, form_id, payload_content = parts
                                    if LOG_PACKET_HANDLING:
                                        log_event(f"Received packet: function={function}, callsign={callsign}, form_id={form_id}", packet_handling=True)
                                    if ':' in payload_content[:5] and function in ['U', 'R', 'G']:
                                        seq_total, content = payload_content.split('|', 1)
                                        seq, total = map(int, seq_total.split(':'))
                                        key = f"{form_id}"
                                        buffer_dict = form_parts if function in ['U', 'R'] else cms_parts
                                        buffer_dict.setdefault(key, {})[seq] = content
                                        log_event(f"Received part {seq}/{total} for {key}", multi_packet=True, buffer_management=True)
                                        if len(buffer_dict[key]) == total:
                                            full_payload = ''.join(buffer_dict[key][i] for i in range(1, total + 1))
                                            log_event(f"Assembled full payload for {key}: {full_payload[:50]}", buffer_management=True)
                                            packet_data = (function, callsign, form_id, full_payload)
                                            try:
                                                packet_queue.put_nowait(packet_data)
                                                if LOG_PACKET_QUEUE:
                                                    log_event(f"Enqueued full packet: {function}|{callsign}|{form_id}|{full_payload[:20]}", packet_queue=True)
                                            except queue.Full:
                                                log_event(f"Queue full, dropped packet: {function}|{callsign}|{form_id}|{full_payload[:50]}", debug=True, packet_drop=True)
                                            del buffer_dict[key]
                                        continue
                                    packet_data = (function, callsign, form_id, payload_content)
                                    try:
                                        packet_queue.put_nowait(packet_data)
                                        if LOG_PACKET_QUEUE:
                                            log_event(f"Enqueued packet: {packet[:50]}", packet_queue=True)
                                        if LOG_LISTENER_QUEUE:
                                            log_event(f"Listener enqueued: {function}|{callsign}|{form_id}|{payload_content[:20]}", listener_queue=True)
                                        if LOG_PACKET_RELAY:
                                            log_event(f"Packet relayed to queue: {function}|{callsign}|{form_id}|{payload_content[:20]}", packet_relay=True)
                                        if LOG_PACKET_ENQUEUE_TIME:
                                            log_event(f"Packet enqueued at {time.time()}", packet_enqueue_time=True)
                                        if LOG_QUEUE_SIZE:
                                            log_event(f"Queue size after enqueue: {packet_queue.qsize()}", queue_size=True)
                                        if function == 'U':
                                            if LOG_COMMAND_VALIDATION:
                                                log_event(f"Validated command 'U' as FORM_UPDATE or PUSH_UPDATE", command_validation=True)
                                            if CMS_SYNC_ENABLED and form_id.startswith("push/"):
                                                file_path = CMS_PUSH_DIR / form_id
                                                os.makedirs(file_path.parent, exist_ok=True)
                                                content = payload_content.replace('~', '\n').rstrip() + '\n'
                                                with open(file_path, 'w', newline='\n') as f:
                                                    f.write(content)
                                                if LOG_CMS_SYNC:
                                                    log_event(f"Updated CMS push file {file_path}: {content[:50]}", cms_sync=True)
                                                if LOG_FILE_IO:
                                                    log_event(f"Updated CMS file {file_path}", file_io=True)
                                            else:
                                                file_path = os.path.join(FORMS_DIR, f"{form_id}.txt")
                                                os.makedirs(FORMS_DIR, exist_ok=True)
                                                content = payload_content.replace('~', '\n').rstrip() + '\n'
                                                if LOG_NEWLINE_HANDLING:
                                                    log_event(f"Initial U (FORM_UPDATE) content after replace/rstrip: {repr(content)}", newline_handling=True)
                                                lines = content.split('\n')
                                                sanitized_lines = []
                                                for line in lines:
                                                    if ',' in line and len(line.split(',')) == 5:
                                                        fid, label, row, col, length = line.split(',')
                                                        length_cleaned = re.sub(r'[^0-9]', '', length) or '256'
                                                        if length != length_cleaned:
                                                            if LOG_FORM_FILE_WRITE:
                                                                log_event(f"Sanitized length in {form_id}: {line} -> {length_cleaned}", form_file_write=True)
                                                        sanitized_lines.append(f"{fid},{label},{row},{col},{length_cleaned}")
                                                    else:
                                                        sanitized_lines.append(line)
                                                content = '\n'.join(sanitized_lines)
                                                if LOG_NEWLINE_HANDLING:
                                                    log_event(f"Final U (FORM_UPDATE) content after join: {repr(content)}", newline_handling=True)
                                                with open(file_path, 'w', newline='\n') as f:
                                                    f.write(content)
                                                if LOG_FORM_FILE_WRITE:
                                                    log_event(f"Wrote sanitized content to {file_path}: {content[:50]}", form_file_write=True)
                                                if LOG_FILE_CONTENT:
                                                    log_event(f"Full content written to {file_path}: {repr(content)}", file_content=True)
                                                if LOG_FILE_IO:
                                                    log_event(f"Updated form file {file_path}", file_io=True)
                                                if LOG_SYNC_FORMS:
                                                    log_event(f"Updated {file_path}: {content[:50]}", sync_forms=True)
                                            build_forms_index()
                                        elif function == 'D':
                                            if LOG_COMMAND_VALIDATION:
                                                log_event(f"Validated command 'D' as FORM_DELETE or PUSH_DELETE", command_validation=True)
                                            if CMS_SYNC_ENABLED and form_id.startswith("push/"):
                                                file_path = CMS_PUSH_DIR / form_id
                                                if file_path.exists():
                                                    file_path.unlink()
                                                    if LOG_CMS_SYNC:
                                                        log_event(f"Deleted CMS push file {file_path}", cms_sync=True)
                                                    if LOG_FILE_IO:
                                                        log_event(f"Deleted CMS file {file_path}", file_io=True)
                                            else:
                                                file_path = os.path.join(FORMS_DIR, f"{form_id}.txt")
                                                if os.path.exists(file_path):
                                                    os.remove(file_path)
                                                    if LOG_FORM_DELETION:
                                                        log_event(f"Form {form_id} deleted from {file_path}", form_deletion=True)
                                                    if LOG_FILE_IO:
                                                        log_event(f"Deleted form file {file_path}", file_io=True)
                                            build_forms_index()
                                    except queue.Full:
                                        log_event(f"Queue full, dropped packet: {packet[:50]}", debug=True, packet_drop=True)
                                except UnicodeDecodeError as e:
                                    if LOG_AX25_PARSE_ERROR:
                                        log_event(f"AX.25 decode error: {str(e)}, raw: {ax25_packet.hex()}", ax25_parse_error=True)
                                    continue
                        else:
                            log_event("Fake Direwolf disconnected: Empty data", debug=True, socket_errors=True)
                            kiss_socket.close()
                            kiss_socket = None
                            socket_connected = False
                            if LOG_AX25_STATE:
                                log_event("AX.25 state: Disconnected from Fake Direwolf", ax25_state=True)
                            if LOG_SOCKET_STATUS:
                                log_event("Socket status: Disconnected (empty data)", socket_status=True)
                            buffer = b""
                            break
                    else:
                        log_event("KISS socket is None, breaking to reconnect", debug=True, socket_errors=True)
                        socket_connected = False
                        if LOG_SOCKET_STATUS:
                            log_event("Socket status: Disconnected (None)", socket_status=True)
                        break
                except socket.timeout:
                    now = time.time()
                    if now - last_no_data >= 60 and now - last_timeout_log >= 60:
                        log_event("No data received, connection still alive", debug=True)
                        last_no_data = now
                        last_timeout_log = now
                except (ConnectionResetError, OSError) as e:
                    log_event(f"Socket error: {str(e)}, closing socket", debug=True, socket_errors=True)
                    if kiss_socket:
                        kiss_socket.close()
                        kiss_socket = None
                        socket_connected = False
                        if LOG_AX25_STATE:
                            log_event("AX.25 state: Closed due to error", ax25_state=True)
                        if LOG_SOCKET_STATUS:
                            log_event("Socket status: Disconnected (error)", socket_status=True)
                    buffer = b""
                    break
                except Exception as e:
                    log_event(f"Unexpected listener error: {str(e)}", debug=True, socket_errors=True)
                    if LOG_ERROR_DETAILS:
                        log_event(f"Listener error details: {traceback.format_exc()}", error_details=True)
                    continue
                time.sleep(0.1)
        except Exception as e:
            log_event(f"Unexpected listener error: {str(e)}", debug=True, socket_errors=True)
            if kiss_socket:
                kiss_socket.close()
                kiss_socket = None
                socket_connected = False
            buffer = b""
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

def process_server_data(stdscr, data):
    pass  # Legacy function, retained

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
    if LOG_THREAD_STATE:
        log_event("KISS listener thread started", thread_state=True)

    log_event("Entering main", debug=True)
    display_form_list(stdscr)
    while True:
        char = stdscr.getch()
        if char != -1:
            log_event(f"Key pressed: {char}", debug=True)
            if LOG_KEY_CONTEXT:
                log_event(f"Key {char} in state: form_id={form_id}, mode={mode}, current_field={current_field}", key_context=True)
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
                            show_menu = False
                            screen_dirty = True
                            stdscr.addstr(1, 2, "Group Chat Screen - TBD", curses.color_pair(GREEN))
                            stdscr.refresh()
                            time.sleep(1)
                        elif menu_selection == 5:
                            log_comms("Quitting via menu")
                            log_event("Script exiting: Menu quit selected", debug=True)
                            stop_event.set()
                            if kiss_socket:
                                kiss_socket.close()
                                if LOG_AX25_STATE:
                                    log_event("AX.25 state: Socket closed on exit", ax25_state=True)
                            break
                    elif char == 27:
                        show_menu = False
                        screen_dirty = True
                else:
                    form_files = [f[:-4] for f in os.listdir(FORMS_DIR) if f.endswith('.txt')]
                    form_files.sort()
                    if chr(char).isdigit() and 1 <= int(chr(char)) <= len(form_files):
                        form_idx = int(chr(char)) - 1
                        form_id = form_files[form_idx]
                        selecting_mode = True
                        display_mode_prompt(stdscr, form_id)
                    elif char == ord('d') or char == ord('D'):
                        show_menu = True
                        menu_selection = 0
                        screen_dirty = True
                    elif char == ord('r') or char == ord('R'):
                        if LOG_SOCKET_RECONNECT:
                            log_event("Manual reconnect triggered", socket_reconnect=True)
                        if kiss_socket:
                            kiss_socket.close()
                            kiss_socket = None
                            socket_connected = False
                            if LOG_SOCKET_STATE:
                                log_event("Socket state: Closed for manual reconnect", socket_state=True)
                            if LOG_SOCKET_STATUS:
                                log_event("Socket status: Disconnected (manual)", socket_status=True)
                        screen_dirty = True
            elif selecting_mode:
                if chr(char).lower() == 's':
                    mode = 'S'
                    if LOG_MODE_SWITCH:
                        log_event(f"Mode switched to Search for {form_id}", mode_switch=True)
                    display_search_screen(stdscr, form_id)
                elif chr(char).lower() == 'i':
                    mode = 'I'
                    if LOG_MODE_SWITCH:
                        log_event(f"Mode switched to Insert for {form_id}", mode_switch=True)
                    load_form(stdscr, form_id)
            elif char == 27 and form_fields:
                if sending:
                    redraw_screen(stdscr, sending=True)
                else:
                    if LOG_FORM_EXIT:
                        log_event(f"Form {form_id} exited via Esc, mode={mode}", form_exit=True)
                    form_id = None
                    selecting_mode = False
                    form_fields = {}
                    field_values = {}
                    current_field = None
                    display_form_list(stdscr)
            elif char == 27 and show_menu and menu_selection in (2, 3):  # CMS or Messages
                show_menu = False
                screen_dirty = True
            elif char == 10 and current_field is not None and form_fields:
                if current_field == 'submit' and not sending:
                    if LOG_SUBMISSION_FLOW:
                        log_event("Submit triggered", submission_flow=True)
                    send_to_kiss(stdscr, "")
                    form_id = None
                    selecting_mode = False
                    form_fields = {}
                    field_values = {}
                    current_field = None
                    if LOG_FORM_EXIT:
                        log_event(f"Form {form_id} exited via submit, mode={mode}", form_exit=True)
                elif current_field == 'cancel':
                    if LOG_FORM_EXIT:
                        log_event(f"Form {form_id} exited via cancel, mode={mode}", form_exit=True)
                    form_id = None
                    selecting_mode = False
                    form_fields = {}
                    field_values = {}
                    current_field = None
                    display_form_list(stdscr)
                else:
                    field_ids = sorted([fid for fid in form_fields.keys() if fid != 'L01' and fid != 'R01'], key=lambda x: (form_fields[x]['row'], form_fields[x]['col'])) + ['submit', 'cancel']
                    idx = field_ids.index(current_field)
                    current_field = field_ids[(idx + 1) % len(field_ids)]
                    cursor_offset = 0 if current_field in ('submit', 'cancel') else min(len(field_values.get(current_field, '')), form_fields[current_field]['len'] if current_field in form_fields else 25)
                    max_y, max_x = stdscr.getmaxyx()
                    row = 19 if current_field in ('submit', 'cancel') else form_fields[current_field]['row']
                    col = (max_x - 11) // 2 + 1 if current_field == 'submit' else (max_x + 1) // 2 + 1 if current_field == 'cancel' else form_fields[current_field]['col'] + 1
                    move_cursor(stdscr, row, col + cursor_offset)
            elif char == curses.KEY_BACKSPACE:
                if current_field and current_field not in ('submit', 'cancel') and form_fields and cursor_offset > 0:
                    row = form_fields[current_field]['row']
                    col = form_fields[current_field]['col'] + 1
                    field_values[current_field] = (
                        field_values[current_field][:cursor_offset - 1] +
                        field_values[current_field][cursor_offset:]
                    )
                    cursor_offset -= 1
                    move_cursor(stdscr, row, col + cursor_offset)
                    redraw_screen(stdscr)
            elif char == curses.KEY_UP:
                if current_field and current_field not in ('submit', 'cancel') and form_fields:
                    is_left = current_field.startswith('L')
                    current_row = form_fields[current_field]['row']
                    above_fields = [fid for fid in form_fields if form_fields[fid]['row'] < current_row and (fid.startswith('L') if is_left else fid.startswith('R')) and fid not in ('L01', 'R01')]
                    if above_fields:
                        next_field = max(above_fields, key=lambda x: form_fields[x]['row'])
                        current_field = next_field
                        cursor_offset = min(len(field_values[current_field]), form_fields[current_field]['len'] - 1)
                        move_cursor(stdscr, form_fields[current_field]['row'], form_fields[current_field]['col'] + 1 + cursor_offset)
                        if LOG_ROW_MOVEMENT:
                            log_event(f"Up from {current_field} to {next_field}", row_movement=True)
            elif char == curses.KEY_DOWN:
                if current_field and form_fields:
                    if current_field in ('submit', 'cancel'):
                        field_ids = sorted([fid for fid in form_fields.keys() if fid != 'L01' and fid != 'R01'], key=lambda x: (form_fields[x]['row'], form_fields[x]['col']))
                        if field_ids:
                            current_field = field_ids[0]
                            cursor_offset = min(len(field_values[current_field]), form_fields[current_field]['len'] - 1)
                            move_cursor(stdscr, form_fields[current_field]['row'], form_fields[current_field]['col'] + 1 + cursor_offset)
                    else:
                        is_left = current_field.startswith('L')
                        current_row = form_fields[current_field]['row']
                        below_fields = [fid for fid in form_fields if form_fields[fid]['row'] > current_row and (fid.startswith('L') if is_left else fid.startswith('R')) and fid not in ('L01', 'R01')]
                        if below_fields:
                            next_field = min(below_fields, key=lambda x: form_fields[x]['row'])
                            current_field = next_field
                            cursor_offset = min(len(field_values[current_field]), form_fields[current_field]['len'] - 1)
                            move_cursor(stdscr, form_fields[current_field]['row'], form_fields[current_field]['col'] + 1 + cursor_offset)
                            if LOG_ROW_MOVEMENT:
                                log_event(f"Down from {current_field} to {next_field}", row_movement=True)
                        elif not below_fields and current_field != 'submit':
                            current_field = 'submit'
                            cursor_offset = 0
                            max_y, max_x = stdscr.getmaxyx()
                            move_cursor(stdscr, 19, (max_x - 11) // 2 + 1)
            elif char == curses.KEY_LEFT:
                if current_field and current_field not in ('submit', 'cancel') and form_fields and current_field.startswith('R'):
                    current_row = form_fields[current_field]['row']
                    field_num = current_field[1:]
                    left_field = f"L{field_num}"
                    if left_field in form_fields and form_fields[left_field]['row'] == current_row:
                        current_field = left_field
                        cursor_offset = min(len(field_values[current_field]), form_fields[current_field]['len'] - 1)
                        move_cursor(stdscr, form_fields[current_field]['row'], form_fields[current_field]['col'] + 1 + cursor_offset)
                        if LOG_COLUMN_NAVIGATION:
                            log_event(f"Left from R{field_num} to L{field_num}", column_navigation=True)
            elif char == curses.KEY_RIGHT:
                if current_field and current_field not in ('submit', 'cancel') and form_fields and current_field.startswith('L'):
                    current_row = form_fields[current_field]['row']
                    field_num = current_field[1:]
                    right_field = f"R{field_num}"
                    if right_field in form_fields and form_fields[right_field]['row'] == current_row:
                        current_field = right_field
                        cursor_offset = min(len(field_values[current_field]), form_fields[current_field]['len'] - 1)
                        move_cursor(stdscr, form_fields[current_field]['row'], form_fields[current_field]['col'] + 1 + cursor_offset)
                        if LOG_COLUMN_NAVIGATION:
                            log_event(f"Right from L{field_num} to R{field_num}", column_navigation=True)
            elif char == 3:
                log_comms("Branch: Ctrl+C exit")
                log_event("Script exiting: Ctrl+C pressed", debug=True)
                stop_event.set()
                if kiss_socket:
                    kiss_socket.close()
                    if LOG_AX25_STATE:
                        log_event("AX.25 state: Socket closed on exit", ax25_state=True)
                break
            elif 32 <= char <= 126:
                if current_field and current_field not in ('submit', 'cancel') and form_fields:
                    row = form_fields[current_field]['row']
                    col = form_fields[current_field]['col'] + 1
                    length = form_fields[current_field]['len']
                    if len(field_values[current_field]) < length:
                        field_values[current_field] = (
                            field_values[current_field][:cursor_offset] +
                            chr(char) +
                            field_values[current_field][cursor_offset:]
                        )[:length]
                        cursor_offset += 1
                        move_cursor(stdscr, row, col + cursor_offset)
                        screen_dirty = True
                        redraw_screen(stdscr)

        while not packet_queue.empty():
            try:
                function, callsign, form_id, payload = packet_queue.get_nowait()
                if LOG_PACKET_QUEUE:
                    log_event(f"Dequeued packet: {function}|{callsign}|{form_id}|{payload[:20]}", packet_queue=True)
                if LOG_UI_PACKET_HANDLING:
                    log_event(f"UI handling packet: {function}|{callsign}|{form_id}|{payload[:20]}", ui_packet_handling=True)
                if LOG_PACKET_HANDLING:
                    log_event(f"Processing packet: function={function}, callsign={callsign}, form_id={form_id}", packet_handling=True)
                if LOG_PACKET_DEQUEUE_TIME:
                    log_event(f"Packet dequeued at {time.time()}", packet_dequeue_time=True)
                if LOG_QUEUE_SIZE:
                    log_event(f"Queue size after dequeue: {packet_queue.qsize()}", queue_size=True)
                if function == 'M' and not syncing:
                    if LOG_COMMAND_VALIDATION:
                        log_event(f"Validated command 'M' as MD5", command_validation=True)
                    if LOG_SYNC_STATE:
                        log_event(f"Received M (MD5) from {callsign}: {payload}", sync_state=True, ui=True)
                    server_hash = payload.strip()
                    if form_id == "PUSH" and CMS_SYNC_ENABLED:
                        clean_push_cache()
                        client_hash = build_cms_push_index()
                        if LOG_MD5_COMPARISON:
                            log_event(f"Push MD5 comparison: server={server_hash}, client={client_hash}", md5_comparison=True)
                        if server_hash != client_hash:
                            if LOG_SYNC_MISMATCHES:
                                log_event(f"Push MD5 mismatch detected: server={server_hash}, client={client_hash}", sync_mismatches=True)
                            if LOG_SYNC_START:
                                log_event("Push sync started due to MD5 mismatch", sync_start=True)
                            syncing = True
                            push_index_path = CMS_DIR / 'push_index.json'
                            try:
                                with open(push_index_path, 'r') as f:
                                    push_dict = json.load(f)['push']
                                if LOG_DIFF_STATE:
                                    log_event(f"Client push from JSON: {push_dict}", diff_state=True)
                            except FileNotFoundError:
                                push_dict = {}
                                log_event("No push_index.json found, assuming empty client push", json_rebuild=True)
                            index_parts = [f"{fname}:{md5}" for fname, data in push_dict.items() for md5 in [data['md5']]]
                            index = "|".join(index_parts)
                            update_packet = f"X|{callsign}|PUSH|{index}"
                            if LOG_SYNC_INDEX:
                                log_event(f"X (PUSH INDEX) packet built: {update_packet}", sync_index=True)
                            if LOG_SYNC_PACKETS:
                                log_event(f"Sending X (PUSH INDEX) packet: {update_packet}", sync_packets=True)
                            send_to_kiss(stdscr, update_packet)
                        else:
                            log_event("Push MD5 match, no sync needed", debug=True)
                            syncing = False
                    else:
                        client_hash = build_forms_index()
                        if LOG_MD5_COMPARISON:
                            log_event(f"Forms MD5 comparison: server={server_hash}, client={client_hash}", md5_comparison=True)
                        if server_hash != client_hash:
                            if LOG_SYNC_MISMATCHES:
                                log_event(f"Forms MD5 mismatch detected: server={server_hash}, client={client_hash}", sync_mismatches=True)
                            if LOG_SYNC_START:
                                log_event("Forms sync started due to MD5 mismatch", sync_start=True)
                            syncing = True
                            forms_index_path = os.path.join(FORMS_DIR, 'forms_index.json')
                            try:
                                with open(forms_index_path, 'r') as f:
                                    forms_dict = json.load(f)['forms']
                                if LOG_DIFF_STATE:
                                    log_event(f"Client forms from JSON: {forms_dict}", diff_state=True)
                            except FileNotFoundError:
                                forms_dict = {}
                                log_event("No forms_index.json found, assuming empty client forms", json_rebuild=True)
                            index_parts = [f"{form_id}:{md5}" for form_id, data in forms_dict.items() for md5 in [data['md5']]]
                            index = "|".join(index_parts)
                            update_packet = f"X|{callsign}|{form_id if form_id else 'ALL'}|{index}"
                            if LOG_SYNC_INDEX:
                                log_event(f"X (FORMS INDEX) packet built: {update_packet}", sync_index=True)
                            if LOG_SYNC_PACKETS:
                                log_event(f"Sending X (FORMS INDEX) packet: {update_packet}", sync_packets=True)
                            send_to_kiss(stdscr, update_packet)
                        else:
                            log_event("Forms MD5 match, no sync needed", debug=True)
                            display_form_list(stdscr)
                elif function == 'U':
                    if LOG_COMMAND_VALIDATION:
                        log_event(f"Validated command 'U' as FORM_UPDATE or PUSH_UPDATE", command_validation=True)
                    screen_dirty = True
                    display_form_list(stdscr)
                    if form_id.startswith("push/"):
                        client_hash = build_cms_push_index()
                        if LOG_SYNC_COMPLETION:
                            log_event(f"Push sync completed, MD5: {client_hash}", sync_completion=True)
                    else:
                        client_hash = build_forms_index()
                        if LOG_SYNC_COMPLETION:
                            log_event(f"Forms sync completed, MD5: {client_hash}", sync_completion=True)
                    syncing = False
                elif function == 'D':
                    if LOG_COMMAND_VALIDATION:
                        log_event(f"Validated command 'D' as FORM_DELETE or PUSH_DELETE", command_validation=True)
                    screen_dirty = True
                    display_form_list(stdscr)
                    if form_id.startswith("push/"):
                        client_hash = build_cms_push_index()
                        if LOG_SYNC_COMPLETION:
                            log_event(f"Push sync completed, MD5: {client_hash}", sync_completion=True)
                    else:
                        client_hash = build_forms_index()
                        if LOG_SYNC_COMPLETION:
                            log_event(f"Forms sync completed, MD5: {client_hash}", sync_completion=True)
                    syncing = False
                elif function == 'R':
                    if LOG_COMMAND_VALIDATION:
                        log_event(f"Validated command 'R' as SEARCH_RESULT", command_validation=True)
                    if LOG_SEARCH_RESULTS:
                        log_event(f"Received R (SEARCH_RESULT): {payload[:50]}", search_results=True)
                    sending = False
                    screen_dirty = True
                    display_results_screen(stdscr, form_id, payload)
                elif function == 'A':
                    if LOG_COMMAND_VALIDATION:
                        log_event(f"Validated command 'A' as ACK", command_validation=True)
                    if LOG_SUBMISSION_DETAILS:
                        log_event(f"Received A (ACK): {payload}", submission_details=True)
                    sending = False
                    submission_result = payload
                    screen_dirty = True
                    display_form_list(stdscr)
                elif function in ('G', 'C'):
                    if LOG_COMMAND_VALIDATION:
                        log_event(f"Validated command '{function}' as {'MSG' if function == 'G' else 'CHAT'}", command_validation=True)
                    messages.append(f"{function}:{callsign}:{payload}")
                    unread_messages = True
                    screen_dirty = True
                elif function == 'G':
                    if LOG_CMS_OPERATIONS:
                        log_event(f"Received G (GET): {payload[:50]}", cms_operations=True)
                    # Placeholder for CMS content display (TBD in UI)
                elif function == 'L':
                    if LOG_CMS_OPERATIONS:
                        log_event(f"Received L (LIST): {payload}", cms_operations=True)
                    # Placeholder for CMS list display (TBD in UI)
                elif function not in ['M', 'A', 'R', 'U', 'D', 'G', 'C', 'L', 'P']:
                    log_event(f"Received invalid command '{function}' from {callsign}", command_validation=True)
                packet_queue.task_done()
            except queue.Empty:
                break

        if screen_dirty:
            redraw_screen(stdscr)
        time.sleep(0.05)

# Chunk 8 v5.0.0 - Search Screen
def display_search_screen(stdscr, form_id):
    global form_fields, field_values, current_field, cursor_offset, screen_dirty, mode
    if LOG_UI_TRANSITIONS:
        log_event(f"Transition to search screen for {form_id}", ui_transitions=True)
    if LOG_SCREEN_STATE:
        log_event(f"Screen state: Displaying search screen for {form_id}", screen_state=True)
    form_data = load_form_data(form_id)
    if not form_data:
        log_comms(f"Form {form_id} not found")
        display_form_list(stdscr)
        return
    form_fields = form_data['fields']
    field_values = {fid: '' for fid in form_fields}
    current_field = min(form_fields.keys())
    cursor_offset = 0
    screen_dirty = True
    RED, GREEN, YELLOW, LIGHT_BLUE = init_colors()
    while True:
        redraw_screen(stdscr)
        char = stdscr.getch()
        if char == 27 or (char == 10 and current_field == 'cancel'):
            if LOG_SCREEN_STATE:
                log_event("Screen state: Cancelled search, returning to form list", screen_state=True)
            display_form_list(stdscr)
            break
        elif char == 10 and current_field == 'submit' and not sending:
            send_to_kiss(stdscr, "")
            break
        elif char == 10:
            field_ids = sorted(form_fields.keys()) + ['submit', 'cancel']
            idx = field_ids.index(current_field)
            current_field = field_ids[(idx + 1) % len(field_ids)]
            cursor_offset = 0 if current_field in ('submit', 'cancel') else min(len(field_values.get(current_field, '')), form_fields[current_field]['len'])
            row = 19 if current_field in ('submit', 'cancel') else form_fields[current_field]['row']
            max_x = stdscr.getmaxyx()[1]
            col = (max_x - 11) // 2 + 1 if current_field == 'submit' else (max_x + 1) // 2 + 1 if current_field == 'cancel' else form_fields[current_field]['col'] + 1
            move_cursor(stdscr, row, col)
        elif char in (curses.KEY_UP, curses.KEY_DOWN):
            field_ids = sorted(form_fields.keys()) + ['submit', 'cancel']
            idx = field_ids.index(current_field)
            delta = -1 if char == curses.KEY_UP else 1
            current_field = field_ids[(idx + delta) % len(field_ids)]
            cursor_offset = 0 if current_field in ('submit', 'cancel') else min(len(field_values.get(current_field, '')), form_fields[current_field]['len'])
            row = 19 if current_field in ('submit', 'cancel') else form_fields[current_field]['row']
            max_x = stdscr.getmaxyx()[1]
            col = (max_x - 11) // 2 + 1 if current_field == 'submit' else (max_x + 1) // 2 + 1 if current_field == 'cancel' else form_fields[current_field]['col'] + 1
            move_cursor(stdscr, row, col)
        elif char == curses.KEY_BACKSPACE and current_field in form_fields and cursor_offset > 0:
            field_values[current_field] = field_values[current_field][:cursor_offset-1] + field_values[current_field][cursor_offset:]
            cursor_offset -= 1
            screen_dirty = True
        elif 32 <= char <= 126 and current_field in form_fields:
            length = form_fields[current_field]['len']
            if len(field_values[current_field]) < length:
                field_values[current_field] = field_values[current_field][:cursor_offset] + chr(char) + field_values[current_field][cursor_offset:]
                cursor_offset += 1
                screen_dirty = True
        if screen_dirty:
            redraw_screen(stdscr)

# Chunk 9 v5.0.0 - Results Screen
def display_results_screen(stdscr, form_id, payload):
    global screen_dirty
    if LOG_UI_TRANSITIONS:
        log_event(f"Transition to results screen for {form_id}", ui_transitions=True)
    if LOG_SCREEN_STATE:
        log_event(f"Screen state: Displaying search results for {form_id}", screen_state=True)
    RED, GREEN, YELLOW, LIGHT_BLUE = init_colors()
    rows = payload.split('~')
    parsed_rows = []
    for row in rows:
        fields = {}
        for field in row.split('|'):
            if len(field) >= 2:
                fields[field[:2]] = field[2:]
        parsed_rows.append(fields)
    all_fields = sorted(set().union(*[row.keys() for row in parsed_rows]))
    result_data = [{fid: row.get(fid, 'N/A') for fid in all_fields} for row in parsed_rows]
    result_df = pd.DataFrame(result_data)
    screen_dirty = True
    while True:
        stdscr.erase()
        stdscr.addstr(0, 0, "=" * (COLS-1), curses.color_pair(RED))
        stdscr.addstr(1, 2, f"Search Results for {form_id}", curses.color_pair(GREEN))
        table = tabulate(result_df, headers='keys', tablefmt='grid', showindex=False)
        for i, line in enumerate(table.split('\n')[:20]):
            stdscr.addstr(i+3, 2, line[:COLS-4], curses.color_pair(GREEN))
        stdscr.addstr(22, 2, "= Esc=Back =", curses.color_pair(GREEN))
        stdscr.addstr(23, 0, "=" * (COLS-1), curses.color_pair(RED))
        stdscr.refresh()
        char = stdscr.getch()
        if char == 27:
            if LOG_SCREEN_STATE:
                log_event("Screen state: Exiting results screen to form list", screen_state=True)
            display_form_list(stdscr)
            break

# Chunk 10 v5.0.0 - Main Loop (Exit Only)
if __name__ == "__main__":
    print("Starting terminal client...")
    try:
        log_event("Client startup initiated", debug=True)
        curses.wrapper(main)
    except Exception as e:
        log_event(f"Curses failed: {str(e)}", debug=True, socket_errors=True)
        if LOG_ERROR_DETAILS:
            log_event(f"Startup error details: {traceback.format_exc()}", error_details=True)
        raise

# Chunk 11 v5.0.0 - Design Goals and Statuses
# DESIGN GOALS AND CHANGES:
# - See client_mini_revisions_20250322_v5.0.0.txt for this update (v5.0.0)
# - Full history in PacketRadioTerminalServiceManual [REVISION_SUMMARY]