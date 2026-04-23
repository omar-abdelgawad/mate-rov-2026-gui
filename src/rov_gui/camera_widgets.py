import cv2
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel


class CameraFeed(QThread):
    frame_signal = pyqtSignal(QImage)

    def __init__(self, url, width=640, height=480):
        super().__init__()
        self.url = url
        self.width = width
        self.height = height
        self.running = True

    def run(self):
        # Improved GStreamer pipeline for stability
        pipeline = (
            f"rtspsrc location={self.url} latency=0 buffer-mode=auto ! "
            "decodebin ! videoconvert ! appsink max-buffers=1 drop=True"
        )

        while self.running:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

            if not cap.isOpened():
                # Emit a placeholder or retry after a delay
                self.msleep(2000)
                continue

            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Resize and convert to QImage
                frame = cv2.resize(frame, (self.width, self.height))
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(
                    rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
                ).copy()

                self.frame_signal.emit(qt_image)

            cap.release()
            self.msleep(1000)

    def stop(self):
        self.running = False
        self.wait()


class CameraGrid(QWidget):
    def __init__(self, urls):
        super().__init__()
        self.urls = urls
        self.feeds = []
        self.labels = []

        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.setStyleSheet("background-color: black;")

        # Custom layout for 5-6 cameras
        # 0: Net (Top Left)
        # 1: Side (Top Right)
        # 2: Gripper (Bottom Left)
        # 3: Jelly (Bottom Right)
        # 4: ZED (Middle Large)

        # Grid positions for a balanced look
        positions = [
            (0, 0),
            (0, 2),  # Top corners
            (2, 0),
            (2, 2),  # Bottom corners
            (0, 1, 3, 1),  # Center (Spanning 3 rows)
        ]

        for i, url in enumerate(self.urls):
            label = QLabel("Loading Stream...")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: white; border: 1px solid #333;")

            if i == 4:  # ZED (Center)
                self.layout.addWidget(label, *positions[i])
                feed = CameraFeed(url, width=800, height=600)
            else:
                self.layout.addWidget(label, *positions[i])
                feed = CameraFeed(url, width=480, height=270)

            feed.frame_signal.connect(
                lambda img, lbl=label: lbl.setPixmap(QPixmap.fromImage(img))
            )
            self.feeds.append(feed)
            self.labels.append(label)

    def start(self):
        for feed in self.feeds:
            feed.start()

    def stop(self):
        for feed in self.feeds:
            feed.stop()
        self.close()

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)
