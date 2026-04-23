
# Network
RASPBERRY_PI_IP = "192.168.1.100"
PILOT_STATION_IP = "192.168.1.101"
SSH_USERNAME = "pi"
SSH_PASSWORD = "pi"

# RTSP camera mapping {name: (device_path, rtsp_url)}
CAM_PORTS = {
    "Side": ("/dev/video4", f"rtsp://{RASPBERRY_PI_IP}:5001/unicast"),
    "Net": ("/dev/video2", f"rtsp://{RASPBERRY_PI_IP}:5002/unicast"),
    "Jelly": ("/dev/video6", f"rtsp://{RASPBERRY_PI_IP}:5004/unicast"),
    "Gripper": ("/dev/video8", f"rtsp://{RASPBERRY_PI_IP}:5003/unicast"),
    "ZED": ("/dev/video0", f"rtsp://{RASPBERRY_PI_IP}:8554/unicast"),
}

# Pilot page RTSP feed URLs (derived from mapping to avoid duplication)
PILOT_FEEDS = [
    CAM_PORTS["Net"][1],      # Top left
    CAM_PORTS["Side"][1],     # Top right
    CAM_PORTS["Gripper"][1],  # Bot left
    CAM_PORTS["Jelly"][1],    # Bot right
    f"rtsp://{PILOT_STATION_IP}:8554/videofeed",  # Middle (ZED local preference)
]
