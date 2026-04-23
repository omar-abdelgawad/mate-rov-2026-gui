from PyQt5.QtCore import QCoreApplication, QMetaObject, QRect
from PyQt5.QtGui import QIcon, QPixmap, QFont, QFontDatabase
from PyQt5.QtWidgets import QLabel, QPushButton
import os
import subprocess
from stylesheet import Engineer_buttons_st, red_button, back_st
from utils import BG_path, scale

class EngineerUi(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(scale(928), scale(596))

        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "GillSans.ttf")
        id = QFontDatabase.addApplicationFont(font_path)
        families = QFontDatabase.applicationFontFamilies(id)
        
        font = QFont(families[0], 18)
        Afont = QFont(families[0], 14)
        ICCfont = QFont(families[0], 17)

        self.Bg_label = QLabel(Dialog)
        self.Bg_label.setObjectName("Background label")
        self.Bg_label.setGeometry(QRect(scale(-3), scale(-5), scale(945), scale(607)))
        self.Bg_label.setPixmap(QPixmap(BG_path))
        self.Bg_label.setScaledContents(True)

        self.BackButton = QPushButton(Dialog)
        self.BackButton.setObjectName("Back Button")
        self.BackButton.setGeometry(QRect(scale(10), scale(10), scale(61), scale(41)))
        icon = QIcon.fromTheme("go-previous")
        self.BackButton.setIcon(icon)
        self.BackButton.setStyleSheet(back_st + " color: white;")
        self.BackButton.setFont(Afont)

        self.DepthButton = QPushButton(Dialog)
        self.DepthButton.setObjectName("Depth Estimation Button")
        self.DepthButton.setGeometry(QRect(scale(290), scale(100), scale(351), scale(81)))
        self.DepthButton.setStyleSheet(Engineer_buttons_st + " color: white;")
        self.DepthButton.setFont(font)
        self.DepthButton.clicked.connect(self.openDepthEstimation)

        self.IccButton = QPushButton(Dialog)
        self.IccButton.setObjectName("Crab Detection Button")
        self.IccButton.setGeometry(QRect(scale(290), scale(190), scale(351), scale(81)))
        self.IccButton.setStyleSheet(Engineer_buttons_st + " color: white;")
        self.IccButton.setFont(ICCfont)

        self.InformationButton = QPushButton(Dialog)
        self.InformationButton.setObjectName("Information Sheet Button")
        self.InformationButton.setGeometry(QRect(scale(290), scale(280), scale(351), scale(81)))
        self.InformationButton.setStyleSheet(Engineer_buttons_st + " color: white;")
        self.InformationButton.setFont(ICCfont)
        self.InformationButton.clicked.connect(self.openInformationSheet)

        self.EdnaButton = QPushButton(Dialog)
        self.EdnaButton.setObjectName("Edna Button")
        self.EdnaButton.setGeometry(QRect(scale(290), scale(370), scale(351), scale(81)))
        self.EdnaButton.setStyleSheet(Engineer_buttons_st + " color: white;")
        self.EdnaButton.setFont(font)
        self.EdnaButton.clicked.connect(self.openEdna)

        self.setText(Dialog)
        QMetaObject.connectSlotsByName(Dialog)

    def setText(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
        self.Bg_label.setText("")
        self.BackButton.setText(QCoreApplication.translate("Dialog", "Back", None))
        self.DepthButton.setText(QCoreApplication.translate("Dialog", "Depth Estimation", None))
        self.IccButton.setText(QCoreApplication.translate("Dialog", "Crab Detection", None))
        self.InformationButton.setText(QCoreApplication.translate("Dialog", "Information Sheet", None))
        self.EdnaButton.setText(QCoreApplication.translate("Dialog", "eDNA", None))
    
    def openDepthEstimation(self):
        subprocess.run("cd ../length-measurement/build && ./zed_open_capture_depth_tune_stereo", shell=True, check=True)

    def openInformationSheet(self):
        pass

    def openEdna(self):
        pass