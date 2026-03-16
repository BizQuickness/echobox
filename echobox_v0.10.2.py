import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time
import threading
import queue
import os
import sys

# --- CONFIGURATION ---
CITY_NAME = "Roseville"
TEST_CHANNEL = 1
TRIGGER_WORD = "test"
INITIAL_DELAY = 5    # Seconds to wait before sending a PUBLIC channel reply
DM_DELAY = 5         # Seconds to wait before sending a DIRECT MESSAGE reply
COOLDOWN_DELAY = 15  # Seconds to wait before processing the next person in line
CHANNEL_HELP_ENABLED = False  # Set to True to allow "help" replies in the channel. Set to False if multiple bots are on the same channel to prevent spam!
# ---------------------

# This is our "To-Do List" (The Queue)
reply_queue = queue.Queue()

def worker():
    """ This background worker handles the 'To-Do List' one at a time """
    while True:
        task = reply_queue.get()
        if task is None: break
        
        sender_id, display_name, hops, packet_id, is_dm, response_text = task
        
        route_type = "DIRECT" if is_dm else "CHANNEL"
        print(f"[{CITY_NAME} EchoBox] Processing {route_type} reply for {display_name}...")
        
        # 1. Choose the correct delay timer
        wait_time = DM_DELAY if is_dm else INITIAL_DELAY
        time.sleep(wait_time)
        
        try:
            # 2. Send the message provided by the queue
            if is_dm:
                local_interface.sendText(
                    response_text, 
                    destinationId=sender_id, 
                    wantAck=False, 
                    replyId=packet_id
                )
            else:
                local_interface.sendText(
                    response_text, 
                    channelIndex=TEST_CHANNEL, 
                    wantAck=False, 
                    replyId=packet_id
                )
            print(f"[{CITY_NAME} EchoBox] Sent threaded {route_type} reply to {display_name}!")
            
        except TypeError:
            # Safety fallback for older Meshtastic python library versions
            if is_dm:
                local_interface.sendText(response_text, destinationId=sender_id, wantAck=False)
            else:
                local_interface.sendText(response_text, channelIndex=TEST_CHANNEL, wantAck=False)
            print(f"[{CITY_NAME} EchoBox] Sent standard reply (Update 'meshtastic' pip package for threading!)")
        except Exception as e:
            print(f"Error: {e}")
        
        # 3. Wait the custom cooldown delay to protect the radio hardware
        print(f"[{CITY_NAME} EchoBox] Cooling down for {COOLDOWN_DELAY}s...")
        time.sleep(COOLDOWN_DELAY)
        
        reply_queue.task_done()

# Start the background worker immediately
threading.Thread(target=worker, daemon=True).start()

def on_receive(packet, interface):
    try:
        if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            msg = packet['decoded']['text'].strip().lower()
            
            incoming_channel = packet.get('channel', 0)
            
            my_node_num = interface.myInfo.my_node_num
            is_dm = (packet.get('to') == my_node_num)
            
            # Check if it's our target channel or a direct message
            if incoming_channel == TEST_CHANNEL or is_dm:
                
                raw_from = packet.get('from')
                sender_id = packet.get('fromId') or f"!{raw_from:08x}"
                
                node_db = interface.nodes.get(sender_id, {})
                user_name = node_db.get('user', {}).get('shortName', sender_id)
                
                if user_name == sender_id:
                    display_name = sender_id[-4:]
                else:
                    display_name = user_name
                
                hops = packet.get('hopStart', 0) - packet.get('hopLimit', 0)
                packet_id = packet.get('id')
                route_tag = "DM" if is_dm else f"CH {incoming_channel}"

                # SCENARIO A: They sent the exact trigger word
                if msg == TRIGGER_WORD:
                    response_text = f"✅ {CITY_NAME} EchoBox heard {display_name} (Hops: {hops})"
                    print(f"📡 [PING] Adding {display_name} to the queue ({route_tag}).")
                    reply_queue.put((sender_id, display_name, hops, packet_id, is_dm, response_text))
                
                # SCENARIO B: They explicitly asked for help
                elif msg == "help":
                    # If it is a DM, always help. If it is a channel, check the toggle first!
                    if is_dm or CHANNEL_HELP_ENABLED:
                        response_text = f"ℹ️ EchoBox: Please send the exact word '{TRIGGER_WORD}' to get a signal report with hop count."
                        print(f"📡 [HELP] Adding instruction reply for {display_name} ({route_tag}).")
                        reply_queue.put((sender_id, display_name, hops, packet_id, is_dm, response_text))
                    else:
                        print(f"🔇 [HELP] Ignored channel help request from {display_name} (Channel help replies are disabled).")
                
                # SCENARIO C: They sent something random (Catch-all for DMs ONLY)
                elif is_dm:
                    response_text = f"ℹ️ EchoBox: Please send the exact word '{TRIGGER_WORD}' to get a signal report with hop count."
                    print(f"📡 [HELP] Adding instruction reply for {display_name} ({route_tag}).")
                    reply_queue.put((sender_id, display_name, hops, packet_id, is_dm, response_text))

    except Exception as e:
        print(f"Error in on_receive: {e}")

# --- THE NEW WATCHDOG ---
def on_connection_lost(interface=None):
    """ If the USB cable is unplugged or the radio reboots, kill the script! """
    print(f"🚨 [{CITY_NAME} EchoBox] Serial connection lost! Forcing systemd to restart the bot...")
    os._exit(1)  # This hard-crashes the Python script
# ------------------------

print(f"Starting {CITY_NAME} Queue-Based EchoBox...")
try:
    local_interface = meshtastic.serial_interface.SerialInterface()
    
    # Subscribe to incoming messages AND connection drops
    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_connection_lost, "meshtastic.connection.lost")
    
    print(f"✅ Online! Listening on Channel {TEST_CHANNEL} and for Direct Messages...")
    while True: time.sleep(1)
except Exception as e:
    print(f"Connection Failed on startup: {e}")
    # If it fails to even start, exit so systemd tries again
    os._exit(1)
