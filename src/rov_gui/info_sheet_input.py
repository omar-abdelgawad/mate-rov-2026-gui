from PyQt5.QtCore import QRect, QMetaObject, QCoreApplication
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QDialog,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
)
import os

from stylesheet import Engineer_buttons_st, back_st
from utils import BG_path, scale

# from information_sheet_problem import run_analysis
run_analysis = None


class infoSheetInputUi(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(scale(928), scale(596))

        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "GillSans.ttf")
        id = QFontDatabase.addApplicationFont(font_path)
        families = QFontDatabase.applicationFontFamilies(id)

        title_font = QFont(families[0], 18)
        label_font = QFont(families[0], 14)

        # Background
        self.bg_label = QLabel(Dialog)
        self.bg_label.setGeometry(QRect(scale(-3), scale(-5), scale(945), scale(607)))
        self.bg_label.setPixmap(QPixmap(BG_path))
        self.bg_label.setScaledContents(True)

        # Back button
        self.backBtn = QPushButton(Dialog)
        self.backBtn.setGeometry(QRect(scale(10), scale(10), scale(61), scale(41)))
        self.backBtn.setStyleSheet(back_st + " color: white;")
        self.backBtn.setFont(label_font)
        self.backBtn.setText("Back")

        # ===== Longitude =====
        self.long_label = QLabel("Longitude (D° M' S\")", Dialog)
        self.long_label.setGeometry(QRect(scale(100), scale(80), scale(250), scale(30)))
        self.long_label.setFont(label_font)

        self.long_deg = QLineEdit(Dialog)
        self.long_deg.setPlaceholderText("Deg")
        self.long_deg.setGeometry(QRect(scale(100), scale(120), scale(80), scale(40)))

        self.long_min = QLineEdit(Dialog)
        self.long_min.setPlaceholderText("Min")
        self.long_min.setGeometry(QRect(scale(190), scale(120), scale(80), scale(40)))

        self.long_sec = QLineEdit(Dialog)
        self.long_sec.setPlaceholderText("Sec")
        self.long_sec.setGeometry(QRect(scale(280), scale(120), scale(80), scale(40)))

        # ===== Latitude =====
        self.lat_label = QLabel("Latitude (D° M' S\")", Dialog)
        self.lat_label.setGeometry(QRect(scale(100), scale(180), scale(250), scale(30)))
        self.lat_label.setFont(label_font)

        self.lat_deg = QLineEdit(Dialog)
        self.lat_deg.setPlaceholderText("Deg")
        self.lat_deg.setGeometry(QRect(scale(100), scale(220), scale(80), scale(40)))

        self.lat_min = QLineEdit(Dialog)
        self.lat_min.setPlaceholderText("Min")
        self.lat_min.setGeometry(QRect(scale(190), scale(220), scale(80), scale(40)))

        self.lat_sec = QLineEdit(Dialog)
        self.lat_sec.setPlaceholderText("Sec")
        self.lat_sec.setGeometry(QRect(scale(280), scale(220), scale(80), scale(40)))

        # ===== Keel Depth =====
        self.depth_label = QLabel("Keel Depth", Dialog)
        self.depth_label.setGeometry(
            QRect(scale(100), scale(300), scale(200), scale(30))
        )
        self.depth_label.setFont(label_font)

        self.depth_input = QLineEdit(Dialog)
        self.depth_input.setPlaceholderText("Meters")
        self.depth_input.setGeometry(
            QRect(scale(100), scale(340), scale(150), scale(40))
        )

        # ===== Heading =====
        self.heading_label = QLabel("Heading (°)", Dialog)
        self.heading_label.setGeometry(
            QRect(scale(100), scale(400), scale(200), scale(30))
        )
        self.heading_label.setFont(label_font)

        self.heading_input = QLineEdit(Dialog)
        self.heading_input.setPlaceholderText("Degrees")
        self.heading_input.setGeometry(
            QRect(scale(100), scale(440), scale(150), scale(40))
        )

        # ===== Submit Button =====
        self.submitBtn = QPushButton("Save", Dialog)
        self.submitBtn.setGeometry(QRect(scale(600), scale(450), scale(200), scale(60)))
        self.submitBtn.setStyleSheet(Engineer_buttons_st + " color: white;")
        self.submitBtn.setFont(title_font)

        self.setText(Dialog)
        QMetaObject.connectSlotsByName(Dialog)

        # Connect submit
        self.submitBtn.clicked.connect(self.collect_values)

    def setText(self, Dialog):
        Dialog.setWindowTitle(
            QCoreApplication.translate("Dialog", "Info Sheet Input", None)
        )

    def dms_to_float(self, deg, minute, sec):
        value = float(deg) + float(minute) / 60 + float(sec) / 3600
        return round(value, 4)

    def collect_values(self):
        try:
            self.longitude = self.dms_to_float(
                self.long_deg.text(), self.long_min.text(), self.long_sec.text()
            )

            self.latitude = self.dms_to_float(
                self.lat_deg.text(), self.lat_min.text(), self.lat_sec.text()
            )

            self.keel_depth = round(float(self.depth_input.text()), 4)
            self.heading = round(float(self.heading_input.text()), 4)

            # 🚀 CALL ANALYSIS
            result = run_analysis(
                latitude=self.latitude,
                longitude=self.longitude,
                heading=self.heading,
                keel_depth=self.keel_depth,
            )

            # 🚀 SHOW RESULTS
            self.show_results_dialog(result)

        except ValueError:
            print("Invalid input!")

    def show_results_dialog(self, result):
        dialog = QDialog()
        dialog.setWindowTitle("Analysis Results")
        dialog.resize(500, 300)

        layout = QVBoxLayout()

        table = QTableWidget()
        table.setRowCount(len(result.results))
        table.setColumnCount(3)

        table.setHorizontalHeaderLabels(["Platform", "Surface Threat", "Subsea Threat"])

        for row, r in enumerate(result.results):
            table.setItem(row, 0, QTableWidgetItem(r.platform.name))
            table.setItem(row, 1, QTableWidgetItem(r.surface_threat.value))
            table.setItem(row, 2, QTableWidgetItem(r.subsea_threat.value))
        for num, r in enumerate(result.results):
            print(f"the platform:  {r.platform.name}")
            print(f"surface_threat: {r.surface_threat.value}")
            print(f"subsea threat: {r.subsea_threat.value}")
        layout.addWidget(table)
        dialog.setLayout(layout)

        dialog.exec_()
