import os

from PyQt5.QtCore import QCoreApplication, QMetaObject, Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from stylesheet import Engineer_buttons_st, back_st
from utils import BG_path, ResponsiveBackground, scale


class _IntDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        from PyQt5.QtWidgets import QSpinBox

        editor = QSpinBox(parent)
        editor.setMinimum(0)
        editor.setMaximum(1_000_000_000)
        editor.setStyleSheet("background: white; color: black;")
        return editor


class EdnaUi(object):
    def setupUI(self, Dialog):
        Dialog.setObjectName("EdnaDialog")
        Dialog.resize(scale(928), scale(596))
        Dialog.setMinimumSize(scale(800), scale(500))
        Dialog.setMaximumSize(scale(1200), scale(800))

        # Font (match the rest)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, "GillSans.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        families = QFontDatabase.applicationFontFamilies(font_id)
        base_font = QFont(families[0], 13) if families else QFont("Gill Sans", 13)
        btn_font = QFont(families[0], 14) if families else QFont("Gill Sans", 14)

        # Responsive background (cover behavior)
        self._bg_label = QLabel(Dialog)
        self._bg_label.setObjectName("EdnaBackground")
        self._responsive_bg = ResponsiveBackground(Dialog, self._bg_label, BG_path)

        root_layout = QVBoxLayout(Dialog)
        root_layout.setContentsMargins(scale(20), scale(20), scale(20), scale(20))
        root_layout.setSpacing(scale(12))

        # Top bar
        top_bar = QHBoxLayout()

        self.backBtn = QPushButton(Dialog)
        self.backBtn.setObjectName("Back Button")
        self.backBtn.setIcon(QIcon.fromTheme("go-previous"))
        self.backBtn.setStyleSheet(back_st + " color: white;")
        self.backBtn.setText("Back")
        self.backBtn.setMinimumSize(scale(110), scale(40))
        self.backBtn.setFont(btn_font)
        top_bar.addWidget(self.backBtn)

        title = QLabel("eDNA Frequency Calculator", Dialog)
        title.setStyleSheet("color: white; font-weight: bold;")
        title.setFont(QFont(base_font.family(), 16))
        title.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(title, stretch=1)

        top_bar.addSpacing(scale(110))
        root_layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget(10, 2, Dialog)
        self.table.setObjectName("ednaTable")
        self.table.setHorizontalHeaderLabels(["Species Name", "Count"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
        )
        self.table.setFont(base_font)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, scale(420))
        self.table.setColumnWidth(1, scale(160))
        self.table.horizontalHeader().setStretchLastSection(True)

        # Count column: integer >= 0
        self.table.setItemDelegateForColumn(1, _IntDelegate(self.table))
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0) is None:
                self.table.setItem(r, 0, QTableWidgetItem(""))
            if self.table.item(r, 1) is None:
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, 1, item)

        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: rgba(0,0,0,0.25);
                color: white;
                gridline-color: rgba(255,255,255,0.18);
                border: 1px solid rgba(255,255,255,0.22);
                border-radius: 10px;
            }
            QTableWidget::item {
                background-color: white;
                color: black;
            }
            QTableWidget::item:alternate {
                background-color: rgba(245, 245, 245, 1);
                color: black;
            }
            QHeaderView::section {
                background-color: rgba(0,0,0,0.35);
                color: white;
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: rgba(41, 128, 185, 0.35);
            }
            QSpinBox {
                background: white;
                color: black;
            }
            QLineEdit {
                background: white;
                color: black;
            }
            """
        )

        root_layout.addWidget(self.table, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.calculateBtn = QPushButton("Calculate", Dialog)
        self.calculateBtn.setObjectName("Calculate Button")
        self.calculateBtn.setStyleSheet(Engineer_buttons_st + " color: white;")
        self.calculateBtn.setMinimumSize(scale(180), scale(50))
        self.calculateBtn.setFont(btn_font)
        self.calculateBtn.clicked.connect(self.calculate)
        btn_row.addWidget(self.calculateBtn)

        root_layout.addLayout(btn_row)

        Dialog.setLayout(root_layout)
        self.setText(Dialog)
        QMetaObject.connectSlotsByName(Dialog)

    def setText(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "eDNA", None))

    def _ensure_percentage_column(self):
        if self.table.columnCount() < 3:
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(
                ["Species Name", "Count", "Percentage (%)"]
            )
            self.table.setColumnWidth(2, scale(180))

    def calculate(self):
        # Read inputs
        counts = []
        total = 0

        for r in range(self.table.rowCount()):
            count_item = self.table.item(r, 1)
            raw = (count_item.text().strip() if count_item else "")

            try:
                c = int(raw) if raw != "" else 0
            except ValueError:
                c = 0
            if c < 0:
                c = 0

            counts.append(c)
            total += c

        self._ensure_percentage_column()

        # Compute and display
        for r, c in enumerate(counts):
            pct = (c / total * 100.0) if total > 0 else 0.0
            pct_item = QTableWidgetItem(f"{pct:.2f}")
            pct_item.setFlags(pct_item.flags() & ~Qt.ItemIsEditable)
            pct_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, pct_item)
