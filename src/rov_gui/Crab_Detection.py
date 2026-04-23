import os
import cv2

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from crab_detection.crab_detector import CrabDetector # from pkg 
from stylesheet import back_st, selection_st
from utils import BG_path, scale

OUTPUT_DIR = "output"


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


class DModelthread(QThread):
    ImageSignal = pyqtSignal(QImage)

    def __init__(self, camera_idx=0):
        super().__init__()
        self.camera_idx = camera_idx
        self.DetectionModel = CrabDetector(OUTPUT_DIR)

    def set_camera(self, camera_idx):
        self.camera_idx = camera_idx

    def run(self):
        cap = cv2.VideoCapture(self.camera_idx)

        if not cap.isOpened():
            print(f"Camera {self.camera_idx} not opened")
            return

        while not self.isInterruptionRequested():
            ret, frame = cap.read()
            if not ret:
                continue

            result, _ = self.DetectionModel.detect(frame)

            orig_h, orig_w = frame.shape[:2]
            result_h, result_w = result.shape[:2]

            if result_w == result_h and orig_w > orig_h:
                result = cv2.resize(result, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

            rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

            rgb = rgb.copy()  

            h, w, ch = rgb.shape
            bytes_per_line = ch * w

            qt_img = QImage(
                rgb.data,
                w,
                h,
                bytes_per_line,
                QImage.Format_RGB888
            ).copy()   

            self.ImageSignal.emit(qt_img)

        cap.release()


class CrabDetectionUi(object):

    def setupUI(self, Dialog, parent=None, start_thread=False):
        self.parent = parent
        self.Dialog = Dialog
        self.currentFrame = None
        self.thread = None
        self.imageUpdater = None
        self.start_on_init = start_thread

        Dialog.setObjectName("CrabDetectionDialog")
        Dialog.resize(scale(928), scale(596))
        Dialog.setMinimumSize(scale(800), scale(500))
        Dialog.setMaximumSize(scale(1200), scale(800))

        bg_path = BG_path.replace("\\", "/")
        Dialog.setStyleSheet(f"""
            QDialog#CrabDetectionDialog {{
                background-image: url("{bg_path}");
                background-repeat: no-repeat;
                background-position: center;
                background-size: cover;
            }}
        """)

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

        self.backBtn.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed
        )
        self.backBtn.setMinimumSize(scale(110), scale(40))

        top_bar_layout.addWidget(self.backBtn)

        camera_label = QLabel("Camera:")
        camera_label.setStyleSheet("color: white; font-weight: bold;")
        top_bar_layout.addWidget(camera_label)

        self.cameraCombo = QComboBox()
        self.cameraCombo.addItem("Z Camera", 0)
        self.cameraCombo.addItem("CAM1", 1)
        self.cameraCombo.addItem("CAM2", 2)
        self.cameraCombo.addItem("CAM3", 3)
        self.cameraCombo.addItem("CAM4", 4)
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

        self.freezeAndSaveBtn = QPushButton("Freeze And Save")
        self.freezeAndSaveBtn.setMinimumHeight(scale(50))
        self.freezeAndSaveBtn.setMinimumWidth(scale(150))
        self.freezeAndSaveBtn.clicked.connect(self.display_save_frame)

        bottom_bar_layout.addWidget(self.freezeAndSaveBtn)
        bottom_bar_layout.addStretch(1)

        root_layout.addLayout(bottom_bar_layout, stretch=0)

        Dialog.setLayout(root_layout)

        if self.start_on_init:
            self.start_thread()

    def start_thread(self):
        if self.thread is not None and self.thread.isRunning():
            print("Thread already running")
            return

        print("Starting crab detection thread")
        self.imageUpdater = ImageUpdater(self)
        self.thread = DModelthread(camera_idx=0)
        self.thread.ImageSignal.connect(self.imageUpdater.handleImage)
        self.thread.start()

    def on_camera_changed(self, index):
        if self.thread is None or not self.thread.isRunning():
            return

        camera_idx = self.cameraCombo.itemData(index)
        print(f"Switching to camera: {camera_idx}")

        self.thread.requestInterruption()
        self.thread.wait()

        self.imageUpdater = ImageUpdater(self)
        self.thread = DModelthread(camera_idx=camera_idx)
        self.thread.ImageSignal.connect(self.imageUpdater.handleImage)
        self.thread.start()

    def stop(self):
        if self.thread is not None and self.thread.isRunning():
            print("Stopping crab detection thread")
            self.thread.requestInterruption()
            self.thread.wait()
            self.thread = None

    def display_save_frame(self):
        if self.currentFrame is None:
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")
        path = os.path.join(OUTPUT_DIR, f"frame_{timestamp}.png")

        self.currentFrame.save(path)
        print(f"Saved: {path}")

        dlg = FreezeDialog(self.currentFrame)
        dlg.exec_()


class FreezeDialog(QDialog):
    def __init__(self, image):
        super().__init__()

        self.setWindowTitle("Frozen Frame")
        dialog_width = scale(700)
        dialog_height = scale(500)
        
        self.resize(dialog_width, dialog_height)
        self.setMaximumSize(scale(1000), scale(750))

        screen = QApplication.primaryScreen().geometry()

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        image = image.convertToFormat(QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(image)
        
        target_width = dialog_width - scale(40)
        target_height = dialog_height - scale(40)
        
        scaled_pixmap = pixmap.scaled(
            target_width, 
            target_height, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        label.setPixmap(scaled_pixmap)

        layout = QVBoxLayout()
        layout.setContentsMargins(scale(10), scale(10), scale(10), scale(10))
        layout.addWidget(label, alignment=Qt.AlignCenter)

        self.setLayout(layout)

        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )