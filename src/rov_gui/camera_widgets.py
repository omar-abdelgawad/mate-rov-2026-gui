import cv2
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QSizePolicy
import time


class CameraFeed(QThread):
    frame_signal = pyqtSignal(QImage)

    def __init__(self, url, width=640, height=480):
        super().__init__()
        self.url = url
        self.width = width
        self.height = height
        self.running = True

    def run(self):
        # Improved GStreamer pipeline for stability with tight timeouts (2 seconds max)
        pipeline = (
            f"rtspsrc location={self.url} latency=0 timeout=2000000 tcp-timeout=2000000 buffer-mode=auto ! "
            "decodebin ! videoconvert ! appsink max-buffers=1 drop=True"
        )

        while self.running:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

            if not cap.isOpened():
                # Emit a placeholder or retry after a delay
                for _ in range(20): # Sleep in small increments to be responsive to self.running = False
                    if not self.running: return
                    self.msleep(100)
                continue

            while self.running and cap.isOpened():
                ret, frame = cap.read()

                if not ret:
                    cap.release()
                    cv2.destroyAllWindows()
                    for _ in range(10): # Responsive sleep
                        if not self.running: return
                        self.msleep(100)
                    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                    continue

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
            
            # Responsive sleep before retry
            for _ in range(10):
                if not self.running: return
                self.msleep(100)

    def stop(self):
        self.running = False
        self.wait(1000) # Wait at most 1 second for thread to finish so we don't freeze GUI


def _update_label(label, image):
    """Scale pixmap to fit the label while preserving aspect ratio."""
    pixmap = QPixmap.fromImage(image)
    scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    label.setPixmap(scaled)


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

        # Layout for 3 cameras:
        # 0: ZED stereo (Top, spanning full width)
        # 1: Side       (Bottom left)
        # 2: Net        (Bottom right)

        # Grid positions: (row, col, rowspan, colspan)
        positions = [
            (0, 0, 1, 2),  # ZED: top row, spans both columns
            (1, 0),         # Side: bottom left
            (1, 1),         # Net: bottom right
        ]

        # ZED dominates the top; bottom cameras are smaller
        self.layout.setRowStretch(0, 7)
        self.layout.setRowStretch(1, 3)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)

        for i, url in enumerate(self.urls):
            label = QLabel("Loading Stream...")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: white; border: 1px solid #333;")
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.setMinimumSize(1, 1)

            self.layout.addWidget(label, *positions[i])

            if i == 0:  # ZED (Top, large)
                feed = CameraFeed(url, width=1280, height=720)
            else:  # Side / Net (Bottom, smaller)
                feed = CameraFeed(url, width=640, height=360)

            feed.frame_signal.connect(
                lambda img, lbl=label: _update_label(lbl, img)
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
