import cv2
import sys

ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.36"
port = sys.argv[2] if len(sys.argv) > 2 else "1935"

gst_pipeline = (
    f"rtspsrc location=rtsp://admin:admin@{ip}:{port} latency=0 ! "
    "rtph264depay ! decodebin ! videoconvert ! appsink"
)

cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Failed to open stream with GStreamer")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame grab failed")
        break

    cv2.imshow("GStreamer RTSP", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
