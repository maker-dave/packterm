#!/usr/bin/env python3
# server.py
# Version 4.0.1 - 2025-03-22  # CHANGE v4.0.1: Added CMS with push sync, compression, menu access, merged from v3.0.14 base

# Chunk 1 v4.0.1 - Imports, Early Globals, and Utilities
import os
import sys
import time
import socket
import threading
import hashlib
import logging
import shutil
import curses
import glob
import select
import traceback
import configparser
import re
import queue
import crcmod
import json
import zlib  # Added for AX.25 compression
from datetime import datetime
from collections import defaultdict
from pathlib import Path  # Added for CMS path handling

comms_log = []
screen_dirty = True
clients = []  # (callsign, last_data_time)
clients_lock = threading.Lock()
forms_md5 = None
push_md5 = None  # Added for CMS push sync
last_mtime = 0
last_push_mtime = 0  # Added for CMS push sync
show_menu = False
menu_selection = 0
syncing_clients = set()
last_broadcast = {}
kiss_socket = None
kiss_socket_ready = threading.Event()
last_md5_time = None
response_parts = {}  # Buffer for multi-packet responses, {callsign:form_id: {seq: content}}

# CMS Config
CMS_DIR = Path(os.path.expanduser('~/terminal/cms'))
CMS_PUSH_DIR = CMS_DIR / "push"
CMS_DIR.mkdir(exist_ok=True)
CMS_PUSH_DIR.mkdir(exist_ok=True)

def log_event(message, ui=False, submission_details=False, submissions=False, submission_payload=False, segment_failure=False, socket_state=False, retries=False, ui_transitions=False, search_query=False, search_results=False, search_parsing=False, csv_processing=False, client_state=False, packet_build=False, packet_parse=False, sync_state=False, sync_md5=False, sync_forms=False, client_packet=False, packet_integrity=False, form_deletion=False, sync_start=False, sync_completion=False, packet_queue=False, client_queue=False, ui_packet_handling=False, queue_state=False, startup_errors=False, backups=False, connection_attempts=False, packet_drop=False, thread_state=False, form_field_creation=False, form_preview=False, field_positioning=False, table_edit=False, form_save=False, ui_render=False, form_sync_error=False, packet_fragments=False, sync_mismatches=False, forms_management=False, kiss_framing=False, packet_timing=False, ax25_state=False, ax25_packet=False, kiss_packet_received=False, ax25_parse_error=False, packet_send_failure=False, socket_send_state=False, socket_send_bytes=False, socket_flush=False, socket_config=False, broadcast_state=False, socket_error=False, thread_error=False, startup_sync=False, thread_sync=False, socket_init=False, ax25_header=False, ax25_parsing_error=False, json_rebuild=False, diff_state=False, broadcast_md5=False, ax25_raw_payload=False, ax25_fcs=False, sync_broadcast=False, sync_response=False, payload_validation=False, packet_length=False, transmission_validation=False, form_content=False, packet_sanitization=False, sync_packet_validation=False, form_field_validation=False, pre_send_validation=False, packet_raw_bytes=False, form_field_sanitization=False, ax25_frame_validation=False, command_validation=False, packet_handling=False, file_io=False, filesystem_sync=False, md5_change=False, multi_packet=False, buffer_management=False, cms_sync=False, cms_operations=False, cms_packet_build=False, cms_ui_state=False):  # CHANGE v4.0.1: Added CMS logging
    logging.info(message)
    if ui:
        comms_log.append((message, datetime.now().strftime('%H:%M:%S')))
        if len(comms_log) > 19:
            comms_log.pop(0)
        global screen_dirty
        screen_dirty = True
    if submission_details and LOG_SUBMISSION_DETAILS: logging.info("Submission Detail: " + message)
    if submissions and LOG_SUBMISSIONS: logging.info("Submission: " + message)
    if submission_payload and LOG_SUBMISSION_PAYLOAD: logging.info("Submission Payload: " + message)
    if segment_failure and LOG_SEGMENT_FAILURE: logging.info("Segment Failure: " + message)
    if socket_state and LOG_SOCKET_STATE: logging.info("Socket State: " + message)
    if retries and LOG_RETRIES: logging.info("Retry: " + message)
    if ui_transitions and LOG_UI_TRANSITIONS: logging.info("UI Transition: " + message)
    if search_query and LOG_SEARCH_QUERY: logging.info("Search Query: " + message)
    if search_results and LOG_SEARCH_RESULTS: logging.info("Search Results: " + message)
    if search_parsing and LOG_SEARCH_PARSING: logging.info("Search Parsing: " + message)
    if csv_processing and LOG_CSV_PROCESSING: logging.info("CSV Processing: " + message)
    if client_state and LOG_CLIENT_STATE: logging.info("Client State: " + message)
    if packet_build and LOG_PACKET_BUILD: logging.info("Packet Build: " + message)
    if packet_parse and LOG_PACKET_PARSE: logging.info("Packet Parse: " + message)
    if sync_state and LOG_SYNC_STATE: logging.info("Sync State: " + message)
    if sync_md5 and LOG_SYNC_MD5: logging.info("Sync MD5: " + message)
    if sync_forms and LOG_SYNC_FORMS: logging.info("Sync Forms: " + message)
    if client_packet and LOG_CLIENT_PACKET: logging.info("Client Packet: " + message)
    if packet_integrity and LOG_PACKET_INTEGRITY: logging.info("Packet Integrity: " + message)
    if form_deletion and LOG_FORM_DELETION: logging.info("Form Deletion: " + message)
    if sync_start and LOG_SYNC_START: logging.info("Sync Start: " + message)
    if sync_completion and LOG_SYNC_COMPLETION: logging.info("Sync Completion: " + message)
    if packet_queue and LOG_PACKET_QUEUE: logging.info("Packet Queue: " + message)
    if client_queue and LOG_CLIENT_QUEUE: logging.info("Client Queue: " + message)
    if ui_packet_handling and LOG_UI_PACKET_HANDLING: logging.info("UI Packet Handling: " + message)
    if queue_state and LOG_QUEUE_STATE: logging.info("Queue State: " + message)
    if startup_errors and LOG_STARTUP_ERRORS: logging.info("Startup Error: " + message)
    if backups: logging.info("Backup: " + message)  # Always on per requirement
    if connection_attempts and LOG_CONNECTION_ATTEMPTS: logging.info("Connection Attempt: " + message)
    if packet_drop and LOG_PACKET_DROP: logging.info("Packet Drop: " + message)
    if thread_state and LOG_THREAD_STATE: logging.info("Thread State: " + message)
    if form_field_creation and LOG_FORM_FIELD_CREATION: logging.info("Form Field Creation: " + message)
    if form_preview and LOG_FORM_PREVIEW: logging.info("Form Preview: " + message)
    if field_positioning and LOG_FIELD_POSITIONING: logging.info("Field Positioning: " + message)
    if table_edit and LOG_TABLE_EDIT: logging.info("Table Edit: " + message)
    if form_save and LOG_FORM_SAVE: logging.info("Form Save: " + message)
    if ui_render and LOG_UI_RENDER: logging.info("UI Render: " + message)
    if form_sync_error and LOG_FORM_SYNC_ERROR: logging.info("Form Sync Error: " + message)
    if packet_fragments and LOG_PACKET_FRAGMENTS: logging.info("Packet Fragments: " + message)
    if sync_mismatches and LOG_SYNC_MISMATCHES: logging.info("Sync Mismatch: " + message)
    if forms_management and LOG_FORMS_MANAGEMENT: logging.info("Forms Management: " + message)
    if kiss_framing and LOG_KISS_FRAMING: logging.info("KISS Framing: " + message)
    if packet_timing and LOG_PACKET_TIMING: logging.info("Packet Timing: " + message)
    if ax25_state and LOG_AX25_STATE: logging.info("AX.25 State: " + message)
    if ax25_packet and LOG_AX25_PACKET: logging.info("AX.25 Packet: " + message)
    if kiss_packet_received and LOG_KISS_PACKET_RECEIVED: logging.info("KISS Packet Received: " + message)
    if ax25_parse_error and LOG_AX25_PARSE_ERROR: logging.info("AX.25 Parse Error: " + message)
    if packet_send_failure and LOG_PACKET_SEND_FAILURE: logging.info("Packet Send Failure: " + message)
    if socket_send_state and LOG_SOCKET_SEND_STATE: logging.info("Socket Send State: " + message)
    if socket_send_bytes and LOG_SOCKET_SEND_BYTES: logging.info("Socket Send Bytes: " + message)
    if socket_flush and LOG_SOCKET_FLUSH: logging.info("Socket Flush: " + message)
    if socket_config and LOG_SOCKET_CONFIG: logging.info("Socket Config: " + message)
    if broadcast_state and LOG_BROADCAST_STATE: logging.info("Broadcast State: " + message)
    if socket_error and LOG_SOCKET_ERROR: logging.info("Socket Error: " + message)
    if thread_error and LOG_THREAD_ERROR: logging.info("Thread Error: " + message)
    if startup_sync and LOG_STARTUP_SYNC: logging.info("Startup Sync: " + message)
    if thread_sync and LOG_THREAD_SYNC: logging.info("Thread Sync: " + message)
    if socket_init and LOG_SOCKET_INIT: logging.info("Socket Init: " + message)
    if ax25_header and LOG_AX25_HEADER: logging.info("AX.25 Header: " + message)
    if ax25_parsing_error and LOG_AX25_PARSING_ERROR: logging.info("AX.25 Parsing Error: " + message)
    if json_rebuild and LOG_JSON_REBUILD: logging.info("JSON Rebuild: " + message)
    if diff_state and LOG_DIFF_STATE: logging.info("Diff State: " + message)
    if broadcast_md5 and LOG_BROADCAST_MD5: logging.info("Broadcast MD5: " + message)
    if ax25_raw_payload and LOG_AX25_RAW_PAYLOAD: logging.info("AX.25 Raw Payload: " + message)
    if ax25_fcs and LOG_AX25_FCS: logging.info("AX.25 FCS: " + message)
    if sync_broadcast and LOG_SYNC_BROADCAST: logging.info("Sync Broadcast: " + message)
    if sync_response and LOG_SYNC_RESPONSE: logging.info("Sync Response: " + message)
    if payload_validation and LOG_PAYLOAD_VALIDATION: logging.info("Payload Validation: " + message)
    if packet_length and LOG_PACKET_LENGTH: logging.info("Packet Length: " + message)
    if transmission_validation and LOG_TRANSMISSION_VALIDATION: logging.info("Transmission Validation: " + message)
    if form_content and LOG_FORM_CONTENT: logging.info("Form Content: " + message)
    if packet_sanitization and LOG_PACKET_SANITIZATION: logging.info("Packet Sanitization: " + message)
    if sync_packet_validation and LOG_SYNC_PACKET_VALIDATION: logging.info("Sync Packet Validation: " + message)
    if form_field_validation and LOG_FORM_FIELD_VALIDATION: logging.info("Form Field Validation: " + message)
    if pre_send_validation and LOG_PRE_SEND_VALIDATION: logging.info("Pre-Send Validation: " + message)
    if packet_raw_bytes and LOG_PACKET_RAW_BYTES: logging.info("Packet Raw Bytes: " + message)
    if form_field_sanitization and LOG_FORM_FIELD_SANITIZATION: logging.info("Form Field Sanitization: " + message)
    if ax25_frame_validation and LOG_AX25_FRAME_VALIDATION: logging.info("AX.25 Frame Validation: " + message)
    if command_validation and LOG_COMMAND_VALIDATION: logging.info("Command Validation: " + message)
    if packet_handling and LOG_PACKET_HANDLING: logging.info("Packet Handling: " + message)
    if file_io and LOG_FILE_IO: logging.info("File I/O: " + message)
    if filesystem_sync and LOG_FILESYSTEM_SYNC: logging.info("Filesystem Sync: " + message)
    if md5_change and LOG_MD5_CHANGE: logging.info("MD5 Change: " + message)
    if multi_packet and LOG_MULTI_PACKET: logging.info("Multi-Packet: " + message)
    if buffer_management and LOG_BUFFER_MANAGEMENT: logging.info("Buffer Management: " + message)
    if cms_sync and LOG_CMS_SYNC: logging.info("CMS Sync: " + message)
    if cms_operations and LOG_CMS_OPERATIONS: logging.info("CMS Operation: " + message)
    if cms_packet_build and LOG_CMS_PACKET_BUILD: logging.info("CMS Packet Build: " + message)
    if cms_ui_state and LOG_CMS_UI_STATE: logging.info("CMS UI State: " + message)

def log_comms(message):
    if not message.startswith(f"0{CALLSIGN}>ALL:M|"):  # Exclude MD5 broadcasts from UI
        log_event(message, ui=True)

def backup_script():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, "server_" + timestamp + ".py")
    shutil.copy2(__file__, backup_path)
    log_event("Backed up to " + backup_path, ui=False, backups=True)

VERSION = "4.0.1"  # CHANGE v4.0.1: Merged CMS into v3.0.14 base
PACLEN = 255

config = configparser.ConfigParser()
CONFIG_FILE = None
if not os.path.exists(CONFIG_FILE or ''):
    config['Settings'] = {
        'callsign': 'SVR001',
        'paclen': str(PACLEN),
        'log_client_details': 'True',
        'log_form_sync': 'True',
        'log_submissions': 'True',
        'broadcast_interval': '60',
        'client_timeout': '1800',
        'cms_sync_enabled': 'True',  # Added for CMS push sync
        'cms_sync_max_age': '604800',  # 1 week in seconds
        'log_submission_details': 'True',
        'log_packet_parsing': 'False',
        'log_buffer_events': 'False',
        'log_packet_content': 'False',
        'log_payload_processing': 'False',
        'log_submission_payload': 'True',
        'log_segment_failure': 'True',
        'log_socket_state': 'False',
        'log_retries': 'True',
        'log_ui_transitions': 'False',
        'log_search_query': 'True',
        'log_search_results': 'True',
        'log_search_parsing': 'True',
        'log_csv_processing': 'True',
        'log_client_state': 'True',
        'log_packet_build': 'True',
        'log_packet_parse': 'True',
        'log_sync_state': 'True',
        'log_sync_md5': 'True',
        'log_sync_forms': 'True',
        'log_client_packet': 'True',
        'log_packet_integrity': 'True',
        'log_form_deletion': 'True',
        'log_sync_start': 'True',
        'log_sync_completion': 'True',
        'log_packet_queue': 'True',
        'log_client_queue': 'True',
        'log_ui_packet_handling': 'True',
        'log_queue_state': 'True',
        'log_startup_errors': 'True',
        'home_dir': os.path.expanduser('~/terminal'),
        'server_host': '0.0.0.0',
        'server_port': '12345',
        'fake_direwolf_host': '127.0.0.1',
        'fake_direwolf_port': '8051',
        'queue_maxsize': '100',
        'log_connection_attempts': 'True',
        'log_packet_drop': 'True',
        'log_thread_state': 'True',
        'log_form_field_creation': 'True',
        'log_form_preview': 'False',
        'log_field_positioning': 'False',
        'log_table_edit': 'True',
        'log_form_save': 'True',
        'log_ui_render': 'False',
        'log_form_sync_error': 'True',
        'log_packet_fragments': 'True',
        'log_sync_mismatches': 'True',
        'log_forms_management': 'True',
        'log_kiss_framing': 'True',
        'log_packet_timing': 'False',
        'log_ax25_state': 'True',
        'log_ax25_packet': 'True',
        'log_kiss_packet_received': 'True',
        'log_ax25_parse_error': 'True',
        'log_packet_send_failure': 'True',
        'log_socket_send_state': 'False',
        'log_socket_send_bytes': 'False',
        'log_socket_flush': 'False',
        'log_socket_config': 'False',
        'log_broadcast_state': 'True',
        'log_socket_error': 'True',
        'log_thread_error': 'True',
        'log_startup_sync': 'True',
        'log_thread_sync': 'True',
        'log_socket_init': 'False',
        'log_ax25_header': 'True',
        'log_ax25_parsing_error': 'True',
        'log_json_rebuild': 'True',
        'log_diff_state': 'True',
        'log_broadcast_md5': 'True',
        'log_ax25_raw_payload': 'True',
        'log_ax25_fcs': 'True',
        'log_sync_broadcast': 'True',
        'log_sync_response': 'True',
        'log_payload_validation': 'True',
        'log_packet_length': 'True',
        'log_transmission_validation': 'True',
        'log_form_content': 'True',
        'log_packet_sanitization': 'True',
        'log_sync_packet_validation': 'True',
        'log_form_field_validation': 'True',
        'log_pre_send_validation': 'True',
        'log_packet_raw_bytes': 'True',
        'log_form_field_sanitization': 'True',
        'log_ax25_frame_validation': 'True',
        'log_command_validation': 'True',
        'log_packet_handling': 'True',
        'log_file_io': 'True',
        'log_filesystem_sync': 'True',
        'log_md5_change': 'True',
        'log_multi_packet': 'True',
        'log_buffer_management': 'True',
        'log_cms_sync': 'True',         # Added for CMS
        'log_cms_operations': 'True',   # Added for CMS
        'log_cms_packet_build': 'True', # Added for CMS
        'log_cms_ui_state': 'False'     # Added for CMS, off to reduce spam
    }
    HOME_DIR = config['Settings']['home_dir']
    os.makedirs(HOME_DIR, exist_ok=True)
    CONFIG_FILE = os.path.join(HOME_DIR, 'server.conf')
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
config.read(CONFIG_FILE or os.path.join(os.path.expanduser('~/terminal'), 'server.conf'))
HOME_DIR = config.get('Settings', 'home_dir', fallback=os.path.expanduser('~/terminal'))
CONFIG_FILE = os.path.join(HOME_DIR, 'server.conf')
FORMS_DIR = os.path.join(HOME_DIR, 'forms')
DATA_DIR = os.path.join(HOME_DIR, 'server_data')
LOG_FILE = os.path.join(DATA_DIR, 'server.log')
BACKUP_DIR = os.path.join(HOME_DIR, 'backups')
CALLSIGN = config.get('Settings', 'callsign', fallback='SVR001')
PACLEN = config.getint('Settings', 'paclen', fallback=PACLEN)
FAKE_DIREWOLF_HOST = config.get('Settings', 'fake_direwolf_host', fallback='127.0.0.1')
FAKE_DIREWOLF_PORT = config.getint('Settings', 'fake_direwolf_port', fallback=8051)
SERVER_HOST = config.get('Settings', 'server_host', fallback='0.0.0.0')
SERVER_PORT = config.getint('Settings', 'server_port', fallback=12345)
CMS_SYNC_ENABLED = config.getboolean('Settings', 'cms_sync_enabled', fallback=True)
CMS_SYNC_MAX_AGE = config.getint('Settings', 'cms_sync_max_age', fallback=604800)
LOG_CLIENT_DETAILS = config.getboolean('Settings', 'log_client_details', fallback=True)
LOG_FORM_SYNC = config.getboolean('Settings', 'log_form_sync', fallback=True)
LOG_SUBMISSIONS = config.getboolean('Settings', 'log_submissions', fallback=True)
BROADCAST_INTERVAL = config.getint('Settings', 'broadcast_interval', fallback=60)
CLIENT_TIMEOUT = config.getint('Settings', 'client_timeout', fallback=1800)
LOG_SUBMISSION_DETAILS = config.getboolean('Settings', 'log_submission_details', fallback=True)
LOG_PACKET_PARSING = config.getboolean('Settings', 'log_packet_parsing', fallback=False)
LOG_BUFFER_EVENTS = config.getboolean('Settings', 'log_buffer_events', fallback=False)
LOG_PACKET_CONTENT = config.getboolean('Settings', 'log_packet_content', fallback=False)
LOG_PAYLOAD_PROCESSING = config.getboolean('Settings', 'log_payload_processing', fallback=False)
LOG_SUBMISSION_PAYLOAD = config.getboolean('Settings', 'log_submission_payload', fallback=True)
LOG_SEGMENT_FAILURE = config.getboolean('Settings', 'log_segment_failure', fallback=True)
LOG_SOCKET_STATE = config.getboolean('Settings', 'log_socket_state', fallback=False)
LOG_RETRIES = config.getboolean('Settings', 'log_retries', fallback=True)
LOG_UI_TRANSITIONS = config.getboolean('Settings', 'log_ui_transitions', fallback=False)
LOG_SEARCH_QUERY = config.getboolean('Settings', 'log_search_query', fallback=True)
LOG_SEARCH_RESULTS = config.getboolean('Settings', 'log_search_results', fallback=True)
LOG_SEARCH_PARSING = config.getboolean('Settings', 'log_search_parsing', fallback=True)
LOG_CSV_PROCESSING = config.getboolean('Settings', 'log_csv_processing', fallback=True)
LOG_CLIENT_STATE = config.getboolean('Settings', 'log_client_state', fallback=True)
LOG_PACKET_BUILD = config.getboolean('Settings', 'log_packet_build', fallback=True)
LOG_PACKET_PARSE = config.getboolean('Settings', 'log_packet_parse', fallback=True)
LOG_SYNC_STATE = config.getboolean('Settings', 'log_sync_state', fallback=True)
LOG_SYNC_MD5 = config.getboolean('Settings', 'log_sync_md5', fallback=True)
LOG_SYNC_FORMS = config.getboolean('Settings', 'log_sync_forms', fallback=True)
LOG_CLIENT_PACKET = config.getboolean('Settings', 'log_client_packet', fallback=True)
LOG_PACKET_INTEGRITY = config.getboolean('Settings', 'log_packet_integrity', fallback=True)
LOG_FORM_DELETION = config.getboolean('Settings', 'log_form_deletion', fallback=True)
LOG_SYNC_START = config.getboolean('Settings', 'log_sync_start', fallback=True)
LOG_SYNC_COMPLETION = config.getboolean('Settings', 'log_sync_completion', fallback=True)
LOG_PACKET_QUEUE = config.getboolean('Settings', 'log_packet_queue', fallback=True)
LOG_CLIENT_QUEUE = config.getboolean('Settings', 'log_client_queue', fallback=True)
LOG_UI_PACKET_HANDLING = config.getboolean('Settings', 'log_ui_packet_handling', fallback=True)
LOG_QUEUE_STATE = config.getboolean('Settings', 'log_queue_state', fallback=True)
LOG_STARTUP_ERRORS = config.getboolean('Settings', 'log_startup_errors', fallback=True)
LOG_CONNECTION_ATTEMPTS = config.getboolean('Settings', 'log_connection_attempts', fallback=True)
LOG_PACKET_DROP = config.getboolean('Settings', 'log_packet_drop', fallback=True)
LOG_THREAD_STATE = config.getboolean('Settings', 'log_thread_state', fallback=True)
LOG_FORM_FIELD_CREATION = config.getboolean('Settings', 'log_form_field_creation', fallback=True)
LOG_FORM_PREVIEW = config.getboolean('Settings', 'log_form_preview', fallback=False)
LOG_FIELD_POSITIONING = config.getboolean('Settings', 'log_field_positioning', fallback=False)
LOG_TABLE_EDIT = config.getboolean('Settings', 'log_table_edit', fallback=True)
LOG_FORM_SAVE = config.getboolean('Settings', 'log_form_save', fallback=True)
LOG_UI_RENDER = config.getboolean('Settings', 'log_ui_render', fallback=False)
LOG_FORM_SYNC_ERROR = config.getboolean('Settings', 'log_form_sync_error', fallback=True)
LOG_PACKET_FRAGMENTS = config.getboolean('Settings', 'log_packet_fragments', fallback=True)
LOG_SYNC_MISMATCHES = config.getboolean('Settings', 'log_sync_mismatches', fallback=True)
LOG_FORMS_MANAGEMENT = config.getboolean('Settings', 'log_forms_management', fallback=True)
LOG_KISS_FRAMING = config.getboolean('Settings', 'log_kiss_framing', fallback=True)
LOG_PACKET_TIMING = config.getboolean('Settings', 'log_packet_timing', fallback=False)
LOG_AX25_STATE = config.getboolean('Settings', 'log_ax25_state', fallback=True)
LOG_AX25_PACKET = config.getboolean('Settings', 'log_ax25_packet', fallback=True)
LOG_KISS_PACKET_RECEIVED = config.getboolean('Settings', 'log_kiss_packet_received', fallback=True)
LOG_AX25_PARSE_ERROR = config.getboolean('Settings', 'log_ax25_parse_error', fallback=True)
LOG_PACKET_SEND_FAILURE = config.getboolean('Settings', 'log_packet_send_failure', fallback=True)
LOG_SOCKET_SEND_STATE = config.getboolean('Settings', 'log_socket_send_state', fallback=False)
LOG_SOCKET_SEND_BYTES = config.getboolean('Settings', 'log_socket_send_bytes', fallback=False)
LOG_SOCKET_FLUSH = config.getboolean('Settings', 'log_socket_flush', fallback=False)
LOG_SOCKET_CONFIG = config.getboolean('Settings', 'log_socket_config', fallback=False)
LOG_BROADCAST_STATE = config.getboolean('Settings', 'log_broadcast_state', fallback=True)
LOG_SOCKET_ERROR = config.getboolean('Settings', 'log_socket_error', fallback=True)
LOG_THREAD_ERROR = config.getboolean('Settings', 'log_thread_error', fallback=True)
LOG_STARTUP_SYNC = config.getboolean('Settings', 'log_startup_sync', fallback=True)
LOG_THREAD_SYNC = config.getboolean('Settings', 'log_thread_sync', fallback=True)
LOG_SOCKET_INIT = config.getboolean('Settings', 'log_socket_init', fallback=False)
LOG_AX25_HEADER = config.getboolean('Settings', 'log_ax25_header', fallback=True)
LOG_AX25_PARSING_ERROR = config.getboolean('Settings', 'log_ax25_parsing_error', fallback=True)
LOG_JSON_REBUILD = config.getboolean('Settings', 'log_json_rebuild', fallback=True)
LOG_DIFF_STATE = config.getboolean('Settings', 'log_diff_state', fallback=True)
LOG_BROADCAST_MD5 = config.getboolean('Settings', 'log_broadcast_md5', fallback=True)
LOG_AX25_RAW_PAYLOAD = config.getboolean('Settings', 'log_ax25_raw_payload', fallback=True)
LOG_AX25_FCS = config.getboolean('Settings', 'log_ax25_fcs', fallback=True)
LOG_SYNC_BROADCAST = config.getboolean('Settings', 'log_sync_broadcast', fallback=True)
LOG_SYNC_RESPONSE = config.getboolean('Settings', 'log_sync_response', fallback=True)
LOG_PAYLOAD_VALIDATION = config.getboolean('Settings', 'log_payload_validation', fallback=True)
LOG_PACKET_LENGTH = config.getboolean('Settings', 'log_packet_length', fallback=True)
LOG_TRANSMISSION_VALIDATION = config.getboolean('Settings', 'log_transmission_validation', fallback=True)
LOG_FORM_CONTENT = config.getboolean('Settings', 'log_form_content', fallback=True)
LOG_PACKET_SANITIZATION = config.getboolean('Settings', 'log_packet_sanitization', fallback=True)
LOG_SYNC_PACKET_VALIDATION = config.getboolean('Settings', 'log_sync_packet_validation', fallback=True)
LOG_FORM_FIELD_VALIDATION = config.getboolean('Settings', 'log_form_field_validation', fallback=True)
LOG_PRE_SEND_VALIDATION = config.getboolean('Settings', 'log_pre_send_validation', fallback=True)
LOG_PACKET_RAW_BYTES = config.getboolean('Settings', 'log_packet_raw_bytes', fallback=True)
LOG_FORM_FIELD_SANITIZATION = config.getboolean('Settings', 'log_form_field_sanitization', fallback=True)
LOG_AX25_FRAME_VALIDATION = config.getboolean('Settings', 'log_ax25_frame_validation', fallback=True)
LOG_COMMAND_VALIDATION = config.getboolean('Settings', 'log_command_validation', fallback=True)
LOG_PACKET_HANDLING = config.getboolean('Settings', 'log_packet_handling', fallback=True)
LOG_FILE_IO = config.getboolean('Settings', 'log_file_io', fallback=True)
LOG_FILESYSTEM_SYNC = config.getboolean('Settings', 'log_filesystem_sync', fallback=True)
LOG_MD5_CHANGE = config.getboolean('Settings', 'log_md5_change', fallback=True)
LOG_MULTI_PACKET = config.getboolean('Settings', 'log_multi_packet', fallback=True)
LOG_BUFFER_MANAGEMENT = config.getboolean('Settings', 'log_buffer_management', fallback=True)
LOG_CMS_SYNC = config.getboolean('Settings', 'log_cms_sync', fallback=True)
LOG_CMS_OPERATIONS = config.getboolean('Settings', 'log_cms_operations', fallback=True)
LOG_CMS_PACKET_BUILD = config.getboolean('Settings', 'log_cms_packet_build', fallback=True)
LOG_CMS_UI_STATE = config.getboolean('Settings', 'log_cms_ui_state', fallback=False)
QUEUE_MAXSIZE = config.getint('Settings', 'queue_maxsize', fallback=100)

packet_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)

if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')
log_event("Deleted old log file", ui=False)
log_event(f"Initial packet_queue size: {packet_queue.qsize()}", ui=False, queue_state=True)

# Chunk 2 v4.0.1 - Utility Functions
def get_callsign(stdscr):
    global CALLSIGN
    if not CALLSIGN:
        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "Enter Server Callsign (e.g., KC8QKU, required): ", curses.color_pair(2))
            stdscr.refresh()
            curses.echo()
            CALLSIGN = stdscr.getstr(1, 0, 10).decode().strip().upper()
            curses.noecho()
            if CALLSIGN:
                break
            stdscr.addstr(2, 0, "Callsign cannot be empty. Try again.", curses.color_pair(1))
            stdscr.refresh()
            time.sleep(1)
        config['Settings']['callsign'] = CALLSIGN
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
    log_event("Callsign set to " + CALLSIGN, ui=False)
    return CALLSIGN

def build_ax25_packet(source, dest, payload, compress=False):
    crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    def encode_callsign(callsign, ssid=0, last=False):
        callsign = callsign.ljust(6)[:6].upper()
        ssid_byte = (0x60 | (ssid << 1) | (1 if last else 0))
        return bytes([ord(c) << 1 for c in callsign]) + bytes([ssid_byte])
    payload_bytes = payload.encode()
    if compress:
        payload_bytes = zlib.compress(payload_bytes)
        payload = f"C|{payload_bytes.hex()}"
    max_payload = PACLEN - 32  # Rough estimate for AX.25/KISS overhead
    if len(payload) > max_payload:
        log_event(f"Payload exceeds max ({max_payload}): {len(payload)} bytes, splitting", packet_length=True, multi_packet=True)
        parts = [payload[i:i + max_payload] for i in range(0, len(payload), max_payload)]
        packets = []
        for i, part in enumerate(parts):
            tagged_payload = f"{i+1}:{len(parts)}|{part}"
            if LOG_PAYLOAD_VALIDATION:
                log_event(f"Payload part {i+1}/{len(parts)}: {tagged_payload}", payload_validation=True, multi_packet=True)
            address = encode_callsign(dest) + encode_callsign(source, last=True)
            frame = address + b'\x03\xF0' + tagged_payload.encode()
            fcs = crc16(frame).to_bytes(2, 'little')
            packet = b'\x7E' + frame + fcs + b'\x7E'
            if LOG_AX25_PACKET:
                log_event(f"Built AX.25 packet {i+1}/{len(parts)}: dest={dest}, src={source}, payload={tagged_payload}", ax25_packet=True, multi_packet=True)
            packets.append(packet)
        return packets
    if LOG_PAYLOAD_VALIDATION:
        log_event(f"Payload validated: {payload}", ui=False, payload_validation=True)
    if LOG_PACKET_LENGTH:
        log_event(f"Payload length: {len(payload)} bytes", ui=False, packet_length=True)
    address = encode_callsign(dest) + encode_callsign(source, last=True)
    frame = address + b'\x03\xF0' + payload.encode()
    if LOG_PACKET_RAW_BYTES:
        log_event(f"Frame bytes before FCS: {frame.hex()}", ui=False, packet_raw_bytes=True)
    fcs = crc16(frame).to_bytes(2, 'little')
    packet = b'\x7E' + frame + fcs + b'\x7E'
    if LOG_AX25_PACKET:
        log_event(f"Built AX.25 packet: dest={dest}, src={source}, payload={payload}, hex={packet.hex()}", ui=False, ax25_packet=True)
    if LOG_AX25_FRAME_VALIDATION:
        log_event(f"Validated AX.25 frame: {packet.hex()}", ui=False, ax25_frame_validation=True)
    if LOG_PACKET_LENGTH:
        log_event(f"AX.25 packet length: {len(packet)} bytes", ui=False, packet_length=True)
    return [packet]  # Return as list for consistency

def build_kiss_packet(ax25_packet):
    kiss_data = ax25_packet.replace(b'\xC0', b'\xDB\xDC').replace(b'\xDB', b'\xDB\xDD')
    frame = b'\xC0\x00' + kiss_data + b'\xC0'
    if LOG_KISS_FRAMING:
        log_event(f"KISS frame built: {frame.hex()}", ui=False, kiss_framing=True)
    if LOG_PACKET_LENGTH:
        log_event(f"KISS frame length: {len(frame)} bytes", ui=False, packet_length=True)
    if LOG_TRANSMISSION_VALIDATION:
        log_event(f"Pre-transmission KISS frame: {frame.hex()}", ui=False, transmission_validation=True)
    return frame

# CMS Functions
def check_push_changed():
    global last_push_mtime
    now = time.time()
    files = [f for f in CMS_PUSH_DIR.rglob('*.txt') if now - os.path.getmtime(f) <= CMS_SYNC_MAX_AGE]
    current_mtime = max([os.path.getmtime(f) for f in files] or [0])
    if current_mtime > last_push_mtime:
        last_push_mtime = current_mtime
        log_event(f"Push directory changed, new mtime: {current_mtime}", ui=False, sync_state=True, cms_sync=True)
        return True
    return False

def update_cms_push_index():
    global push_md5
    push_index_path = CMS_DIR / 'push_index.json'
    if CMS_SYNC_ENABLED and check_push_changed():
        push_dict = {"push": {}}
        now = time.time()
        txt_files = [f for f in CMS_PUSH_DIR.rglob('*.txt') if now - os.path.getmtime(f) <= CMS_SYNC_MAX_AGE]
        for filename in txt_files:
            rel_path = filename.relative_to(CMS_PUSH_DIR).as_posix()
            with open(filename, 'rb') as f:
                content = f.read()
                file_md5 = hashlib.md5(content).hexdigest()
                push_dict["push"][rel_path] = {"md5": file_md5, "mtime": os.path.getmtime(filename)}
            if LOG_CMS_SYNC:
                log_event(f"Hashed CMS push {rel_path}: {file_md5}", ui=False, cms_sync=True)
        with open(push_index_path, 'w') as f:
            json.dump(push_dict, f, indent=2)
            os.fsync(f.fileno())
        with open(push_index_path, 'r') as f:
            push_index_content = f.read()
        new_push_md5 = hashlib.md5(push_index_content.encode()).hexdigest()
        if new_push_md5 != push_md5 and push_md5 is not None:
            log_event(f"Push MD5 changed from {push_md5} to {new_push_md5}", ui=True, md5_change=True, cms_sync=True)
        push_md5 = new_push_md5
        log_event(f"Computed MD5 from push_index.json: {push_md5}", ui=False, sync_md5=True, cms_sync=True)
    elif push_md5 is None and CMS_SYNC_ENABLED:
        try:
            with open(push_index_path, 'r') as f:
                push_index_content = f.read()
            push_md5 = hashlib.md5(push_index_content.encode()).hexdigest()
        except FileNotFoundError:
            push_md5 = hashlib.md5('{"push": {}}'.encode()).hexdigest()
        log_event(f"Initial Push MD5: {push_md5}", ui=False, sync_md5=True, cms_sync=True)
    return push_md5

def list_cms_content(category):
    cat_path = CMS_DIR / category
    if not cat_path.is_dir():
        log_event(f"Invalid CMS category: {category}", ui=False, cms_operations=True)
        return f"L|{CALLSIGN}|{category}|Error: Invalid category"
    files = [f for f in cat_path.iterdir() if f.is_file() and f.suffix == ".txt"]
    response = f"L|{CALLSIGN}|{category}|{len(files)} items - " + ", ".join(f.name[:-4] for f in files) if files else "No items"
    log_event(f"Listed CMS category {category}: {response}", ui=False, cms_operations=True)
    return response

def get_cms_content(category, item_id):
    file_path = CMS_DIR / category / f"{item_id}.txt"
    if not file_path.is_file():
        log_event(f"CMS item not found: {file_path}", ui=False, cms_operations=True)
        return f"G001/001|{CALLSIGN}|{category}|{item_id}|Error: Item not found"
    with open(file_path, "r") as f:
        content = f.read().encode()
    packets = [f"G{i+1:03d}/{len(packets):03d}|{CALLSIGN}|{category}|{item_id}|{p.hex()}"
               for i, p in enumerate(content[i:i+PACLEN-32] for i in range(0, len(content), PACLEN-32))]
    log_event(f"Sending {len(packets)} CMS packets for {file_path}", ui=False, cms_packet_build=True)
    return packets

def post_cms_content(category, item_id, content, max_age=None):
    cat_path = CMS_DIR / category
    cat_path.mkdir(parents=True, exist_ok=True)
    file_path = cat_path / f"{item_id}.txt"
    with open(file_path, "w") as f:
        f.write(content)
    if max_age:
        os.utime(file_path, times=(time.time(), time.time() + int(max_age)))
        log_event(f"Set CMS item {file_path} max_age to {max_age}s", ui=False, cms_operations=True)
    log_event(f"Posted CMS content to {file_path}", ui=False, cms_operations=True)
    return f"A|{CALLSIGN}|{category}|{item_id}|SUCCESS"

# Chunk 3 v4.0.1 - Form and CMS Sync Functions
def check_forms_changed():
    global last_mtime
    current_mtime = max([os.path.getmtime(f) for f in glob.glob(os.path.join(FORMS_DIR, '*.txt'))] or [0])
    if current_mtime > last_mtime:
        last_mtime = current_mtime
        log_event(f"Forms directory changed, new mtime: {current_mtime}", ui=False, sync_state=True)
        return True
    return False

def update_forms_index():
    """Rebuild forms_index.json and compute MD5 from its content."""
    global forms_md5
    forms_index_path = os.path.join(FORMS_DIR, 'forms_index.json')
    if check_forms_changed():
        forms_dict = {"forms": {}}
        txt_files = glob.glob(os.path.join(FORMS_DIR, '*.txt'))
        log_event(f"Files found in {FORMS_DIR}: {txt_files}", ui=False, file_io=True)
        for filename in txt_files:
            form_id = os.path.basename(filename)[:-4]
            if form_id == 'forms_index.json':
                continue
            with open(filename, 'rb') as f:
                content = f.read()
                form_md5 = hashlib.md5(content).hexdigest()
                forms_dict["forms"][form_id] = {"md5": form_md5}
            if LOG_SYNC_FORMS:
                log_event(f"Hashed {form_id}: {form_md5}", ui=False, sync_forms=True)
        with open(forms_index_path, 'w') as f:
            json.dump(forms_dict, f, indent=2)
            os.fsync(f.fileno())
            log_event(f"Rebuilt and synced forms_index.json at {forms_index_path}", ui=False, json_rebuild=True, file_io=True, filesystem_sync=True)
        with open(forms_index_path, 'r') as f:
            forms_index_content = f.read()
        new_forms_md5 = hashlib.md5(forms_index_content.encode()).hexdigest()
        if new_forms_md5 != forms_md5 and forms_md5 is not None:
            log_event(f"MD5 changed from {forms_md5} to {new_forms_md5}", ui=True, md5_change=True)
        forms_md5 = new_forms_md5
        log_event(f"Computed MD5 from forms_index.json: {forms_md5}", ui=False, sync_md5=True)
    elif forms_md5 is None:
        try:
            with open(forms_index_path, 'r') as f:
                forms_index_content = f.read()
            forms_md5 = hashlib.md5(forms_index_content.encode()).hexdigest()
            log_event(f"Initial MD5 from forms_index.json: {forms_md5}", ui=False, sync_md5=True)
        except FileNotFoundError:
            forms_md5 = hashlib.md5('{"forms": {}}'.encode()).hexdigest()
            log_event("No forms_index.json found, using empty default MD5: " + forms_md5, ui=False, sync_md5=True)
    return forms_md5

def broadcast_forms_md5(stop_event):
    global forms_md5, push_md5, last_md5_time
    log_event("Starting broadcast_forms_md5 thread", ui=False, thread_state=True)
    kiss_socket_ready.wait()
    log_event("kiss_socket ready, proceeding with broadcasts", ui=False, thread_sync=True)
    if forms_md5 is None:
        forms_md5 = update_forms_index()
        log_event(f"Initial MD5 set: {forms_md5}", ui=False, sync_md5=True)
    if push_md5 is None and CMS_SYNC_ENABLED:
        push_md5 = update_cms_push_index()
    while not stop_event.is_set():
        start_time = time.time()
        try:
            if check_forms_changed():
                previous_md5 = forms_md5
                forms_md5 = update_forms_index()
                if LOG_SYNC_MD5:
                    log_event(f"MD5 recalculated due to forms change: {forms_md5}", ui=False, sync_md5=True)
            if CMS_SYNC_ENABLED and check_push_changed():
                push_md5 = update_cms_push_index()
            # Forms MD5
            payload = f"M|{CALLSIGN}|NONE|{forms_md5}"
            ax25_packets = build_ax25_packet(CALLSIGN, "ALL", payload)
            for ax25_packet in ax25_packets:
                kiss_frame = build_kiss_packet(ax25_packet)
                kiss_socket.send(kiss_frame)
                log_comms(f"0{CALLSIGN}>ALL:{payload}")
            # CMS Push MD5
            if CMS_SYNC_ENABLED:
                payload = f"M|{CALLSIGN}|PUSH|{push_md5}"
                ax25_packets = build_ax25_packet(CALLSIGN, "ALL", payload)
                for ax25_packet in ax25_packets:
                    kiss_frame = build_kiss_packet(ax25_packet)
                    kiss_socket.send(kiss_frame)
                    log_comms(f"0{CALLSIGN}>ALL:{payload}")
            last_md5_time = datetime.now().strftime('%H:%M')
        except Exception as e:
            log_event(f"Broadcast failed: {e}\n{traceback.format_exc()}", ui=False, packet_send_failure=True, socket_error=True)
        elapsed = time.time() - start_time
        time.sleep(max(0, BROADCAST_INTERVAL - elapsed))

# Chunk 4 v4.0.1 - AX.25 Handling
def handle_ax25(stop_event):
    global kiss_socket
    crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    log_event("Starting handle_ax25 thread", ui=False, thread_state=True)
    kiss_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    kiss_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        kiss_socket.connect((FAKE_DIREWOLF_HOST, FAKE_DIREWOLF_PORT))
        log_event(f"Connected to Fake Direwolf at {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT}", ui=False, ax25_state=True)
        kiss_socket_ready.set()
    except Exception as e:
        log_event(f"Failed to connect to Fake Direwolf: {e}\n{traceback.format_exc()}", ui=False, startup_errors=True)
        stop_event.set()
        return
    buffer = b""
    segments = {}
    while not stop_event.is_set():
        readable, _, _ = select.select([kiss_socket], [], [], 1.0)
        if readable:
            try:
                data = kiss_socket.recv(512)
                if not data:
                    raise ConnectionError("Fake Direwolf disconnected")
                buffer += data
                if LOG_KISS_PACKET_RECEIVED:
                    log_event(f"Raw data received: {data.hex()}", ui=False, kiss_packet_received=True)
                while b'\xC0' in buffer[1:]:
                    start = buffer.find(b'\xC0')
                    end = buffer.find(b'\xC0', start + 1)
                    if end == -1:
                        break
                    frame = buffer[start:end + 1]
                    buffer = buffer[end + 1:]
                    ax25_packet = frame[2:-1]  # Strip KISS framing
                    if len(ax25_packet) < 18 or ax25_packet[0] != 0x7E or ax25_packet[-1] != 0x7E:
                        log_event(f"Invalid AX.25 frame: {frame.hex()[:50]}", ui=False, ax25_parse_error=True)
                        continue
                    frame_content = ax25_packet[1:-3]  # Exclude start flag, FCS, end flag
                    received_fcs = ax25_packet[-3:-1]  # FCS is 2 bytes before end flag
                    calculated_fcs = crc16(frame_content).to_bytes(2, 'little')
                    if LOG_AX25_FCS:
                        log_event(f"FCS check - Received: {received_fcs.hex()}, Calculated: {calculated_fcs.hex()}", ui=False, ax25_fcs=True)
                    if received_fcs != calculated_fcs:
                        log_event(f"FCS mismatch: {frame.hex()[:50]}", ui=False, ax25_parse_error=True)
                        continue
                    address = ax25_packet[1:15]
                    dest = ''.join(chr(b >> 1) for b in address[:6]).strip()
                    src = ''.join(chr(b >> 1) for b in address[7:13]).strip()
                    payload_start = 17
                    payload_end = -3
                    raw_payload = ax25_packet[payload_start:payload_end]
                    payload = raw_payload.decode('ascii', errors='replace')
                    if payload.startswith("C|"):
                        payload = zlib.decompress(bytes.fromhex(payload[2:])).decode('ascii', errors='replace')
                    log_comms(f"0{src}>{dest}:{payload}")
                    parts = payload.split('|', 3)
                    if len(parts) != 4:
                        log_event(f"Malformed packet payload: {payload[:50]}", ui=False, segment_failure=True)
                        continue
                    function, callsign, form_id, payload_content = parts
                    if ':' in payload_content[:5] and function in ['X', 'S', 'I', 'L', 'G', 'P']:
                        seq_total, content = payload_content.split('|', 1)
                        seq, total = map(int, seq_total.split(':'))
                        key = f"{callsign}:{form_id}"
                        response_parts.setdefault(key, {})[seq] = content
                        log_event(f"Received part {seq}/{total} for {key}", multi_packet=True, buffer_management=True)
                        if len(response_parts[key]) == total:
                            full_payload = ''.join(response_parts[key][i] for i in range(1, total + 1))
                            log_event(f"Assembled full payload for {key}: {full_payload[:50]}", buffer_management=True)
                            packet_queue.put_nowait((callsign, f"0{src}>{dest}:{function}|{callsign}|{form_id}|{full_payload}", time.time()))
                            del response_parts[key]
                        continue
                    last_data_time = time.time()
                    with clients_lock:
                        if callsign not in [c[0] for c in clients]:
                            clients.append((callsign, last_data_time))
                        else:
                            for i, (cs, _) in enumerate(clients):
                                if cs == callsign:
                                    clients[i] = (cs, last_data_time)
                                    break
                    packet_queue.put_nowait((callsign, f"0{src}>{dest}:{payload}", last_data_time))
                    if LOG_PACKET_HANDLING:
                        log_event(f"Packet enqueued: {payload[:50]}", packet_handling=True)
            except Exception as e:
                log_event(f"AX.25 error: {e}\n{traceback.format_exc()}", ui=False, segment_failure=True)
                break
        time.sleep(0.1)
    kiss_socket.close()
    log_event("Fake Direwolf connection closed", ui=False, ax25_state=True)

# Chunk 5 v4.0.1 - Forms Management Utils
def load_form_data(form_id):
    file_path = os.path.join(FORMS_DIR, form_id + ".txt")
    if not os.path.exists(file_path):
        log_event("Form file not found: " + file_path, ui=False, file_io=True)
        return None
    form_data = {'desc': '', 'fields': {}}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('desc:'):
                form_data['desc'] = line.split(':', 1)[1]
            else:
                fid, label, row, col, length = line.split(',')
                form_data['fields'][fid] = {
                    'label': label,
                    'row': int(row),
                    'col': int(col),
                    'len': int(length)
                }
    if LOG_FILE_IO:
        log_event(f"Loaded form data from {file_path}", file_io=True)
    return form_data

def create_form(form_id, desc, fields):
    file_path = os.path.join(FORMS_DIR, form_id + ".txt")
    with open(file_path, 'w') as f:
        f.write("desc:" + desc + "\n")
        for fid, field in fields.items():
            f.write(fid + "," + field['label'] + "," + str(field['row']) + "," + str(field['col']) + "," + str(field['len']) + "\n")
        os.fsync(f.fileno())
        log_event(f"Ensured {file_path} synced to disk", ui=False, file_io=True, filesystem_sync=True)
    log_event("Created/Updated form: " + form_id, ui=False, file_io=True)

# Chunk 6 v4.0.1 - People.csv Initialization
def init_people_csv():
    people_file = os.path.join(DATA_DIR, 'people.csv')
    if not os.path.exists(people_file) or os.path.getsize(people_file) == 0:
        log_event("Seeding " + people_file + " with initial data", ui=False, file_io=True)
        with open(people_file, 'w') as f:
            f.write("id,name\n")
            f.write("P001,John Doe\n")
            f.write("P002,Jane Smith\n")
            f.write("P003,Alice Johnson\n")
            f.write("P004,Bob Brown\n")
            f.write("P005,Carol White\n")
            f.write("P006,David Green\n")
        log_event("Seeded " + people_file + " with 6 entries", ui=False, file_io=True)

# Chunk 7 v4.0.1 - UI Colors
def init_colors():
    log_event("Initializing colors", ui=False)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
    return 1, 2, 3, 4

# Chunk 8 v4.0.1 - Forms Management Screen
def forms_management_screen(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    selection = 0
    screen_dirty = True
    while True:
        all_files = glob.glob(os.path.join(FORMS_DIR, '*.txt'))
        forms = sorted([os.path.basename(f) for f in all_files if not f.endswith('forms_index.json.txt')])
        if screen_dirty:
            stdscr.clear()
            RED, GREEN, _, LIGHT_BLUE = init_colors()
            max_y, max_x = stdscr.getmaxyx()
            border = "=" * (max_x - 2)
            stdscr.addstr(0, 0, border, curses.color_pair(RED))
            stdscr.addstr(1, 2, "Forms Management", curses.color_pair(LIGHT_BLUE))
            stdscr.addstr(2, 2, "Current Forms:", curses.color_pair(LIGHT_BLUE))
            for i, form in enumerate(forms[:15], start=3):
                form_name = form[:-4]
                if i - 3 == selection:
                    stdscr.addstr(i, 4, form_name, curses.color_pair(GREEN) | curses.A_REVERSE)
                else:
                    stdscr.addstr(i, 4, form_name, curses.color_pair(GREEN))
            if forms and selection < len(forms):
                form_id = forms[selection][:-4]
                form_data = load_form_data(form_id)
                if form_data:
                    stdscr.addstr(2, 40, "Form: " + form_id, curses.color_pair(LIGHT_BLUE))
                    stdscr.addstr(3, 40, "Desc: " + form_data['desc'][:36], curses.color_pair(GREEN))
                    stdscr.addstr(4, 40, "ID:Label (Row,Col,Len)", curses.color_pair(LIGHT_BLUE))
                    line = 5
                    for fid, field in sorted(form_data['fields'].items()):
                        if line < 18:
                            text = fid + ":" + field['label'] + " (" + str(field['row']) + "," + str(field['col']) + "," + str(field['len']) + ")"
                            stdscr.addstr(line, 42, text[:36], curses.color_pair(GREEN))
                            line += 1
            options_text = "(C)reate (E)dit (D)elete E(s)c"
            start_x = (max_x - len(options_text)) // 2
            stdscr.addstr(max_y - 2, start_x, options_text, curses.color_pair(GREEN))
            stdscr.addstr(max_y - 1, 0, border, curses.color_pair(RED))
            stdscr.refresh()
            screen_dirty = False
        char = stdscr.getch()
        if char == -1:
            continue
        if char == curses.KEY_UP and selection > 0:
            selection -= 1
            screen_dirty = True
        elif char == curses.KEY_DOWN and selection < len(forms) - 1 and selection < 14:
            selection += 1
            screen_dirty = True
        elif char == ord('c') or char == ord('C'):
            form_edit_screen(stdscr, None)
            screen_dirty = True
        elif char == 10 and forms:
            form_id = forms[selection][:-4]
            form_edit_screen(stdscr, form_id)
            screen_dirty = True
        elif char == ord('d') or char == ord('D') and forms:
            form_id = forms[selection][:-4]
            stdscr.clear()
            stdscr.addstr(0, 0, "Delete Form: " + form_id, curses.color_pair(LIGHT_BLUE))
            stdscr.addstr(2, 2, "Confirm Delete (Y/N)? ", curses.color_pair(GREEN))
            stdscr.refresh()
            stdscr.nodelay(False)
            char = stdscr.getch()
            stdscr.nodelay(True)
            if char == ord('y') or char == ord('Y'):
                os.remove(os.path.join(FORMS_DIR, form_id + ".txt"))
                log_event(f"Deleted form: {form_id}", ui=False, form_deletion=True)
            screen_dirty = True
        elif char == 27:
            return

# Chunk 9 v4.0.1 - Form Edit Screen
def form_edit_screen(stdscr, form_id):
    curses.curs_set(0)
    stdscr.nodelay(True)
    screen_dirty = True
    RED, GREEN, _, LIGHT_BLUE = init_colors()
    max_y, max_x = stdscr.getmaxyx()
    cursor_row, cursor_col = 3, 13
    table = defaultdict(lambda: {'label': ''})
    if form_id:
        form_data = load_form_data(form_id)
        if form_data:
            table[(3, 13)] = {'label': form_id}
            table[(3, 49)] = {'label': form_data['desc']}
            for fid, field in sorted(form_data['fields'].items(), key=lambda x: (x[1]['row'], x[1]['col'])):
                row = field['row'] + 1 if field['row'] > 3 else field['row']
                col = 13 if field['col'] == 12 else 49
                table[(row, col)] = {'label': field['label']}
    else:
        table[(3, 13)] = {'label': '(Form ID)'}
        table[(3, 49)] = {'label': '(Form Description)'}
    while True:
        if screen_dirty:
            stdscr.clear()
            border = "=" * (max_x - 2)
            stdscr.addstr(0, 0, border, curses.color_pair(RED))
            for row in range(3, 18):
                left = table[(row, 13)]['label']
                right = table[(row, 49)]['label']
                stdscr.addstr(row, 13, "[", curses.color_pair(GREEN))
                stdscr.addstr(row, 14, left[:34].ljust(34), curses.color_pair(GREEN if row > 3 else LIGHT_BLUE))
                stdscr.addstr(row, 48, "]", curses.color_pair(GREEN))
                stdscr.addstr(row, 49, "[", curses.color_pair(GREEN))
                stdscr.addstr(row, 50, right[:29].ljust(29), curses.color_pair(GREEN if row > 3 else LIGHT_BLUE))
                stdscr.addstr(row, 79, "]", curses.color_pair(GREEN))
                if row == cursor_row:
                    stdscr.addstr(row, cursor_col, '■', curses.color_pair(GREEN))
            stdscr.addstr(max_y - 2, 2, "= Arrows/Tab/Shift-Tab=Move D=Delete S=Submit C=Cancel =", curses.color_pair(GREEN))
            stdscr.addstr(max_y - 1, 0, border, curses.color_pair(RED))
            stdscr.refresh()
            screen_dirty = False
        char = stdscr.getch()
        if char == -1:
            time.sleep(0.05)
            continue
        if char == curses.KEY_UP and cursor_row > 3:
            cursor_row -= 1
            screen_dirty = True
        elif char == curses.KEY_DOWN and cursor_row < 17:
            cursor_row += 1
            screen_dirty = True
        elif char == curses.KEY_RIGHT and cursor_col == 13:
            cursor_col = 49
            screen_dirty = True
        elif char == curses.KEY_LEFT and cursor_col == 49:
            cursor_col = 13
            screen_dirty = True
        elif char == 9:
            if cursor_col == 13 and cursor_row < 17:
                cursor_col = 49
            elif cursor_col == 49 and cursor_row < 17:
                cursor_col = 13
                cursor_row += 1
            elif cursor_row == 17:
                cursor_col = 13
                cursor_row = 3
            screen_dirty = True
        elif char == curses.KEY_BTAB:
            if cursor_col == 49 and cursor_row > 3:
                cursor_col = 13
            elif cursor_col == 13 and cursor_row > 3:
                cursor_col = 49
                cursor_row -= 1
            elif cursor_row == 3:
                cursor_col = 49
                cursor_row = 17
            screen_dirty = True
        elif char == 10:
            stdscr.nodelay(False)
            curses.curs_set(1)
            col_name = 'L' if cursor_col == 13 else 'R'
            current_label = table[(cursor_row, cursor_col)]['label']
            max_len = 34 if col_name == 'L' else 29
            stdscr.addstr(cursor_row, cursor_col + 1, " " * max_len, curses.color_pair(GREEN))
            curses.echo()
            new_label = stdscr.getstr(cursor_row, cursor_col + 1, max_len).decode().strip()
            curses.noecho()
            if new_label and new_label not in ['(Form ID)', '(Form Description)']:
                table[(cursor_row, cursor_col)] = {'label': new_label}
            elif not new_label and current_label in ['(Form ID)', '(Form Description)']:
                table[(cursor_row, cursor_col)] = {'label': current_label}
            stdscr.nodelay(True)
            curses.curs_set(0)
            screen_dirty = True
        elif char == ord('d') or char == ord('D'):
            if table[(cursor_row, cursor_col)]['label'] not in ['(Form ID)', '(Form Description)']:
                del table[(cursor_row, cursor_col)]
                screen_dirty = True
        elif char == ord('s') or char == ord('S'):
            form_id_val = table[(3, 13)]['label']
            form_desc = table[(3, 49)]['label']
            if (form_id_val not in ['', '(Form ID)'] and
                form_desc not in ['', '(Form Description)'] and
                any(table[(r, c)]['label'] not in ['', '(Form ID)', '(Form Description)'] for r, c in table if r > 3)):
                fields_dict = {}
                for (row, col) in sorted(table.keys()):
                    label = table[(row, col)]['label']
                    if label and label not in ['(Form ID)', '(Form Description)']:
                        fid = f"{'L' if col == 13 else 'R'}{row - 2:02d}"
                        fields_dict[fid] = {
                            'label': label.upper() if row == 3 else label,
                            'row': row,
                            'col': 12 if col == 13 else 32,
                            'len': 256
                        }
                create_form(form_id_val.upper(), form_desc.upper(), fields_dict)
                return
            screen_dirty = True
        elif char == ord('c') or char == ord('C'):
            stdscr.nodelay(False)
            curses.curs_set(0)
            stdscr.addstr(max_y - 2, 2, "Are you sure? (Y/N) ", curses.color_pair(GREEN))
            stdscr.refresh()
            if LOG_UI_TRANSITIONS:
                log_event(f"Prompting confirmation for cancel in form_edit_screen (form_id={form_id})", ui_transitions=True)
            confirm_char = stdscr.getch()
            if confirm_char in [ord('y'), ord('Y')]:
                if LOG_UI_TRANSITIONS:
                    log_event(f"User confirmed cancel (Y), exiting form_edit_screen (form_id={form_id})", ui_transitions=True)
                stdscr.nodelay(True)
                return
            else:
                if LOG_UI_TRANSITIONS:
                    log_event(f"User declined cancel ({chr(confirm_char) if confirm_char != -1 else 'timeout'}), staying in form_edit_screen (form_id={form_id})", ui_transitions=True)
            stdscr.addstr(max_y - 2, 2, " " * 20, curses.color_pair(GREEN))
            stdscr.nodelay(True)
            screen_dirty = True
        elif char == 27:
            return

# Chunk 10 v4.0.1 - CMS Management Screen
def cms_management_screen(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    selection = 0
    screen_dirty = True
    while True:
        categories = [str(Path(d).relative_to(CMS_DIR)) for d, _, _ in os.walk(CMS_DIR) if d != str(CMS_DIR)]
        if screen_dirty:
            stdscr.clear()
            RED, GREEN, _, LIGHT_BLUE = init_colors()
            max_y, max_x = stdscr.getmaxyx()
            border = "=" * (max_x - 2)
            stdscr.addstr(0, 0, border, curses.color_pair(RED))
            stdscr.addstr(1, 2, "CMS Management", curses.color_pair(LIGHT_BLUE))
            stdscr.addstr(2, 2, "Categories:", curses.color_pair(LIGHT_BLUE))
            for i, cat in enumerate(categories[:15], start=3):
                if i - 3 == selection:
                    stdscr.addstr(i, 4, cat, curses.color_pair(GREEN) | curses.A_REVERSE)
                else:
                    stdscr.addstr(i, 4, cat, curses.color_pair(GREEN))
            if categories and selection < len(categories):
                cat = categories[selection]
                files = [f.name[:-4] for f in (CMS_DIR / cat).glob('*.txt')]
                stdscr.addstr(2, 40, f"Items in {cat}:", curses.color_pair(LIGHT_BLUE))
                for i, item in enumerate(files[:10], start=3):
                    stdscr.addstr(i, 42, item, curses.color_pair(GREEN))
            stdscr.addstr(max_y - 2, 2, "= Up/Down=Select Esc=Back =", curses.color_pair(GREEN))
            stdscr.addstr(max_y - 1, 0, border, curses.color_pair(RED))
            stdscr.refresh()
            screen_dirty = False
            if LOG_CMS_UI_STATE:
                log_event(f"CMS UI rendered: selection={selection}, categories={categories[:15]}", ui=False, cms_ui_state=True)
        char = stdscr.getch()
        if char == -1:
            continue
        if char == curses.KEY_UP and selection > 0:
            selection -= 1
            screen_dirty = True
        elif char == curses.KEY_DOWN and selection < len(categories) - 1 and selection < 14:
            selection += 1
            screen_dirty = True
        elif char == 27:
            return

# Chunk 11 v4.0.1 - Update UI
def update_ui(stdscr):
    global screen_dirty, show_menu, menu_selection
    if not screen_dirty:
        return
    max_y, max_x = stdscr.getmaxyx()
    stdscr.clear()
    border = "=" * (max_x - 2)
    stdscr.addstr(0, 0, border, curses.color_pair(1))
    stdscr.addstr(1, 2, "Packet Radio Server", curses.color_pair(4))
    stdscr.addstr(1, 40, "Direwolf [Connected]", curses.color_pair(4))
    stdscr.addstr(2, 2, f"Callsign:{CALLSIGN}", curses.color_pair(4))
    stdscr.addstr(3, 2, "Recent Clients:", curses.color_pair(4))
    stdscr.addstr(2, 40, "Comms Log", curses.color_pair(4))
    stdscr.addstr(3, 40, "=" * 19, curses.color_pair(1))
    with clients_lock:
        now = time.time()
        clients[:] = [(cs, ls) for cs, ls in clients if now - ls < CLIENT_TIMEOUT]
        for i, (callsign, last_data_time) in enumerate(clients[:max_y-6], start=4):
            timestamp = datetime.fromtimestamp(last_data_time).strftime('%H:%M:%S')
            display = f"{callsign} - {timestamp}"[:35]
            stdscr.addstr(i, 4, display, curses.color_pair(2))
    for i, (msg, ts) in enumerate(comms_log[-(max_y-7):], start=4):
        if i < max_y-3:
            stdscr.addstr(i, 40, (msg[:38] + " - " + ts)[:38], curses.color_pair(2))
    stdscr.addstr(max_y-2, 40, f"Last MD5 broadcast: {last_md5_time or 'N/A'}", curses.color_pair(2))
    stdscr.addstr(max_y-1, 40, f"Forms MD5: {forms_md5 or 'N/A'}", curses.color_pair(2))
    stdscr.addstr(max_y-3, 40, f"Push MD5: {push_md5 or 'N/A'}", curses.color_pair(2))  # Added CMS push MD5
    stdscr.addstr(max_y-2, 2, "-= Commands: D=Menu =-", curses.color_pair(2))
    stdscr.addstr(max_y-1, 0, border, curses.color_pair(1))
    if show_menu:
        menu_width = 22
        menu_height = 8
        menu_y = (max_y - menu_height) // 2
        menu_x = (max_x - menu_width) // 2
        options = [("Main Screen", True), ("Forms Management", True), ("CMS Management", True), ("Quit", True)]
        stdscr.addstr(menu_y, menu_x, "+====================+", curses.color_pair(1))
        for i, (opt, active) in enumerate(options):
            color = 2 if active else 1
            if i == menu_selection:
                stdscr.addstr(menu_y + 1 + i, menu_x, "| " + opt.ljust(18) + " |", curses.color_pair(color) | curses.A_REVERSE)
            else:
                stdscr.addstr(menu_y + 1 + i, menu_x, "| " + opt.ljust(18) + " |", curses.color_pair(color))
        stdscr.addstr(menu_y + 5, menu_x, "| Up/Down=Move       |", curses.color_pair(2))
        stdscr.addstr(menu_y + 6, menu_x, "| Enter=Sel Esc=Back Are |", curses.color_pair(2))
        stdscr.addstr(menu_y + 7, menu_x, "+====================+", curses.color_pair(1))
    stdscr.refresh()
    screen_dirty = False

# Chunk 12 v4.0.1 - Main Loop
def main(stdscr):
    global CALLSIGN, screen_dirty, show_menu, menu_selection, kiss_socket
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FORMS_DIR, exist_ok=True)
    os.makedirs(CMS_DIR, exist_ok=True)
    CALLSIGN = get_callsign(stdscr)
    RED, GREEN, YELLOW, LIGHT_BLUE = init_colors()
    stdscr.clear()
    stdscr.nodelay(True)
    stdscr.refresh()
    log_event(f"Server starting with AX.25 on {FAKE_DIREWOLF_HOST}:{FAKE_DIREWOLF_PORT} (v{VERSION})", ui=False, ax25_state=True)
    init_people_csv()
    stop_event = threading.Event()
    broadcast_thread = threading.Thread(target=broadcast_forms_md5, args=(stop_event,))
    broadcast_thread.daemon = True
    broadcast_thread.start()
    ax25_thread = threading.Thread(target=handle_ax25, args=(stop_event,))
    ax25_thread.daemon = True
    ax25_thread.start()
    kiss_socket_ready.wait()
    while True:
        update_ui(stdscr)
        char = stdscr.getch()
        if char == ord('q') or char == ord('Q') and not show_menu:
            stop_event.set()
            kiss_socket.close()
            log_event("Server shutdown complete", ui=False, ax25_state=True)
            break
        elif char == ord('d') or char == ord('D'):
            show_menu = not show_menu
            menu_selection = 0
            screen_dirty = True
        elif show_menu:
            if char == curses.KEY_UP and menu_selection > 0:
                menu_selection -= 1
                screen_dirty = True
            elif char == curses.KEY_DOWN and menu_selection < 3:
                menu_selection += 1
                screen_dirty = True
            elif char == 10:
                if menu_selection == 0:
                    show_menu = False
                elif menu_selection == 1:
                    forms_management_screen(stdscr)
                elif menu_selection == 2:
                    cms_management_screen(stdscr)
                elif menu_selection == 3:
                    stop_event.set()
                    kiss_socket.close()
                    log_event("Server shutdown complete", ui=False, ax25_state=True)
                    break
                screen_dirty = True
            elif char == 27:
                show_menu = False
                screen_dirty = True
        if not show_menu or menu_selection not in [1, 2]:
            while not packet_queue.empty():
                try:
                    callsign, packet, last_data_time = packet_queue.get_nowait()
                    header, payload = packet.split(':', 1)
                    parts = payload.split('|', 3)
                    if len(parts) != 4:
                        log_event(f"Malformed packet: {payload[:50]}", ui=False, segment_failure=True)
                        continue
                    function, _, form_id, payload_content = parts
                    if LOG_PACKET_HANDLING:
                        log_event(f"Processing packet: function={function}, callsign={callsign}, form_id={form_id}", packet_handling=True)
                    if function == 'I':
                        log_event(f"Received I (INSERT) from {callsign} for {form_id}: {payload_content[:50]}", ui=False, submissions=True)
                        if LOG_COMMAND_VALIDATION:
                            log_event(f"Validated command 'I' as INSERT", command_validation=True)
                        if ':' in payload_content[:5]:
                            seq, total = map(int, payload_content.split('|', 1)[0].split(':'))
                            payload_content = payload_content.split('|', 1)[1]
                            key = callsign + ":" + form_id
                            segments.setdefault(key, {})[seq] = payload_content
                            if len(segments[key]) == total:
                                full_payload = ''.join(segments[key][i] for i in sorted(segments[key]))
                                csv_path = os.path.join(DATA_DIR, form_id + "_submissions.csv")
                                os.makedirs(DATA_DIR, exist_ok=True)
                                with open(csv_path, 'a') as f:
                                    f.write(f"{int(time.time())},{callsign},{full_payload}\n")
                                if LOG_FILE_IO:
                                    log_event(f"Wrote segmented payload to {csv_path}", file_io=True)
                                response = f"A|{CALLSIGN}|{form_id}|SUCCESS"
                                ax25_packets = build_ax25_packet(CALLSIGN, callsign, response)
                                for ax25_packet in ax25_packets:
                                    kiss_frame = build_kiss_packet(ax25_packet)
                                    kiss_socket.send(kiss_frame)
                                    log_comms(f"0{CALLSIGN}>{callsign}:{response}")
                                if LOG_SYNC_RESPONSE:
                                    log_event(f"Sent A (ACK) to {callsign} for {form_id}", ui=False, sync_response=True)
                                del segments[key]
                        else:
                            csv_path = os.path.join(DATA_DIR, form_id + "_submissions.csv")
                            os.makedirs(DATA_DIR, exist_ok=True)
                            with open(csv_path, 'a') as f:
                                f.write(f"{int(time.time())},{callsign},{payload_content}\n")
                            if LOG_FILE_IO:
                                log_event(f"Wrote payload to {csv_path}", file_io=True)
                            response = f"A|{CALLSIGN}|{form_id}|SUCCESS"
                            ax25_packets = build_ax25_packet(CALLSIGN, callsign, response)
                            for ax25_packet in ax25_packets:
                                kiss_frame = build_kiss_packet(ax25_packet)
                                kiss_socket.send(kiss_frame)
                                log_comms(f"0{CALLSIGN}>{callsign}:{response}")
                            if LOG_SYNC_RESPONSE:
                                log_event(f"Sent A (ACK) to {callsign} for {form_id}", ui=False, sync_response=True)
                    elif function == 'S':
                        log_event(f"Received S (SEARCH) from {callsign} for {form_id}: {payload_content[:50]}", ui=False, search_query=True)
                        if LOG_COMMAND_VALIDATION:
                            log_event(f"Validated command 'S' as SEARCH", command_validation=True)
                        search_fields = {}
                        for pair in payload_content.split('|'):
                            if not pair:
                                continue
                            key = pair[:2]
                            value = pair[2:] if len(pair) > 2 else ""
                            search_fields[key] = value
                        csv_path = os.path.join(DATA_DIR, form_id + "_submissions.csv")
                        matches = []
                        if os.path.exists(csv_path):
                            with open(csv_path, 'r') as f:
                                for line in f:
                                    _, _, row_payload = line.strip().split(',', 2)
                                    fields = {}
                                    for field in row_payload.split('|'):
                                        if field:
                                            fields[field[:2]] = field[2:] if len(field) > 2 else ""
                                    match = all(fields.get(k, '') == v for k, v in search_fields.items() if v)
                                    if match:
                                        matches.append(row_payload)
                            if LOG_FILE_IO:
                                log_event(f"Read search data from {csv_path}", file_io=True)
                        response = f"R|{CALLSIGN}|{form_id}|{'~'.join(matches)}"
                        ax25_packets = build_ax25_packet(CALLSIGN, callsign, response)
                        for ax25_packet in ax25_packets:
                            kiss_frame = build_kiss_packet(ax25_packet)
                            kiss_socket.send(kiss_frame)
                            log_comms(f"0{CALLSIGN}>{callsign}:{response}")
                        if LOG_SYNC_RESPONSE:
                            log_event(f"Sent R (SEARCH_RESULT) to {callsign} for {form_id}", ui=False, sync_response=True)
                    elif function == 'X':
                        log_event(f"Received X (INDEX) from {callsign}: {payload_content[:50]}", ui=False, diff_state=True)
                        if LOG_COMMAND_VALIDATION:
                            log_event(f"Validated command 'X' as INDEX", command_validation=True)
                        syncing_clients.add(callsign)
                        try:
                            if form_id == "PUSH" and CMS_SYNC_ENABLED:
                                log_event(f"Received X (PUSH INDEX) from {callsign}: {payload_content[:50]}", ui=False, diff_state=True, cms_sync=True)
                                client_push = {}
                                for pair in payload_content.split('|'):
                                    if ':' in pair:
                                        fname, fhash = pair.split(':', 1)
                                        client_push[fname] = fhash
                                push_index_path = CMS_DIR / 'push_index.json'
                                try:
                                    with open(push_index_path, 'r') as f:
                                        server_push = json.load(f)['push']
                                except FileNotFoundError:
                                    server_push = {}
                                now = time.time()
                                for fname, data in server_push.items():
                                    if now - data['mtime'] > CMS_SYNC_MAX_AGE:
                                        continue
                                    if fname not in client_push or client_push[fname] != data['md5']:
                                        with open(CMS_PUSH_DIR / fname, 'r') as f:
                                            content = f.read().strip()
                                        response = f"U|{CALLSIGN}|{fname}|{content.replace('\n', '~')}"
                                        ax25_packets = build_ax25_packet(CALLSIGN, "ALL", response, compress=True)
                                        for ax25_packet in ax25_packets:
                                            kiss_frame = build_kiss_packet(ax25_packet)
                                            kiss_socket.send(kiss_frame)
                                            log_comms(f"0{CALLSIGN}>ALL:{response}")
                                        if LOG_CMS_SYNC:
                                            log_event(f"Sent U (PUSH_UPDATE) for {fname}", ui=False, cms_sync=True)
                                for fname in client_push:
                                    if fname not in server_push or (now - server_push.get(fname, {}).get('mtime', 0) > CMS_SYNC_MAX_AGE):
                                        response = f"D|{CALLSIGN}|{fname}|"
                                        ax25_packets = build_ax25_packet(CALLSIGN, "ALL", response)
                                        for ax25_packet in ax25_packets:
                                            kiss_frame = build_kiss_packet(ax25_packet)
                                            kiss_socket.send(kiss_frame)
                                            log_comms(f"0{CALLSIGN}>ALL:{response}")
                                        if LOG_CMS_SYNC:
                                            log_event(f"Sent D (PUSH_DELETE) for {fname}", ui=False, cms_sync=True)
                            else:
                                client_forms = {}
                                for pair in payload_content.split('|'):
                                    if ':' in pair:
                                        fname, fhash = pair.split(':', 1)
                                        client_forms[fname] = fhash
                                forms_index_path = os.path.join(FORMS_DIR, 'forms_index.json')
                                try:
                                    with open(forms_index_path, 'r') as f:
                                        server_forms = json.load(f)['forms']
                                    if LOG_FILE_IO:
                                        log_event(f"Read server forms from {forms_index_path}", file_io=True)
                                except FileNotFoundError:
                                    server_forms = {}
                                for fname, server_hash in server_forms.items():
                                    if fname not in client_forms or client_forms[fname] != server_hash:
                                        with open(os.path.join(FORMS_DIR, fname + ".txt"), 'r') as f:
                                            content = f.read().strip()
                                        if LOG_FORM_CONTENT:
                                            log_event(f"Raw form content for {fname}: {content}", ui=False, form_content=True)
                                        if LOG_FILE_IO:
                                            log_event(f"Read form content from {fname}.txt", file_io=True)
                                        content_replaced = content.replace('\n', '~')
                                        fields = content_replaced.split('~')
                                        sanitized_fields = []
                                        for field in fields:
                                            if ',' in field:
                                                parts = field.split(',')
                                                if len(parts) == 5:
                                                    try:
                                                        length_str = re.sub(r'[^0-9]', '', parts[4])
                                                        length = int(length_str) if length_str else 256
                                                        parts[4] = str(length)
                                                        if length_str != parts[4]:
                                                            log_event(f"Cleaned length in {fname}: {field} -> {','.join(parts)}", ui=False, form_field_validation=True)
                                                        if LOG_FORM_FIELD_SANITIZATION:
                                                            log_event(f"Sanitized field in {fname}: {field} -> {','.join(parts)}", ui=False, form_field_sanitization=True)
                                                    except ValueError:
                                                        log_event(f"Invalid length in {fname}: {field}, defaulting to 256", ui=False, form_field_validation=True)
                                                        parts[4] = "256"
                                                sanitized_fields.append(','.join(parts))
                                            else:
                                                sanitized_fields.append(field)
                                        content_replaced = '~'.join(sanitized_fields)
                                        if LOG_PACKET_SANITIZATION:
                                            log_event(f"Sanitized content for {fname}: {content_replaced}", ui=False, packet_sanitization=True)
                                        response = f"U|{CALLSIGN}|{fname}|{content_replaced}"
                                        fields = response.split('~')
                                        final_fields = [fields[0]]
                                        for field in fields[1:]:
                                            if ',' in field:
                                                parts = field.split(',')
                                                if len(parts) == 5:
                                                    parts[4] = '256'
                                                final_fields.append(','.join(parts))
                                            else:
                                                final_fields.append(field)
                                        response = '~'.join(final_fields)
                                        if LOG_PACKET_RAW_BYTES:
                                            log_event(f"Response bytes before AX.25: {response.encode().hex()}", ui=False, packet_raw_bytes=True)
                                        for field in response.split('~')[1:]:
                                            if ',' in field:
                                                try:
                                                    length = field.split(',')[-1]
                                                    int(length)
                                                except ValueError:
                                                    log_event(f"Pre-send validation failed for {fname}: {field}, aborting send", ui=False, pre_send_validation=True)
                                                    continue
                                        if LOG_PRE_SEND_VALIDATION:
                                            log_event(f"Pre-send validated U (FORM_UPDATE) packet: {response}", ui=False, pre_send_validation=True)
                                        if LOG_SYNC_PACKET_VALIDATION:
                                            log_event(f"Validated U (FORM_UPDATE) packet: {response}", ui=False, sync_packet_validation=True)
                                        ax25_packets = build_ax25_packet(CALLSIGN, "ALL", response)
                                        for ax25_packet in ax25_packets:
                                            kiss_frame = build_kiss_packet(ax25_packet)
                                            kiss_socket.send(kiss_frame)
                                            log_comms(f"0{CALLSIGN}>ALL:{response}")
                                        if LOG_SYNC_RESPONSE:
                                            log_event(f"Sent U (FORM_UPDATE) to ALL for {fname}", ui=False, sync_response=True)
                                for fname in client_forms:
                                    if fname not in server_forms:
                                        response = f"D|{CALLSIGN}|{fname}|"
                                        ax25_packets = build_ax25_packet(CALLSIGN, "ALL", response)
                                        for ax25_packet in ax25_packets:
                                            kiss_frame = build_kiss_packet(ax25_packet)
                                            kiss_socket.send(kiss_frame)
                                            log_comms(f"0{CALLSIGN}>ALL:{response}")
                                        if LOG_SYNC_RESPONSE:
                                            log_event(f"Sent D (FORM_DELETE) to ALL for {fname}", ui=False, sync_response=True)
                        finally:
                            syncing_clients.remove(callsign)
                            log_event(f"Sync completed for {callsign}", ui=False, sync_completion=True)
                    elif function == 'L':
                        response = list_cms_content(form_id)
                        ax25_packets = build_ax25_packet(CALLSIGN, callsign, response)
                        for ax25_packet in ax25_packets:
                            kiss_frame = build_kiss_packet(ax25_packet)
                            kiss_socket.send(kiss_frame)
                            log_comms(f"0{CALLSIGN}>{callsign}:{response}")
                    elif function == 'G':
                        responses = get_cms_content(form_id, payload_content)
                        for response in responses:
                            ax25_packets = build_ax25_packet(CALLSIGN, callsign, response, compress=True)
                            for ax25_packet in ax25_packets:
                                kiss_frame = build_kiss_packet(ax25_packet)
                                kiss_socket.send(kiss_frame)
                                log_comms(f"0{CALLSIGN}>{callsign}:{response}")
                    elif function == 'P':
                        category, item_id, rest = payload_content.split('|', 2)
                        content = rest
                        max_age = None
                        if '|' in rest:
                            content, max_age = rest.rsplit('|', 1)
                            max_age = max_age if max_age.isdigit() else None
                        response = post_cms_content(category, item_id, content, max_age)
                        ax25_packets = build_ax25_packet(CALLSIGN, callsign, response)
                        for ax25_packet in ax25_packets:
                            kiss_frame = build_kiss_packet(ax25_packet)
                            kiss_socket.send(kiss_frame)
                            log_comms(f"0{CALLSIGN}>{callsign}:{response}")
                    elif function not in ['I', 'S', 'X', 'U', 'D', 'M', 'A', 'R', 'G', 'C', 'L', 'G', 'P']:
                        log_event(f"Received invalid command '{function}' from {callsign}", command_validation=True)
                    packet_queue.task_done()
                except queue.Empty:
                    break
        time.sleep(0.05)

# Chunk 13 v4.0.1 - Design Goals and Statuses
# DESIGN GOALS AND CHANGES:
# - See server_mini_revisions_20250322_v4.0.1.txt for this update (v4.0.1)
# - Full history in PacketRadioTerminalServiceManual [REVISION_SUMMARY]

backup_script()

# Chunk 14 v4.0.1 - Entry Point
if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        with open(LOG_FILE, 'a') as f:
            f.write(str(datetime.now()) + " - Fatal error: " + str(e) + " - traceback: " + traceback.format_exc() + "\n")
        log_event("Startup failed: " + str(e), ui=False, startup_errors=True)
        sys.exit(1)