import os
import cv2
import numpy as np

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QThread, Qt, QDateTime
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QSizePolicy,
    QDialog,
    QApplication,
)

from ultralytics import YOLO

# This stops Ultralytics from checking for updates or reaching out to the web
os.environ["ULTRALYTICS_OFFLINE"] = "True"
# This stops the heavy logging that can sometimes clutter the thread output
os.environ["YOLO_VERBOSE"] = "False"


from stylesheet import back_st, selection_st
from utils import BG_path, ResponsiveBackground, scale
from config import CAM_PORTS

OUTPUT_DIR = "crab_detection_output"

class CrabDetector:
    def __init__(self, output_dir="./output"):
        # Setup paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "best_v4_all4.onnx")
        
        # Load the ONNX model. 
        # Note: We do NOT use .to('cpu') here as it is not supported for ONNX.
        self.model = YOLO(model_path, task="detect")

        self.TARGET_CLASSES = ["green-crab", "rock-crab", "jonah-crab"]
        self.CONF_THRESHOLD = 0.5

        self.CLASS_COLORS = {
            "green-crab": (0, 255, 0),     # Green
            "rock-crab": (255, 0, 0),      # Blue (BGR)
            "jonah-crab": (0, 0, 255),     # Red (BGR)
        }

        self.totalCount = 0
        self.OUTPUT_DIR = output_dir

        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def detect(self, frame):
        # We pass device='cpu' here to ensure it uses the onnxruntime CPU engine.
        # This prevents the AutoUpdate 'onnxruntime-gpu' crash.
        results = self.model.predict(frame, device='cpu', verbose=False)

        stats = {cls: 0 for cls in self.TARGET_CLASSES}

        for result in results:
            if result.boxes is None:
                continue
                
            for box, cls, conf in zip(
                result.boxes.xyxy,
                result.boxes.cls,
                result.boxes.conf,
            ):
                # Ensure the index is an integer for the names dictionary
                class_id = int(cls)
                class_name = self.model.names[class_id]

                if conf < self.CONF_THRESHOLD or class_name not in self.TARGET_CLASSES:
                    continue

                self.totalCount += 1
                stats[class_name] += 1

                # Coordinates for the bounding box
                x1, y1, x2, y2 = map(int, box)

                color = self.CLASS_COLORS.get(class_name, (0, 255, 255))
                label = f"{class_name} {conf:.2f}"

                # Draw the rectangle and label on the frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

        # Overlay the count for the most important class (Green Crab)
        cv2.putText(
            frame,
            f"Green Crabs: {stats['green-crab']}",
            (20, frame.shape[0] - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3,
        )

        return frame, self.totalCount


class ImageUpdater(QObject):
    def __init__(self, ui_ref):
        super().__init__()
        self.ui = ui_ref

    @pyqtSlot(QImage)
    def handleImage(self, image):
        self.ui.currentFrame = image

        label_width = self.ui.label.width()
        label_height = self.ui.label.height()

        if label_width <= 1 or label_height <= 1:
            return

        scaledImg = image.scaled(
            label_width,
            label_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.ui.label.setPixmap(QPixmap.fromImage(scaledImg))


class VideoFeedThread(QThread):
    ImageSignal = pyqtSignal(QImage)

    def __init__(self, stream_url=None):
        super().__init__()
        self.stream_url = stream_url

    def set_camera(self, stream_url):
        self.stream_url = stream_url

    def run(self):
        pipeline = (
            f"rtspsrc location={self.stream_url} latency=0 timeout=2000000 tcp-timeout=2000000 buffer-mode=auto ! "
            "decodebin ! videoconvert ! appsink max-buffers=1 drop=True"
        )
        
        while not self.isInterruptionRequested():
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            
            if not cap.isOpened():
                # Emit a placeholder or retry after a delay
                for _ in range(20): # Sleep in small increments
                    if self.isInterruptionRequested(): return
                    self.msleep(100)
                continue
                
            while not self.isInterruptionRequested() and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.release()
                    cv2.destroyAllWindows()
                    for _ in range(10): # Responsive sleep
                        if self.isInterruptionRequested(): return
                        self.msleep(100)
                    break # Break inner loop to restart capture
    
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb = rgb.copy()
    
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
    
                self.ImageSignal.emit(qt_img)
            
            if cap.isOpened():
                cap.release()


class FrozenCrabDetectionDialog(QDialog):
    def __init__(self, image, detector: CrabDetector):
        super().__init__()
        self.detector = detector
        self.original_qimage = image.copy()

        self.setWindowTitle("Frozen Frame - Crab Detection")
        self.dialog_width = scale(800)
        self.dialog_height = scale(600)
        self.resize(self.dialog_width, self.dialog_height)
        self.setMaximumSize(scale(1000), scale(750))

        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.update_image_display(self.original_qimage)

        self.detect_btn = QPushButton("Detect")
        self.detect_btn.setMinimumHeight(scale(40))
        self.detect_btn.clicked.connect(self.run_detection)

        layout = QVBoxLayout()
        layout.setContentsMargins(scale(10), scale(10), scale(10), scale(10))
        layout.addWidget(self.label, alignment=Qt.AlignCenter, stretch=1)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.detect_btn)
        btn_layout.addStretch(1)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_image_display(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        target_width = self.dialog_width - scale(40)
        target_height = self.dialog_height - scale(80)
        scaled_pixmap = pixmap.scaled(
            target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(scaled_pixmap)

    def run_detection(self):
        # Convert QImage to cv2 format (BGR)
        qimg = self.original_qimage.convertToFormat(QImage.Format_RGB888)
        width = qimg.width()
        height = qimg.height()
        
        ptr = qimg.bits()
        ptr.setsize(height * width * 3)
        arr = np.array(ptr).reshape((height, width, 3))
        cv_img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        # Run detection
        result_img, count = self.detector.detect(cv_img)

        # Save result
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")
        filename = f"frozen_detection_{timestamp}.png"
        save_path = os.path.join(self.detector.OUTPUT_DIR, filename)
        cv2.imwrite(save_path, result_img)
        print(f"Saved detection to: {save_path}")

        # Convert back to QImage for display
        rgb = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        res_qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

        self.update_image_display(res_qimg)
        self.detect_btn.setText(f"Detected: {count} Total (Saved)")
        self.detect_btn.setEnabled(False) # Disable after detection


class FrozenCrabDetectionUi(object):
    def setupUI(self, Dialog, parent=None, start_thread=False):
        self.parent = parent
        self.Dialog = Dialog
        self.currentFrame = None
        self.thread = None
        self.imageUpdater = None
        self.start_on_init = start_thread
        self.detector = CrabDetector(OUTPUT_DIR)

        Dialog.setObjectName("FrozenCrabDetectionDialog")
        Dialog.resize(scale(928), scale(596))
        Dialog.setMinimumSize(scale(800), scale(500))
        Dialog.setMaximumSize(scale(1200), scale(800))

        self._bg_label = QLabel(Dialog)
        self._bg_label.setObjectName("FrozenCrabDetectionBackground")
        self._responsive_bg = ResponsiveBackground(Dialog, self._bg_label, BG_path)

        root_layout = QVBoxLayout(Dialog)
        root_layout.setContentsMargins(scale(20), scale(20), scale(20), scale(20))
        root_layout.setSpacing(scale(12))

        top_bar_layout = QHBoxLayout()

        self.backBtn = QPushButton(Dialog)
        self.backBtn.setObjectName("Back Button")

        icon = QIcon.fromTheme("go-previous")
        self.backBtn.setIcon(icon)
        self.backBtn.setStyleSheet(back_st + " color: white;")
        self.backBtn.setText("Back")
        self.backBtn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.backBtn.setMinimumSize(scale(110), scale(40))
        top_bar_layout.addWidget(self.backBtn)

        camera_label = QLabel("Camera:")
        camera_label.setStyleSheet("color: white; font-weight: bold;")
        top_bar_layout.addWidget(camera_label)

        self.cameraCombo = QComboBox()
        for name, port_info in CAM_PORTS.items():
            self.cameraCombo.addItem(name, port_info[1])
        self.cameraCombo.setStyleSheet(selection_st)
        self.cameraCombo.setMaximumWidth(scale(150))
        self.cameraCombo.currentIndexChanged.connect(self.on_camera_changed)
        top_bar_layout.addWidget(self.cameraCombo)

        top_bar_layout.addStretch(1)
        root_layout.addLayout(top_bar_layout, stretch=0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setStyleSheet("background: rgba(0,0,0,0);")
        self.label.setMinimumHeight(scale(280))
        self.label.setMinimumWidth(scale(500))
        root_layout.addWidget(self.label, stretch=1)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.addStretch(1)

        self.freezeBtn = QPushButton("Freeze Frame")
        self.freezeBtn.setMinimumHeight(scale(50))
        self.freezeBtn.setMinimumWidth(scale(150))
        self.freezeBtn.clicked.connect(self.display_freeze_dialog)
        bottom_bar_layout.addWidget(self.freezeBtn)

        bottom_bar_layout.addStretch(1)
        root_layout.addLayout(bottom_bar_layout, stretch=0)

        Dialog.setLayout(root_layout)

        if self.start_on_init:
            self.start_thread()

    def start_thread(self):
        if self.thread is not None and self.thread.isRunning():
            print("Thread already running")
            return

        print("Starting frozen crab feed thread")
        initial_url = self.cameraCombo.itemData(0)
        self.imageUpdater = ImageUpdater(self)
        self.thread = VideoFeedThread(stream_url=initial_url)
        self.thread.ImageSignal.connect(self.imageUpdater.handleImage)
        self.thread.start()

    def on_camera_changed(self, index):
        if self.thread is None or not self.thread.isRunning():
            return

        stream_url = self.cameraCombo.itemData(index)
        print(f"Switching to camera: {stream_url}")

        self.thread.requestInterruption()
        self.thread.wait()

        self.imageUpdater = ImageUpdater(self)
        self.thread = VideoFeedThread(stream_url=stream_url)
        self.thread.ImageSignal.connect(self.imageUpdater.handleImage)
        self.thread.start()

    def stop(self):
        if self.thread is not None and self.thread.isRunning():
            print("Stopping frozen crab feed thread")
            self.thread.requestInterruption()
            self.thread.wait()
            self.thread = None

    def display_freeze_dialog(self):
        if self.currentFrame is None:
            return

        dlg = FrozenCrabDetectionDialog(self.currentFrame, self.detector)
        dlg.exec_()
