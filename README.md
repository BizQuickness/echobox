# EchoBox - Meshtastic Sentry Node

A robust, server-grade auto-responder script for Meshtastic networks. Designed specifically for headless deployments (like a Raspberry Pi), this script monitors designated public channels or direct messages for a trigger word and replies automatically. 

It is designed to help users test new nodes and connectivity without overloading the mesh. It features a thread-safe queue to handle simultaneous pings, intelligent airtime management, dynamic routing, and a self-healing watchdog system for hardware disconnects.

## 🚀 Key Features

* **Airtime Management & Staggering:** Built-in delay timers prevent overlapping messages. If running multiple EchoBox nodes in the same city, you can manually stagger the `INITIAL_DELAY` so they reply sequentially, drastically cutting down on mesh traffic and lost packets.
* **Smart Name Extraction:** Parses the sender's actual display name or emoji from the local node database. If the user hasn't propagated a name yet, it gracefully falls back to the last four hex digits of their Node ID.
* **Hop Calculation:** Automatically calculates and includes how many hops the original ping took to reach the EchoBox node.
* **Unified Queue System:** Uses a background worker and an infinite `queue.Queue()` to process incoming pings one at a time. Both public channel pings and Direct Messages are processed in order and protected by a hardware cooldown timer.
* **Direct Message Routing:** Users who don't want to spam the public channel can Direct Message the node. The EchoBox detects this, applies a separate DM delay timer, and replies privately using threaded messaging.
* **Self-Healing Hardware Watchdog:** Subscribes to `meshtastic.connection.lost`. If the USB cable is unplugged or the radio restarts, the script intentionally triggers a hard crash. When paired with a Linux `systemd` service, this forces the Pi to automatically heal the connection and restart the bot.

## 🔌 Hardware Setup



1. Flash your Meshtastic node (e.g., LILYGO T-Echo, Heltec V3 or V4) with the latest firmware.
2. Connect the node directly to your Raspberry Pi using a high-quality data USB cable.
3. Ensure the node is powered and recognized by the Pi.

## ⚙️ Configuration & Multi-Node Setup

The script contains a simple configuration block at the top of `echobox.py`. Adjust these variables before deployment:

* `CITY_NAME`: The display name your bot uses in replies (e.g., "Roseville").
* `TEST_CHANNEL`: The channel index to listen on (`0` for Primary, `1` for Secondary).
* `TRIGGER_WORD`: The exact text string the bot listens for (e.g., "test").

### Programming Multiple Nodes (Staggering)
If you are deploying multiple EchoBox nodes in the same area to test mesh coverage, you **must** stagger their public channel replies to prevent packet collisions. Leave the `DM_DELAY` at 5 seconds for all nodes, but change the `INITIAL_DELAY`:

* **Node 1 (e.g., North Node):**
  * `INITIAL_DELAY = 5`
* **Node 2 (e.g., Central Node):**
  * `INITIAL_DELAY = 25`
* **Node 3 (e.g., South Node):**
  * `INITIAL_DELAY = 45`

## 🛠️ Installation & Setup (Raspberry Pi)

This guide walks you through setting up the EchoBox script on a Raspberry Pi using a `systemd` service to ensure 24/7 uptime.

### 1. Install Prerequisites
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Prepare the Environment
Create a dedicated folder for the script and initialize a Python virtual environment:
```bash
mkdir ~/echobox
cd ~/echobox
python3 -m venv venv
source venv/bin/activate
pip install meshtastic pubsub
```

### 3. Add the Script
Create your Python file and paste the echobox.py code into it:
```bash
nano echobox.py
```
(Save and exit: Ctrl+O, Enter, Ctrl+X)

Test it manually to ensure it connects (optional):
```bash
python3 echobox.py
```
(Press Ctrl+C to stop the manual test).

### 4. Create the systemd Service (Power Outage Protection)
Create a service file to run the script in the background automatically:
```bash
sudo nano /etc/systemd/system/echobox.service
```

Paste the following configuration. ⚠️ IMPORTANT: Replace `pi` with your actual Raspberry Pi username if it is different!

Ini, TOML
```
[Unit]
Description=Meshtastic EchoBox Node
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/echobox
ExecStart=/home/pi/echobox/venv/bin/python3 /home/pi/echobox/echobox.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
(Save and exit: Ctrl+O, Enter, Ctrl+X)

### 5. Enable and Start the Service
Enable the script to start on boot and launch it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable echobox.service
sudo systemctl start echobox.service
```
Helpful Commands:
* View live logs: `journalctl -u echobox.service -f`
* Stop the bot: `sudo systemctl stop echobox.service`
* Restart the bot: `sudo systemctl restart echobox.service`
