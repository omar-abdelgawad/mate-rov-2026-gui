import argparse

# Network
RASPBERRY_PI_IP = "192.168.0.101"
SSH_USERNAME = "pi"
SSH_PASSWORD = "pi"

# RTSP camera mapping {name: (device_path, rtsp_url)}
CAM_PORTS = {
    "Side": ("/dev/video4", f"rtsp://{RASPBERRY_PI_IP}:5000/unicast"),
    "Net": ("/dev/video2", f"rtsp://{RASPBERRY_PI_IP}:5001/unicast"),
    "ZED": ("/dev/video0", f"rtsp://{RASPBERRY_PI_IP}:8554/zed"),
}

# CLI Override logic
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--mobile-rtsp", nargs="+", help="Override RTSP feeds with mobile stream(s)")
args, _ = parser.parse_known_args()

if args.mobile_rtsp:
    urls = args.mobile_rtsp
    ordered_keys = ["Side", "Net", "ZED"]
    for i, key in enumerate(ordered_keys):
        if i < len(urls):
            CAM_PORTS[key] = (CAM_PORTS[key][0], urls[i])
        else:
            # Leave remaining streams empty so they show "Loading Stream..." and fail predictably
            CAM_PORTS[key] = (CAM_PORTS[key][0], "rtsp://invalid.stream.empty")

# Pilot page RTSP feed URLs (derived from mapping to avoid duplication)
PILOT_FEEDS = [
    CAM_PORTS["ZED"][1],   # Top (ZED stereo)
    CAM_PORTS["Side"][1],  # Bottom left
    CAM_PORTS["Net"][1],   # Bottom right
]
