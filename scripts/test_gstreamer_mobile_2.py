import cv2

gst_pipeline = (
    "rtspsrc location=rtsp://admin:admin@192.168.1.36:1935 latency=0 ! "
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
