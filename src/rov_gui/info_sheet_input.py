from PyQt5.QtCore import QRect, QMetaObject, QCoreApplication, Qt
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase, QColor
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QDialog,
    QAbstractItemView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QHeaderView,
)
import os

from stylesheet import Engineer_buttons_st, back_st, selection_st
from utils import BG_path, ResponsiveBackground, scale

from information_sheet_problem import analyze_iceberg, ThreatLevel


class infoSheetInputUi(object):
    def _log_analysis_result(
        self,
        *,
        lat_deg: int,
        lat_min: int,
        lat_sec: int,
        lat_hem: str,
        lon_deg: int,
        lon_min: int,
        lon_sec: int,
        lon_hem: str,
        heading: float,
        keel_depth: float,
        result,
    ) -> None:
        print("\n===== Iceberg API Result =====")
        print(
            "Input:",
            f"lat={lat_deg} {lat_min} {lat_sec} {lat_hem},",
            f"lon={lon_deg} {lon_min} {lon_sec} {lon_hem},",
            f"heading={heading}, keel_depth={keel_depth}",
        )
        for item in result.results:
            surface = getattr(item.surface_threat, "value", item.surface_threat)
            subsea = getattr(item.subsea_threat, "value", item.subsea_threat)
            print(
                f"{item.platform.name}: "
                f"surface={str(surface).upper()} | subsea={str(subsea).upper()}"
            )
        print("==============================\n")

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
        self.bg_label.setPixmap(QPixmap(BG_path))
        self._responsive_bg = ResponsiveBackground(Dialog, self.bg_label, BG_path)

        # Back button
        self.backBtn = QPushButton(Dialog)
        self.backBtn.setGeometry(QRect(scale(10), scale(10), scale(61), scale(41)))
        self.backBtn.setStyleSheet(back_st + " color: white;")
        self.backBtn.setFont(label_font)
        self.backBtn.setText("Back")

        # ===== Latitude =====
        self.lat_label = QLabel("Latitude (D° M' S\") (N/S)", Dialog)
        self.lat_label.setGeometry(QRect(scale(100), scale(80), scale(250), scale(30)))
        self.lat_label.setFont(label_font)

        self.lat_deg = QLineEdit(Dialog)
        self.lat_deg.setPlaceholderText("Deg")
        self.lat_deg.setGeometry(QRect(scale(100), scale(120), scale(80), scale(40)))

        self.lat_min = QLineEdit(Dialog)
        self.lat_min.setPlaceholderText("Min")
        self.lat_min.setGeometry(QRect(scale(190), scale(120), scale(80), scale(40)))

        self.lat_sec = QLineEdit(Dialog)
        self.lat_sec.setPlaceholderText("Sec")
        self.lat_sec.setGeometry(QRect(scale(280), scale(120), scale(80), scale(40)))

        self.lat_dir = QComboBox(Dialog)
        self.lat_dir.setObjectName("Latitude Direction")
        self.lat_dir.addItems(["N", "S"])
        self.lat_dir.setCurrentText("N")
        self.lat_dir.setStyleSheet(selection_st)
        self.lat_dir.setGeometry(QRect(scale(370), scale(120), scale(60), scale(40)))

        # ===== Longitude =====
        self.long_label = QLabel("Longitude (D° M' S\") (E/W)", Dialog)
        self.long_label.setGeometry(QRect(scale(100), scale(180), scale(250), scale(30)))
        self.long_label.setFont(label_font)

        self.long_deg = QLineEdit(Dialog)
        self.long_deg.setPlaceholderText("Deg")
        self.long_deg.setGeometry(QRect(scale(100), scale(220), scale(80), scale(40)))

        self.long_min = QLineEdit(Dialog)
        self.long_min.setPlaceholderText("Min")
        self.long_min.setGeometry(QRect(scale(190), scale(220), scale(80), scale(40)))

        self.long_sec = QLineEdit(Dialog)
        self.long_sec.setPlaceholderText("Sec")
        self.long_sec.setGeometry(QRect(scale(280), scale(220), scale(80), scale(40)))

        self.long_dir = QComboBox(Dialog)
        self.long_dir.setObjectName("Longitude Direction")
        # Match analyze_iceberg API + official examples: longitude uses E/W.
        self.long_dir.addItems(["E", "W"])
        self.long_dir.setCurrentText("W")
        self.long_dir.setStyleSheet(selection_st)
        self.long_dir.setGeometry(QRect(scale(370), scale(220), scale(60), scale(40)))

        # ===== Heading =====
        self.heading_label = QLabel("Heading (°)", Dialog)
        self.heading_label.setGeometry(
            QRect(scale(100), scale(300), scale(200), scale(30))
        )
        self.heading_label.setFont(label_font)

        self.heading_input = QLineEdit(Dialog)
        self.heading_input.setPlaceholderText("Degrees")
        self.heading_input.setGeometry(
            QRect(scale(100), scale(340), scale(150), scale(40))
        )

        # ===== Keel Depth =====
        self.depth_label = QLabel("Keel Depth", Dialog)
        self.depth_label.setGeometry(
            QRect(scale(100), scale(400), scale(200), scale(30))
        )
        self.depth_label.setFont(label_font)

        self.depth_input = QLineEdit(Dialog)
        self.depth_input.setPlaceholderText("Meters")
        self.depth_input.setGeometry(
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

    def get_longitude_direction(self) -> str:
        return self.long_dir.currentText()

    def get_latitude_direction(self) -> str:
        return self.lat_dir.currentText()

    def collect_values(self):
        try:
            self.keel_depth = round(float(self.depth_input.text()), 4)
            self.heading = round(float(self.heading_input.text()), 4)

            lat_deg = int(self.lat_deg.text())
            lat_min = int(self.lat_min.text())
            lat_sec = int(self.lat_sec.text())
            lat_hem = self.get_latitude_direction()

            lon_deg = int(self.long_deg.text())
            lon_min = int(self.long_min.text())
            lon_sec = int(self.long_sec.text())
            lon_hem = self.get_longitude_direction()

            # CALL ANALYSIS (library API uses DMS + hemisphere)
            result = analyze_iceberg(
                lat_deg,
                lat_min,
                lat_sec,
                lat_hem,
                lon_deg,
                lon_min,
                lon_sec,
                lon_hem,
                self.heading,
                self.keel_depth,
            )

            self._log_analysis_result(
                lat_deg=lat_deg,
                lat_min=lat_min,
                lat_sec=lat_sec,
                lat_hem=lat_hem,
                lon_deg=lon_deg,
                lon_min=lon_min,
                lon_sec=lon_sec,
                lon_hem=lon_hem,
                heading=self.heading,
                keel_depth=self.keel_depth,
                result=result,
            )

            # 🚀 SHOW RESULTS
            self.show_results_dialog(result)

        except ValueError:
            print("Invalid input!")

    def show_results_dialog(self, result):
        dialog = QDialog()
        dialog.setObjectName("info_sheet_results_dialog")
        dialog.setWindowTitle("Information Sheet Results")
        dialog.resize(scale(928), scale(596))

        # Match parent UI background
        bg_label = QLabel(dialog)
        bg_label.setPixmap(QPixmap(BG_path))
        _responsive_bg = ResponsiveBackground(dialog, bg_label, BG_path)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(scale(30), scale(30), scale(30), scale(30))
        root.setSpacing(scale(12))

        # Map (PNG) on top
        map_label = QLabel(dialog)
        map_label.setAlignment(Qt.AlignCenter)
        map_label.setMinimumHeight(scale(280))
        map_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.88); border-radius: 10px;"
        )

        png_bytes = getattr(getattr(result, "rendered_map", None), "png_bytes", None)
        if png_bytes:
            pm = QPixmap()
            pm.loadFromData(png_bytes, "PNG")

            def _set_scaled():
                if pm.isNull():
                    return
                map_label.setPixmap(
                    pm.scaled(
                        map_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

            _set_scaled()

            old_resize_event = map_label.resizeEvent

            def _resize_event(evt):
                _set_scaled()
                if old_resize_event:
                    old_resize_event(evt)

            map_label.resizeEvent = _resize_event  # type: ignore[method-assign]
        else:
            map_label.setText("No rendered map available.")

        # Threat table under it
        table = QTableWidget(dialog)
        table.setRowCount(len(result.results))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Platform", "Surface Threat", "Subsea Threat"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setStyleSheet(
            "background-color: rgba(255,255,255,0.92); border-radius: 10px;"
        )

        def _threat_key(level: ThreatLevel | str) -> str | None:
            """Normalize API threat to logic values: red/yellow/green."""
            raw = getattr(level, "value", level)
            key = str(raw).strip().lower()

            # Handle forms like "ThreatLevel.RED" from str(enum_member).
            if "." in key:
                key = key.split(".")[-1]

            if key in {"red", "yellow", "green"}:
                return key
            return None

        def _threat_bg(level: ThreatLevel | str) -> QColor:
            key = _threat_key(level)
            if key == "red":
                return QColor(212, 93, 93, 160)
            if key == "yellow":
                return QColor(241, 196, 15, 160)
            if key == "green":
                return QColor(46, 204, 113, 140)
            return QColor(140, 140, 140, 140)

        def _threat_text(level: ThreatLevel | str) -> str:
            key = _threat_key(level)
            if key is None:
                raw = getattr(level, "value", level)
                return f"UNKNOWN({raw})"
            return key.upper()

        for row, r in enumerate(result.results):
            p_item = QTableWidgetItem(r.platform.name)
            s_item = QTableWidgetItem(_threat_text(r.surface_threat))
            u_item = QTableWidgetItem(_threat_text(r.subsea_threat))
            s_item.setBackground(_threat_bg(r.surface_threat))
            u_item.setBackground(_threat_bg(r.subsea_threat))
            table.setItem(row, 0, p_item)
            table.setItem(row, 1, s_item)
            table.setItem(row, 2, u_item)

        close_btn = QPushButton("Close", dialog)
        close_btn.setStyleSheet(Engineer_buttons_st + " color: white;")
        close_btn.setMinimumHeight(scale(48))
        close_btn.clicked.connect(dialog.accept)

        root.addWidget(map_label, stretch=3)
        root.addWidget(table, stretch=2)
        root.addWidget(close_btn, stretch=0)

        dialog.exec_()
