import cv2
import sys

ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.36"
port = sys.argv[2] if len(sys.argv) > 2 else "1935"

url = f"rtsp://admin:admin@{ip}:{port}"

cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("Failed to open stream")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("RTSP Stream", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
