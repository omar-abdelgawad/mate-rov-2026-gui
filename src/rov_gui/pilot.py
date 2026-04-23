from PyQt5.QtCore import QCoreApplication, QRect, QMetaObject
from PyQt5.QtGui import QIcon, QPixmap, QFont, QFontDatabase
from PyQt5.QtWidgets import QLabel, QPushButton
from stylesheet import Engineer_buttons_st, back_st
import os
from camera_widgets import CameraGrid
from utils import BG_path, scale
from config import PILOT_FEEDS


class PilotUi(object):
    def setupUi(self, Dialog):
        # Loading font
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "GillSans.ttf")
        id = QFontDatabase.addApplicationFont(font_path)
        if id == -1:
            print("Failed to load font!")

        families = QFontDatabase.applicationFontFamilies(id)
        # Scaled font sizes
        font = QFont(families[0], 22)
        Afont = QFont(families[0], 11)

        Dialog.setObjectName("Dialog")
        Dialog.resize(scale(928), scale(596))  # Scaled window size

        # Background
        self.Bg_label = QLabel(Dialog)
        self.Bg_label.setObjectName("Background")
        self.Bg_label.setGeometry(QRect(scale(-3), scale(-5), scale(945), scale(607)))
        self.Bg_label.setPixmap(QPixmap(BG_path))
        self.Bg_label.setScaledContents(True)

        # Back button
        self.BackButton = QPushButton(Dialog)
        self.BackButton.setObjectName("Back button")
        self.BackButton.setGeometry(QRect(scale(10), scale(10), scale(61), scale(41)))
        icon = QIcon()
        icon = QIcon.fromTheme("go-previous")
        self.BackButton.setIcon(icon)
        self.BackButton.setStyleSheet(back_st)
        self.BackButton.setFont(Afont)

        # Camera system button
        self.CamButton = QPushButton(Dialog)
        self.CamButton.setObjectName("Launching the Camera system button")
        self.CamButton.setGeometry(QRect(scale(290), scale(240), scale(351), scale(81)))
        self.CamButton.setStyleSheet(Engineer_buttons_st)
        self.CamButton.setFont(font)

        self.camera_grid = None
        self.CamButton.clicked.connect(self.launch_camera_system)
        self.setText(Dialog)
        QMetaObject.connectSlotsByName(Dialog)

    def launch_camera_system(self):
        if self.camera_grid is None:
            self.camera_grid = CameraGrid(PILOT_FEEDS)
            self.camera_grid.setWindowTitle("ROV Camera System")
            self.camera_grid.resize(scale(1280), scale(720))

        self.camera_grid.show()
        self.camera_grid.start()

    def setText(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
        self.Bg_label.setText("")
        self.BackButton.setText(QCoreApplication.translate("Dialog", "Back", None))
        self.CamButton.setText(
            QCoreApplication.translate("Dialog", "Launch Camera System", None)
        )
