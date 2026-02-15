import sys
import cv2
import os
import logging
import time

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy,
    QDialog, QStackedWidget, QLineEdit
)

from PyQt6.QtGui import QFont, QColor, QImage, QPixmap, QFontDatabase
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= CONSTANTS =================
PRODUCTS = {
    "🚬 たばこ": 850,
    "🍺 アルコール": 300,
    "💧 水": 100,
    "🍟 ポテトチップス": 150,
    "🧃 ジュース": 120,
    "🍞 パン": 200,
    "🍫 チョコレート": 130,
}

AGE_RESTRICTED = ["🚬 たばこ", "🍺 アルコール"]

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)

AGE_LIST = [
    "(0-2)", "(4-6)", "(8-12)", "(15-20)",
    "(25-32)", "(38-43)", "(48-53)", "(60-100)",
]

FACE_SCALE_FACTOR = 1.3
FACE_MIN_NEIGHBORS = 5
CAMERA_INTERVAL_MS = 30
LEGAL_AGE = 20
CONFIDENT_AGE = 25

# NFC simulation database (card_id -> age)
NFC_DATABASE = {
    "NFC-001-TANAKA": {"name": "田中太郎", "age": 22, "dob": "2003-03-15"},
    "NFC-002-SUZUKI": {"name": "鈴木花子", "age": 17, "dob": "2008-07-22"},
    "NFC-003-SATO":   {"name": "佐藤健一", "age": 35, "dob": "1990-01-10"},
    "NFC-004-YAMADA": {"name": "山田美咲", "age": 19, "dob": "2006-11-05"},
    "NFC-005-TAKAGI": {"name": "高木翔太", "age": 24, "dob": "2001-06-30"},
    "NFC-006-NAKAMURA": {"name": "中村遥", "age": 15, "dob": "2010-09-12"},
}

# ================= COLORS =================
COLORS = {
    "bg":             "#0F172A",
    "panel":          "#1E293B",
    "panel_border":   "#334155",
    "header_bg":      "#7C3AED",
    "header_bg2":     "#4F46E5",
    "accent":         "#8B5CF6",
    "accent_hover":   "#A78BFA",
    "accent_pressed": "#7C3AED",
    "danger":         "#EF4444",
    "danger_hover":   "#F87171",
    "danger_pressed": "#DC2626",
    "danger_dark":    "#991B1B",
    "danger_bg":      "#450A0A",
    "danger_border":  "#B91C1C",
    "success":        "#10B981",
    "success_hover":  "#34D399",
    "success_pressed": "#059669",
    "warning":        "#F59E0B",
    "warning_hover":  "#FBBF24",
    "warning_pressed": "#D97706",
    "info":           "#3B82F6",
    "info_hover":     "#60A5FA",
    "info_pressed":   "#2563EB",
    "nfc_blue":       "#0EA5E9",
    "nfc_blue_hover": "#38BDF8",
    "nfc_blue_pressed": "#0284C7",
    "nfc_bg":         "#0C4A6E",
    "nfc_border":     "#0369A1",
    "text":           "#F1F5F9",
    "text_dim":       "#94A3B8",
    "text_muted":     "#64748B",
    "restricted_bg":  "#451A1A",
    "restricted_fg":  "#FCA5A5",
    "normal_bg":      "#1E3A5F",
    "normal_fg":      "#93C5FD",
    "cart_item_bg":   "#2D1B69",
    "cart_item_fg":   "#C4B5FD",
    "camera_border":  "#8B5CF6",
    "list_bg":        "#0F172A",
}

# ================= STYLESHEET =================
GLOBAL_STYLE = f"""
    QWidget {{
        background: {COLORS['bg']};
        color: {COLORS['text']};
        font-family: 'Segoe UI', 'Noto Sans JP', 'Meiryo', 'Yu Gothic UI',
                     'Helvetica Neue', Arial, sans-serif;
    }}
    QListWidget {{
        background: {COLORS['list_bg']};
        border: 2px solid {COLORS['panel_border']};
        border-radius: 12px;
        padding: 8px;
        outline: 0;
        font-size: 15px;
    }}
    QListWidget::item {{
        padding: 14px 18px;
        margin: 4px 2px;
        border-radius: 10px;
        border: 1px solid transparent;
    }}
    QListWidget::item:selected {{
        background: {COLORS['accent']};
        color: white;
        border: 1px solid {COLORS['accent_hover']};
    }}
    QListWidget::item:hover:!selected {{
        border: 1px solid {COLORS['accent']};
        background: rgba(139, 92, 246, 0.12);
    }}
    QScrollBar:vertical {{
        background: {COLORS['panel']};
        width: 10px;
        margin: 4px 2px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['text_muted']};
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['text_dim']};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
"""


# ================= HELPERS =================
def make_shadow(color="#00000060", blur=24, ox=0, oy=6):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setColor(QColor(color))
    shadow.setOffset(ox, oy)
    return shadow


def make_btn(text, color, hover, pressed, bold=True, padding="16px 24px"):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFont(
        QFont("Segoe UI", 14, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color};
            color: white;
            border: none;
            border-radius: 12px;
            padding: {padding};
            font-size: 15px;
            font-weight: {'700' if bold else '500'};
            letter-spacing: 0.5px;
        }}
        QPushButton:hover {{
            background: {hover};
        }}
        QPushButton:pressed {{
            background: {pressed};
        }}
        QPushButton:disabled {{
            background: {COLORS['text_muted']};
            color: {COLORS['panel']};
        }}
    """)
    btn.setGraphicsEffect(make_shadow(color + "50", 16, 0, 4))
    return btn


def make_section_label(text, size=13):
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
    lbl.setStyleSheet(f"""
        color: {COLORS['text_dim']};
        letter-spacing: 2px;
        padding: 4px 8px;
        margin-bottom: 2px;
        font-size: {size}px;
    """)
    return lbl


def make_panel():
    panel = QFrame()
    panel.setStyleSheet(f"""
        QFrame {{
            background: {COLORS['panel']};
            border: 1px solid {COLORS['panel_border']};
            border-radius: 16px;
        }}
    """)
    panel.setGraphicsEffect(make_shadow("#00000040", 20, 0, 4))
    return panel


# ================= NFC SCAN DIALOG =================
class NFCScanDialog(QDialog):
    """
    NFC ID card scanning dialog.
    Shown when AI detects age < 25 for age-restricted items.
    Simulates NFC scan with a text input for demo purposes.
    """

    def __init__(self, detected_age_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🪪 NFC ID Scan")
        self.setFixedSize(600, 720)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.verified_age = None
        self.verified_name = None
        self.detected_age_text = detected_age_text
        self.scan_animation_timer = None
        self.pulse_state = 0

        self._build()
        self._start_pulse_animation()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['panel']};
                border: 3px solid {COLORS['nfc_blue']};
                border-radius: 20px;
            }}
        """)
        self.card.setGraphicsEffect(make_shadow("#0EA5E960", 40, 0, 8))

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        # ── Header Banner ──
        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['nfc_blue']},
                    stop:1 {COLORS['info']}
                );
                border-radius: 14px;
                border: none;
            }}
        """)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(20, 18, 20, 18)
        banner_layout.setSpacing(6)

        icon_lbl = QLabel("🪪")
        icon_lbl.setFont(QFont("Segoe UI", 44))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent; border:none;")

        title = QLabel("IDカードをスキャン")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:white; background:transparent; border:none; letter-spacing:1px;")

        sub = QLabel("SCAN YOUR ID CARD (NFC)")
        sub.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            "color:rgba(255,255,255,0.65); background:transparent; border:none; letter-spacing:3px;")

        banner_layout.addWidget(icon_lbl)
        banner_layout.addWidget(title)
        banner_layout.addWidget(sub)

        # ── Reason Section ──
        reason_frame = QFrame()
        reason_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(14, 165, 233, 0.08);
                border: 2px solid {COLORS['nfc_border']};
                border-radius: 12px;
            }}
        """)
        reason_layout = QVBoxLayout(reason_frame)
        reason_layout.setContentsMargins(18, 14, 18, 14)
        reason_layout.setSpacing(6)

        reason_title = QLabel(f"AI推定年齢: {self.detected_age_text}")
        reason_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        reason_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reason_title.setStyleSheet(
            f"color:{COLORS['warning']}; background:transparent; border:none;")

        reason_msg = QLabel(
            "25歳未満と推定されたため、\n"
            "本人確認書類のNFCスキャンが必要です"
        )
        reason_msg.setFont(QFont("Segoe UI", 12))
        reason_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reason_msg.setWordWrap(True)
        reason_msg.setStyleSheet(
            f"color:{COLORS['text_dim']}; background:transparent; border:none;")

        reason_layout.addWidget(reason_title)
        reason_layout.addWidget(reason_msg)

        # ── NFC Scan Area ──
        self.scan_frame = QFrame()
        self.scan_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['nfc_bg']};
                border: 3px dashed {COLORS['nfc_blue']};
                border-radius: 16px;
            }}
        """)
        scan_layout = QVBoxLayout(self.scan_frame)
        scan_layout.setContentsMargins(24, 24, 24, 24)
        scan_layout.setSpacing(12)

        self.nfc_icon = QLabel("📡")
        self.nfc_icon.setFont(QFont("Segoe UI", 52))
        self.nfc_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nfc_icon.setStyleSheet("background:transparent; border:none;")

        self.scan_status = QLabel("NFCリーダーにカードをかざしてください")
        self.scan_status.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_status.setWordWrap(True)
        self.scan_status.setStyleSheet(
            f"color:{COLORS['nfc_blue']}; background:transparent; border:none;")

        self.scan_sub = QLabel("Place your ID card on the NFC reader")
        self.scan_sub.setFont(QFont("Segoe UI", 11))
        self.scan_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_sub.setStyleSheet(
            f"color:{COLORS['text_muted']}; background:transparent; border:none;")

        # Simulated NFC input
        input_note = QLabel("── デモ用: カードIDを入力 ──")
        input_note.setFont(QFont("Segoe UI", 10))
        input_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        input_note.setStyleSheet(
            f"color:{COLORS['text_muted']}; background:transparent; border:none;")

        self.nfc_input = QLineEdit()
        self.nfc_input.setPlaceholderText("例: NFC-001-TANAKA")
        self.nfc_input.setFont(QFont("Segoe UI", 14))
        self.nfc_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nfc_input.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['nfc_border']};
                border-radius: 10px;
                padding: 14px 18px;
                font-size: 14px;
                letter-spacing: 1px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['nfc_blue']};
                background: rgba(14, 165, 233, 0.05);
            }}
        """)

        scan_layout.addWidget(self.nfc_icon)
        scan_layout.addWidget(self.scan_status)
        scan_layout.addWidget(self.scan_sub)
        scan_layout.addSpacing(8)
        scan_layout.addWidget(input_note)
        scan_layout.addWidget(self.nfc_input)

        # ── Result Area (hidden initially) ──
        self.result_frame = QFrame()
        self.result_frame.setVisible(False)
        self.result_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['list_bg']};
                border: 2px solid {COLORS['panel_border']};
                border-radius: 12px;
            }}
        """)
        self.result_layout = QVBoxLayout(self.result_frame)
        self.result_layout.setContentsMargins(18, 14, 18, 14)
        self.result_layout.setSpacing(6)

        self.result_icon = QLabel()
        self.result_icon.setFont(QFont("Segoe UI", 28))
        self.result_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_icon.setStyleSheet("background:transparent; border:none;")

        self.result_text = QLabel()
        self.result_text.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.result_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_text.setWordWrap(True)
        self.result_text.setStyleSheet(f"background:transparent; border:none;")

        self.result_detail = QLabel()
        self.result_detail.setFont(QFont("Segoe UI", 12))
        self.result_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_detail.setWordWrap(True)
        self.result_detail.setStyleSheet(
            f"color:{COLORS['text_dim']}; background:transparent; border:none;")

        self.result_layout.addWidget(self.result_icon)
        self.result_layout.addWidget(self.result_text)
        self.result_layout.addWidget(self.result_detail)

        # ── Accepted cards info ──
        cards_info = QLabel(
            "対応カード:  運転免許証  ·  マイナンバーカード  ·  パスポート  ·  在留カード"
        )
        cards_info.setFont(QFont("Segoe UI", 10))
        cards_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cards_info.setWordWrap(True)
        cards_info.setStyleSheet(
            f"color:{COLORS['text_muted']}; background:transparent; border:none;")

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = make_btn(
            "✕  キャンセル",
            COLORS["danger"], COLORS["danger_hover"], COLORS["danger_pressed"]
        )
        cancel_btn.clicked.connect(self.reject)

        self.scan_btn = make_btn(
            "📡  スキャン",
            COLORS["nfc_blue"], COLORS["nfc_blue_hover"], COLORS["nfc_blue_pressed"]
        )
        self.scan_btn.clicked.connect(self._simulate_nfc_scan)

        self.proceed_btn = make_btn(
            "✓  支払いに進む",
            COLORS["success"], COLORS["success_hover"], COLORS["success_pressed"]
        )
        self.proceed_btn.setVisible(False)
        self.proceed_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.proceed_btn)

        # ── Assemble ──
        layout.addWidget(banner)
        layout.addWidget(reason_frame)
        layout.addWidget(self.scan_frame)
        layout.addWidget(self.result_frame)
        layout.addWidget(cards_info)
        layout.addLayout(btn_layout)

        outer.addWidget(self.card)

    def _start_pulse_animation(self):
        self.scan_animation_timer = QTimer()
        self.scan_animation_timer.timeout.connect(self._pulse_nfc)
        self.scan_animation_timer.start(800)

    def _pulse_nfc(self):
        self.pulse_state = (self.pulse_state + 1) % 3
        icons = ["📡", "🔵", "📶"]
        self.nfc_icon.setText(icons[self.pulse_state])

    def _simulate_nfc_scan(self):
        card_id = self.nfc_input.text().strip().upper()

        if not card_id:
            self.scan_status.setText("❌ カードIDを入力してください")
            self.scan_status.setStyleSheet(
                f"color:{COLORS['danger']}; background:transparent; border:none;")
            return

        # Show scanning animation
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("⏳  スキャン中...")
        self.scan_status.setText("📡  読み取り中...")
        self.scan_status.setStyleSheet(
            f"color:{COLORS['warning']}; background:transparent; border:none;")

        QTimer.singleShot(1500, lambda: self._process_nfc_result(card_id))

    def _process_nfc_result(self, card_id):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("📡  再スキャン")

        if self.scan_animation_timer:
            self.scan_animation_timer.stop()

        if card_id not in NFC_DATABASE:
            # Card not found
            self.nfc_icon.setText("❌")
            self.scan_status.setText("カードを認識できません")
            self.scan_status.setStyleSheet(
                f"color:{COLORS['danger']}; background:transparent; border:none;")
            self.scan_sub.setText("登録されていないカードです。別のカードをお試しください。")

            self.result_frame.setVisible(True)
            self.result_icon.setText("⚠️")
            self.result_text.setText("カードが見つかりません")
            self.result_text.setStyleSheet(
                f"color:{COLORS['danger']}; background:transparent; border:none;")
            self.result_detail.setText(f"ID: {card_id}")
            self.result_frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(239, 68, 68, 0.08);
                    border: 2px solid {COLORS['danger_border']};
                    border-radius: 12px;
                }}
            """)
            self.proceed_btn.setVisible(False)
            return

        person = NFC_DATABASE[card_id]
        self.verified_name = person["name"]
        self.verified_age = person["age"]

        self.result_frame.setVisible(True)

        if person["age"] >= LEGAL_AGE:
            # Age verified - OK
            self.nfc_icon.setText("✅")
            self.scan_status.setText("本人確認完了")
            self.scan_status.setStyleSheet(
                f"color:{COLORS['success']}; background:transparent; border:none;")
            self.scan_sub.setText("年齢確認に成功しました")

            self.scan_frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(16, 185, 129, 0.06);
                    border: 3px solid {COLORS['success']};
                    border-radius: 16px;
                }}
            """)

            self.result_icon.setText("✅")
            self.result_text.setText(f"{person['name']}  ─  {person['age']}歳")
            self.result_text.setStyleSheet(
                f"color:{COLORS['success']}; background:transparent; border:none;")
            self.result_detail.setText(
                f"生年月日: {person['dob']}  ·  ID: {card_id}")
            self.result_frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(16, 185, 129, 0.08);
                    border: 2px solid {COLORS['success']};
                    border-radius: 12px;
                }}
            """)

            self.proceed_btn.setVisible(True)
            self.scan_btn.setVisible(False)

        else:
            # Underage confirmed
            self.nfc_icon.setText("⛔")
            self.scan_status.setText("年齢制限: 購入不可")
            self.scan_status.setStyleSheet(
                f"color:{COLORS['danger']}; background:transparent; border:none;")
            self.scan_sub.setText("20歳未満のため購入できません")

            self.scan_frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(239, 68, 68, 0.06);
                    border: 3px solid {COLORS['danger']};
                    border-radius: 16px;
                }}
            """)

            self.result_icon.setText("⛔")
            self.result_text.setText(f"{person['name']}  ─  {person['age']}歳")
            self.result_text.setStyleSheet(
                f"color:{COLORS['danger']}; background:transparent; border:none;")
            self.result_detail.setText(
                f"生年月日: {person['dob']}\n"
                f"20歳未満のお客様は年齢制限商品を購入できません"
            )
            self.result_frame.setStyleSheet(f"""
                QFrame {{
                    background: rgba(239, 68, 68, 0.08);
                    border: 2px solid {COLORS['danger']};
                    border-radius: 12px;
                }}
            """)

            self.proceed_btn.setVisible(False)

    def closeEvent(self, event):
        if self.scan_animation_timer:
            self.scan_animation_timer.stop()
        event.accept()

    def reject(self):
        if self.scan_animation_timer:
            self.scan_animation_timer.stop()
        super().reject()

    def accept(self):
        if self.scan_animation_timer:
            self.scan_animation_timer.stop()
        super().accept()


# ================= CAMERA VERIFICATION DIALOG =================
class CameraVerificationDialog(QDialog):
    """Camera opens only during payment for age verification."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📷 年齢確認")
        self.setFixedSize(620, 660)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.detected_age = None
        self.detected_age_text = None
        self.cap = None
        self.timer = None
        self.face_cascade = None
        self.age_net = None

        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.main_card = QFrame()
        self.main_card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['panel']};
                border: 3px solid {COLORS['camera_border']};
                border-radius: 20px;
            }}
        """)
        self.main_card.setGraphicsEffect(make_shadow("#8B5CF660", 36, 0, 8))

        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['header_bg']},
                    stop:1 {COLORS['header_bg2']}
                );
                border-radius: 14px; border: none;
            }}
        """)
        hdr_layout = QVBoxLayout(hdr)
        hdr_layout.setContentsMargins(20, 16, 20, 16)
        hdr_layout.setSpacing(4)

        t = QLabel("📷  年齢確認カメラ")
        t.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color:white; background:transparent; border:none;")

        s = QLabel("顔をカメラに向けてください")
        s.setFont(QFont("Segoe UI", 12))
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet(
            "color:rgba(255,255,255,0.65); background:transparent; border:none;")

        hdr_layout.addWidget(t)
        hdr_layout.addWidget(s)

        # Camera
        cam_frame = QFrame()
        cam_frame.setStyleSheet(f"""
            QFrame {{
                background: #000;
                border: 3px solid {COLORS['camera_border']};
                border-radius: 14px;
            }}
        """)
        cam_inner = QVBoxLayout(cam_frame)
        cam_inner.setContentsMargins(4, 4, 4, 4)

        self.camera_label = QLabel("カメラ起動中...")
        self.camera_label.setFixedSize(540, 360)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setFont(QFont("Segoe UI", 14))
        self.camera_label.setStyleSheet(
            "background:#000; border-radius:10px; border:none; color:#64748B;")
        cam_inner.addWidget(self.camera_label,
                            alignment=Qt.AlignmentFlag.AlignCenter)

        # Status
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['list_bg']};
                border: 2px solid {COLORS['panel_border']};
                border-radius: 12px;
            }}
        """)
        st_layout = QHBoxLayout(self.status_frame)
        st_layout.setContentsMargins(18, 14, 18, 14)

        self.status_icon = QLabel("⏳")
        self.status_icon.setFont(QFont("Segoe UI", 24))
        self.status_icon.setStyleSheet("background:transparent; border:none;")

        self.status_text = QLabel("顔を検出しています...")
        self.status_text.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.status_text.setStyleSheet(
            f"color:{COLORS['text_dim']}; background:transparent; border:none;")

        st_layout.addWidget(self.status_icon)
        st_layout.addWidget(self.status_text, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = make_btn(
            "✕  キャンセル",
            COLORS["danger"], COLORS["danger_hover"], COLORS["danger_pressed"]
        )
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = make_btn(
            "✓  確認完了",
            COLORS["success"], COLORS["success_hover"], COLORS["success_pressed"]
        )
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.confirm_btn)

        layout.addWidget(hdr)
        layout.addWidget(cam_frame)
        layout.addWidget(self.status_frame)
        layout.addLayout(btn_layout)

        outer.addWidget(self.main_card)

    def start_camera(self, face_cascade, age_net):
        self.face_cascade = face_cascade
        self.age_net = age_net

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            logger.error("Camera failed to open in verification")
            self.status_icon.setText("❌")
            self.status_text.setText("カメラを開けません")
            self.status_text.setStyleSheet(
                f"color:{COLORS['danger']}; background:transparent; border:none;")
            return False

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(CAMERA_INTERVAL_MS)
        logger.info("Verification camera started")
        return True

    def _update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, FACE_SCALE_FACTOR, FACE_MIN_NEIGHBORS
        )

        detected = False

        for (x, y, w, h) in faces:
            face_roi = frame[y:y + h, x:x + w]
            blob = cv2.dnn.blobFromImage(
                face_roi, 1.0, (227, 227),
                MODEL_MEAN_VALUES, swapRB=False
            )
            self.age_net.setInput(blob)
            preds = self.age_net.forward()
            age_text = AGE_LIST[preds[0].argmax()]

            if age_text in ["(0-2)", "(4-6)", "(8-12)", "(15-20)"]:
                self.detected_age = 16
            elif age_text == "(25-32)":
                self.detected_age = 28
            elif age_text == "(38-43)":
                self.detected_age = 40
            elif age_text == "(48-53)":
                self.detected_age = 50
            else:
                self.detected_age = 70

            self.detected_age_text = age_text

            if self.detected_age >= CONFIDENT_AGE:
                box_color = (16, 185, 129)
                self.status_icon.setText("🟢")
                self.status_text.setText(f"年齢確認 OK ─ 推定: {age_text}")
                self.status_text.setStyleSheet(
                    f"color:{COLORS['success']}; background:transparent; border:none;")
                self.status_frame.setStyleSheet(f"""
                    QFrame {{
                        background: rgba(16,185,129,0.08);
                        border: 2px solid {COLORS['success']};
                        border-radius: 12px;
                    }}
                """)
                self.confirm_btn.setEnabled(True)
                self.confirm_btn.setText("✓  確認完了  ─  支払いへ")

            elif self.detected_age >= LEGAL_AGE:
                # Between 20-24: might be ok but need NFC
                box_color = (245, 158, 11)
                self.status_icon.setText("🟡")
                self.status_text.setText(f"推定: {age_text} ─ NFC確認が必要")
                self.status_text.setStyleSheet(
                    f"color:{COLORS['warning']}; background:transparent; border:none;")
                self.status_frame.setStyleSheet(f"""
                    QFrame {{
                        background: rgba(245,158,11,0.08);
                        border: 2px solid {COLORS['warning']};
                        border-radius: 12px;
                    }}
                """)
                self.confirm_btn.setEnabled(True)
                self.confirm_btn.setText("🪪  IDカードをスキャン")

            else:
                box_color = (239, 68, 68)
                self.status_icon.setText("🔴")
                self.status_text.setText(f"年齢不足 ─ 推定: {age_text}")
                self.status_text.setStyleSheet(
                    f"color:{COLORS['danger']}; background:transparent; border:none;")
                self.status_frame.setStyleSheet(f"""
                    QFrame {{
                        background: rgba(239,68,68,0.08);
                        border: 2px solid {COLORS['danger']};
                        border-radius: 12px;
                    }}
                """)
                self.confirm_btn.setEnabled(True)
                self.confirm_btn.setText("🪪  IDカードをスキャン")

            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 3)
            cv2.putText(frame, age_text, (x, y - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, box_color, 2)
            detected = True
            break

        if not detected:
            self.status_icon.setText("⏳")
            self.status_text.setText("顔を検出しています...")
            self.status_text.setStyleSheet(
                f"color:{COLORS['text_dim']}; background:transparent; border:none;")
            self.status_frame.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['list_bg']};
                    border: 2px solid {COLORS['panel_border']};
                    border-radius: 12px;
                }}
            """)
            self.confirm_btn.setEnabled(False)
            self.confirm_btn.setText("✓  確認完了")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w,
                     QImage.Format.Format_RGB888).copy()
        scaled = QPixmap.fromImage(img).scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.camera_label.setPixmap(scaled)

    def _stop_camera(self):
        if self.timer:
            self.timer.stop()
            self.timer = None
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("Verification camera stopped")

    def closeEvent(self, event):
        self._stop_camera()
        event.accept()

    def reject(self):
        self._stop_camera()
        super().reject()

    def accept(self):
        self._stop_camera()
        super().accept()


# ================= UNDERAGE ALERT DIALOG =================
class UnderageAlertDialog(QDialog):
    """Red-themed alert for confirmed underage after NFC scan."""

    def __init__(self, name, age, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⛔ 年齢制限")
        self.setFixedSize(560, 480)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build(name, age)

    def _build(self, name, age):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['danger_bg']};
                border: 3px solid {COLORS['danger']};
                border-radius: 20px;
            }}
        """)
        card.setGraphicsEffect(make_shadow("#EF444480", 40, 0, 8))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(14)

        # Banner
        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['danger']};
                border-radius: 14px; border: none;
            }}
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(20, 18, 20, 18)
        b_layout.setSpacing(6)

        icon_lbl = QLabel("⛔")
        icon_lbl.setFont(QFont("Segoe UI", 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "background:transparent; border:none; color:white;")

        title = QLabel("購入できません")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:white; background:transparent; border:none; letter-spacing:2px;")

        sub = QLabel("PURCHASE DENIED")
        sub.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            "color:rgba(255,255,255,0.7); background:transparent; border:none; letter-spacing:3px;")

        b_layout.addWidget(icon_lbl)
        b_layout.addWidget(title)
        b_layout.addWidget(sub)

        # Person info
        info = QLabel(f"👤  {name}  ─  {age}歳")
        info.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet(f"""
            color: {COLORS['danger']};
            background: rgba(239, 68, 68, 0.1);
            border: 2px solid {COLORS['danger_border']};
            border-radius: 10px;
            padding: 14px;
        """)

        # Message
        msg = QLabel(
            "20歳未満のお客様は\n"
            "たばこ・アルコール等の\n"
            "年齢制限商品を購入できません。\n\n"
            "スタッフにご相談ください。"
        )
        msg.setFont(QFont("Segoe UI", 14))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(
            f"color:{COLORS['restricted_fg']}; background:transparent; border:none; line-height:1.5;")

        # Close button
        close_btn = QPushButton("✕  閉じる")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 24px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {COLORS['danger_hover']}; }}
            QPushButton:pressed {{ background: {COLORS['danger_pressed']}; }}
        """)
        close_btn.setGraphicsEffect(make_shadow("#EF444460", 16, 0, 4))

        layout.addWidget(banner)
        layout.addWidget(info)
        layout.addWidget(msg)
        layout.addStretch()
        layout.addWidget(close_btn)

        outer.addWidget(card)


# ================= SUCCESS DIALOG =================
class PaymentSuccessDialog(QDialog):
    """Green-themed payment success dialog."""

    def __init__(self, count, total, verified_name=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(480, 440)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build(count, total, verified_name)

    def _build(self, count, total, verified_name):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['panel']};
                border: 3px solid {COLORS['success']};
                border-radius: 20px;
            }}
        """)
        card.setGraphicsEffect(make_shadow("#10B98160", 36, 0, 8))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(16)

        icon_lbl = QLabel("✅")
        icon_lbl.setFont(QFont("Segoe UI", 52))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent; border:none;")

        title = QLabel("お支払い完了")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color:{COLORS['success']}; background:transparent; border:none;")

        verified_text = ""
        if verified_name:
            verified_text = f"本人確認: {verified_name} 様\n"

        detail = QLabel(
            f"{verified_text}"
            f"商品数：{count} 点\n"
            f"合計金額：¥{total:,}\n\n"
            f"ありがとうございます！\n"
            f"またのご来店をお待ちしております。"
        )
        detail.setFont(QFont("Segoe UI", 14))
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setWordWrap(True)
        detail.setStyleSheet(
            f"color:{COLORS['text_dim']}; background:transparent; border:none; line-height:1.6;")

        ok_btn = make_btn(
            "OK", COLORS["success"], COLORS["success_hover"], COLORS["success_pressed"])
        ok_btn.clicked.connect(self.accept)

        layout.addWidget(icon_lbl)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addStretch()
        layout.addWidget(ok_btn)

        outer.addWidget(card)


# ================= MAIN APP =================
class MyMart(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("✦ My Mart — AI Self POS")
        self.setGeometry(30, 20, 1200, 780)
        self.setMinimumSize(1000, 650)

        self.cart = []
        self._init_error = False

        if not self._check_required_files():
            self._init_error = True
            return

        if not self._init_models():
            self._init_error = True
            return

        self._build_ui()
        self._update_totals()

    def _check_required_files(self):
        required = [
            "haarcascade_frontalface_default.xml",
            "age_deploy.prototxt",
            "age_net.caffemodel",
        ]
        for f in required:
            if not os.path.exists(f):
                logger.error(f"Missing: {f}")
                QMessageBox.critical(self, "Error", f"必要ファイルがありません:\n{f}")
                return False
        return True

    def _init_models(self):
        try:
            self.face_cascade = cv2.CascadeClassifier(
                "haarcascade_frontalface_default.xml")
            self.age_net = cv2.dnn.readNetFromCaffe(
                "age_deploy.prototxt", "age_net.caffemodel")
            logger.info("Models loaded")
            return True
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            QMessageBox.critical(self, "Error", f"モデル読み込み失敗:\n{e}")
            return False

    # ================= UI =================
    def _build_ui(self):
        self.setStyleSheet(GLOBAL_STYLE)

        # ── HEADER ──
        header = QFrame()
        header.setFixedHeight(76)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['header_bg']},
                    stop:1 {COLORS['header_bg2']}
                );
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
        """)
        header.setGraphicsEffect(make_shadow("#7C3AED50", 24, 0, 6))

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 0, 28, 0)

        title = QLabel("✦  My Mart")
        title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title.setStyleSheet(
            "color:white; background:transparent; border:none; letter-spacing:1px;")

        subtitle = QLabel("AI Self Checkout POS")
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setStyleSheet(
            "color:rgba(255,255,255,0.65); background:transparent; border:none;")

        self.header_status = QLabel("●  Ready")
        self.header_status.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.header_status.setStyleSheet(
            f"color:{COLORS['success']}; background:transparent; border:none;")

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        header_layout.addLayout(title_col)
        header_layout.addStretch()
        header_layout.addWidget(self.header_status)

        # ── LEFT: Products ──
        left = make_panel()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(14)

        left_layout.addWidget(make_section_label("🛒  商品一覧  ─  PRODUCTS"))

        self.product_list = QListWidget()
        self.product_list.setFont(QFont("Segoe UI", 15))

        for name, price in PRODUCTS.items():
            item = QListWidgetItem(f"  {name}     ¥{price:,}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setSizeHint(QSize(0, 52))
            if name in AGE_RESTRICTED:
                item.setBackground(QColor(COLORS["restricted_bg"]))
                item.setForeground(QColor(COLORS["restricted_fg"]))
            else:
                item.setBackground(QColor(COLORS["normal_bg"]))
                item.setForeground(QColor(COLORS["normal_fg"]))
            self.product_list.addItem(item)

        add_btn = make_btn(
            "＋  カートに追加", COLORS["accent"], COLORS["accent_hover"], COLORS["accent_pressed"])
        add_btn.clicked.connect(self._add_item)

        note = QLabel("🔴  赤い商品 = 年齢確認必要（お支払い時にカメラ＋NFC確認）")
        note.setFont(QFont("Segoe UI", 11))
        note.setWordWrap(True)
        note.setStyleSheet(
            f"color:{COLORS['text_muted']}; padding:6px 10px; background:transparent; border:none;")

        left_layout.addWidget(self.product_list)
        left_layout.addWidget(note)
        left_layout.addWidget(add_btn)

        # ── RIGHT: Cart ──
        right = make_panel()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(14)

        right_layout.addWidget(make_section_label("🧾  カート  ─  CART"))

        self.cart_list = QListWidget()
        self.cart_list.setFont(QFont("Segoe UI", 15))

        # Total
        total_frame = QFrame()
        total_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['list_bg']};
                border: 2px solid {COLORS['panel_border']};
                border-radius: 12px; padding: 4px;
            }}
        """)
        total_lay = QHBoxLayout(total_frame)
        total_lay.setContentsMargins(18, 14, 18, 14)

        total_lbl = QLabel("合計")
        total_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        total_lbl.setStyleSheet(
            f"color:{COLORS['text_dim']}; background:transparent; border:none;")

        self.total_value = QLabel("¥0")
        self.total_value.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.total_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.total_value.setStyleSheet(
            f"color:{COLORS['text_muted']}; background:transparent; border:none;")

        self.item_count = QLabel("(0 items)")
        self.item_count.setFont(QFont("Segoe UI", 12))
        self.item_count.setStyleSheet(
            f"color:{COLORS['text_muted']}; background:transparent; border:none;")

        self.restricted_indicator = QLabel("")
        self.restricted_indicator.setFont(QFont("Segoe UI", 11))
        self.restricted_indicator.setStyleSheet(
            f"color:{COLORS['danger']}; background:transparent; border:none;")

        total_lay.addWidget(total_lbl)
        total_lay.addWidget(self.item_count)
        total_lay.addStretch()
        total_lay.addWidget(self.restricted_indicator)
        total_lay.addWidget(self.total_value)

        # ── Payment button (changes dynamically) ──
        self.pay_btn = make_btn(
            "💳  お支払い",
            COLORS["success"], COLORS["success_hover"], COLORS["success_pressed"]
        )
        self.pay_btn.clicked.connect(self._process_payment)

        del_btn = make_btn(
            "✕  選択商品を削除", COLORS["danger"], COLORS["danger_hover"], COLORS["danger_pressed"])
        del_btn.clicked.connect(self._remove_item)

        clear_btn = make_btn(
            "🗑  カートを空にする",
            COLORS["text_muted"], COLORS["text_dim"], COLORS["text_muted"], bold=False
        )
        clear_btn.clicked.connect(self._clear_cart)

        right_layout.addWidget(self.cart_list)
        right_layout.addWidget(total_frame)
        right_layout.addWidget(del_btn)
        right_layout.addWidget(self.pay_btn)
        right_layout.addWidget(clear_btn)

        # ── BODY ──
        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(left, 1)
        body.addWidget(right, 1)

        # ── FOOTER ──
        footer = QLabel(
            "Powered by OpenCV DNN · PyQt6 · Camera + NFC verification at payment")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Segoe UI", 10))
        footer.setStyleSheet(f"color:{COLORS['text_muted']}; padding:8px;")

        root = QVBoxLayout()
        root.setContentsMargins(18, 14, 18, 10)
        root.setSpacing(16)
        root.addWidget(header)
        root.addLayout(body, 1)
        root.addWidget(footer)
        self.setLayout(root)

    # ================= CART =================
    def _add_item(self):
        item = self.product_list.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        price = PRODUCTS[name]

        self.cart.append({
            "name": name,
            "price": price,
            "restricted": name in AGE_RESTRICTED,
        })

        cart_item = QListWidgetItem(f"  {name}     ¥{price:,}")
        cart_item.setSizeHint(QSize(0, 48))
        if name in AGE_RESTRICTED:
            cart_item.setBackground(QColor(COLORS["restricted_bg"]))
            cart_item.setForeground(QColor(COLORS["restricted_fg"]))
        else:
            cart_item.setBackground(QColor(COLORS["cart_item_bg"]))
            cart_item.setForeground(QColor(COLORS["cart_item_fg"]))

        self.cart_list.addItem(cart_item)
        self._update_totals()
        logger.info(f"Added: {name} ¥{price}")

    def _remove_item(self):
        row = self.cart_list.currentRow()
        if row >= 0:
            removed = self.cart.pop(row)
            self.cart_list.takeItem(row)
            self._update_totals()
            logger.info(f"Removed: {removed['name']}")

    def _clear_cart(self):
        if not self.cart:
            return
        reply = QMessageBox.question(
            self, "確認", "カートを空にしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cart.clear()
            self.cart_list.clear()
            self._update_totals()

    def _update_totals(self):
        total = sum(i["price"] for i in self.cart)
        count = len(self.cart)
        restricted_count = sum(1 for i in self.cart if i["restricted"])

        self.total_value.setText(f"¥{total:,}")
        self.item_count.setText(f"({count} item{'s' if count != 1 else ''})")

        if restricted_count > 0:
            self.restricted_indicator.setText(f"🔴 年齢確認 ×{restricted_count}")
        else:
            self.restricted_indicator.setText("")

        color = COLORS['success'] if total > 0 else COLORS['text_muted']
        self.total_value.setStyleSheet(
            f"color:{color}; background:transparent; border:none;")

        # ── DYNAMIC PAYMENT BUTTON ──
        if restricted_count > 0:
            # Change to NFC scan style
            self.pay_btn.setText("🪪  IDスキャンでお支払い")
            self.pay_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['nfc_blue']},
                        stop:1 {COLORS['info']}
                    );
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 16px 24px;
                    font-size: 15px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['nfc_blue_hover']},
                        stop:1 {COLORS['info_hover']}
                    );
                }}
                QPushButton:pressed {{
                    background: {COLORS['nfc_blue_pressed']};
                }}
                QPushButton:disabled {{
                    background: {COLORS['text_muted']};
                    color: {COLORS['panel']};
                }}
            """)
        else:
            # Normal payment button
            self.pay_btn.setText("💳  お支払い")
            self.pay_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['success']};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 16px 24px;
                    font-size: 15px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background: {COLORS['success_hover']};
                }}
                QPushButton:pressed {{
                    background: {COLORS['success_pressed']};
                }}
                QPushButton:disabled {{
                    background: {COLORS['text_muted']};
                    color: {COLORS['panel']};
                }}
            """)

    # ================= PAYMENT FLOW =================
    def _process_payment(self):
        if not self.cart:
            QMessageBox.information(self, "カート", "カートが空です")
            return

        has_restricted = any(i["restricted"] for i in self.cart)
        total = sum(i["price"] for i in self.cart)
        count = len(self.cart)

        if has_restricted:
            # ── STEP 1: Camera age check ──
            self.header_status.setText("●  年齢確認中...")
            self.header_status.setStyleSheet(
                f"color:{COLORS['warning']}; background:transparent; border:none;")

            cam_dialog = CameraVerificationDialog(self)
            cam_ok = cam_dialog.start_camera(self.face_cascade, self.age_net)

            if not cam_ok:
                QMessageBox.warning(self, "カメラエラー", "カメラを開けません")
                self._reset_header()
                return

            result = cam_dialog.exec()
            self._reset_header()

            if result != QDialog.DialogCode.Accepted:
                logger.info("Camera verification cancelled")
                return

            if cam_dialog.detected_age is None:
                QMessageBox.warning(self, "エラー", "顔を認識できませんでした")
                return

            # ── STEP 2: Check if age >= 25 (confident pass) ──
            if cam_dialog.detected_age >= CONFIDENT_AGE:
                # Clearly adult - direct payment
                logger.info(
                    f"Age verified by camera: {cam_dialog.detected_age_text} → direct payment")
                self._complete_payment(count, total)
                return

            # ── STEP 3: Under 25 → NFC ID scan required ──
            logger.info(
                f"Age uncertain: {cam_dialog.detected_age_text} → NFC scan required")

            self.header_status.setText("●  NFC スキャン中...")
            self.header_status.setStyleSheet(
                f"color:{COLORS['nfc_blue']}; background:transparent; border:none;")

            nfc_dialog = NFCScanDialog(cam_dialog.detected_age_text, self)
            nfc_result = nfc_dialog.exec()

            self._reset_header()

            if nfc_result != QDialog.DialogCode.Accepted:
                logger.info("NFC scan cancelled")
                return

            if nfc_dialog.verified_age is None:
                QMessageBox.warning(self, "エラー", "カードを認識できませんでした")
                return

            if nfc_dialog.verified_age < LEGAL_AGE:
                # Confirmed underage via NFC
                alert = UnderageAlertDialog(
                    nfc_dialog.verified_name,
                    nfc_dialog.verified_age,
                    self
                )
                alert.exec()
                logger.warning(
                    f"Underage blocked: {nfc_dialog.verified_name} ({nfc_dialog.verified_age})")
                return

            # NFC verified adult
            self._complete_payment(count, total, nfc_dialog.verified_name)

        else:
            # No restricted items - direct payment
            self._complete_payment(count, total)

    def _complete_payment(self, count, total, verified_name=None):
        self.header_status.setText("●  支払い完了!")
        self.header_status.setStyleSheet(
            f"color:{COLORS['success']}; background:transparent; border:none;")

        dialog = PaymentSuccessDialog(count, total, verified_name, self)
        dialog.exec()

        self.cart.clear()
        self.cart_list.clear()
        self._update_totals()
        self._reset_header()
        logger.info(
            f"Payment: ¥{total:,} ({count} items) verified={verified_name}")

    def _reset_header(self):
        self.header_status.setText("●  Ready")
        self.header_status.setStyleSheet(
            f"color:{COLORS['success']}; background:transparent; border:none;")

    def closeEvent(self, event):
        logger.info("Application closed")
        event.accept()


# ================= RUN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    QFontDatabase.addApplicationFont(":/fonts/NotoSansJP-Regular.otf")

    win = MyMart()
    if win._init_error:
        sys.exit(1)

    win.show()
    sys.exit(app.exec())
