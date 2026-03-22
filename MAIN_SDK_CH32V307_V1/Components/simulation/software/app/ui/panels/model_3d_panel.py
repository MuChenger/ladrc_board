from __future__ import annotations

import math
import struct
import time
from collections import deque
from pathlib import Path
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    import numpy as np
    import pyqtgraph.opengl as gl

    OPENGL_AVAILABLE = True
    OPENGL_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover
    np = None
    gl = None
    OPENGL_AVAILABLE = False
    OPENGL_IMPORT_ERROR = str(exc)


class AttitudeIndicatorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self.setFixedSize(150, 150)

    def set_angles(self, roll: float, pitch: float, yaw: float):
        self._roll = float(roll)
        self._pitch = float(pitch)
        self._yaw = float(yaw)
        self.update()

    def paintEvent(self, event):  # pragma: no cover - UI paint
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 92), 1))
        painter.setBrush(QtGui.QColor(10, 18, 30, 224))
        painter.drawRoundedRect(rect, 14, 14)

        title_rect = QtCore.QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 18)
        painter.setPen(QtGui.QColor(250, 252, 255, 235))
        title_font = QtGui.QFont("Microsoft YaHei", 9)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(title_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "XYZ 坐标")

        center = QtCore.QPointF(rect.center().x(), rect.center().y() + 12)
        radius = min(rect.width(), rect.height()) * 0.25

        outer_ring = QtCore.QRectF(center.x() - radius - 14, center.y() - radius - 14, (radius + 14) * 2, (radius + 14) * 2)
        inner_ring = QtCore.QRectF(center.x() - radius - 4, center.y() - radius - 4, (radius + 4) * 2, (radius + 4) * 2)
        painter.setPen(QtGui.QPen(QtGui.QColor(190, 214, 232, 82), 1.2))
        painter.setBrush(QtGui.QColor(18, 30, 44, 118))
        painter.drawEllipse(outer_ring)
        painter.setPen(QtGui.QPen(QtGui.QColor(224, 235, 245, 54), 1))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(inner_ring)

        tick_pen = QtGui.QPen(QtGui.QColor(214, 228, 240, 72), 1)
        painter.setPen(tick_pen)
        for angle_deg in range(0, 360, 30):
            angle = math.radians(angle_deg)
            r1 = radius + 8
            r2 = radius + 13
            p1 = QtCore.QPointF(center.x() + math.cos(angle) * r1, center.y() + math.sin(angle) * r1)
            p2 = QtCore.QPointF(center.x() + math.cos(angle) * r2, center.y() + math.sin(angle) * r2)
            painter.drawLine(p1, p2)

        self._draw_body_indicator(painter, center, radius * 0.9)

        axes = [
            ("X", QtGui.QColor("#ff7b7b"), np.array([1.0, 0.0, 0.0], dtype=float)),
            ("Y", QtGui.QColor("#78f09c"), np.array([0.0, 1.0, 0.0], dtype=float)),
            ("Z", QtGui.QColor("#7fc3ff"), np.array([0.0, 0.0, 1.0], dtype=float)),
        ]
        transformed = []
        for label, color, vec in axes:
            rotated = self._rotate_vector(vec)
            transformed.append((rotated[2], label, color, rotated))
        transformed.sort()

        axis_font = QtGui.QFont("Microsoft YaHei", 10)
        axis_font.setBold(True)
        painter.setFont(axis_font)
        for _, label, color, vec in transformed:
            end = QtCore.QPointF(center.x() + vec[0] * radius, center.y() - vec[1] * radius)
            alpha = int(140 + max(0.0, vec[2]) * 90)
            pen = QtGui.QPen(QtGui.QColor(color.red(), color.green(), color.blue(), alpha), 2.6)
            painter.setPen(pen)
            painter.drawLine(center, end)
            painter.setBrush(QtGui.QColor(color.red(), color.green(), color.blue(), min(255, alpha + 20)))
            painter.drawEllipse(end, 4.6, 4.6)
            text_pos = QtCore.QPointF(end.x() + 6, end.y() - 6)
            painter.drawText(text_pos, label)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(235, 243, 250, 210))
        painter.drawEllipse(center, 4.2, 4.2)
        painter.setBrush(QtGui.QColor(90, 108, 126, 200))
        painter.drawEllipse(center, 1.6, 1.6)

    def _draw_body_indicator(self, painter, center: QtCore.QPointF, scale: float):
        body_vertices = [
            np.array([-0.65, -0.26, -0.22], dtype=float),
            np.array([0.65, -0.26, -0.22], dtype=float),
            np.array([0.65, 0.26, -0.22], dtype=float),
            np.array([-0.65, 0.26, -0.22], dtype=float),
            np.array([-0.65, -0.26, 0.22], dtype=float),
            np.array([0.65, -0.26, 0.22], dtype=float),
            np.array([0.65, 0.26, 0.22], dtype=float),
            np.array([-0.65, 0.26, 0.22], dtype=float),
        ]
        top_float_left = [
            np.array([-0.45, 0.34, -0.08], dtype=float),
            np.array([0.42, 0.34, -0.08], dtype=float),
            np.array([0.42, 0.50, -0.08], dtype=float),
            np.array([-0.45, 0.50, -0.08], dtype=float),
            np.array([-0.45, 0.34, 0.10], dtype=float),
            np.array([0.42, 0.34, 0.10], dtype=float),
            np.array([0.42, 0.50, 0.10], dtype=float),
            np.array([-0.45, 0.50, 0.10], dtype=float),
        ]
        top_float_right = [
            np.array([-0.45, -0.50, -0.08], dtype=float),
            np.array([0.42, -0.50, -0.08], dtype=float),
            np.array([0.42, -0.34, -0.08], dtype=float),
            np.array([-0.45, -0.34, -0.08], dtype=float),
            np.array([-0.45, -0.50, 0.10], dtype=float),
            np.array([0.42, -0.50, 0.10], dtype=float),
            np.array([0.42, -0.34, 0.10], dtype=float),
            np.array([-0.45, -0.34, 0.10], dtype=float),
        ]

        faces = [
            ([4, 5, 6, 7], QtGui.QColor(138, 149, 161, 172)),
            ([0, 1, 2, 3], QtGui.QColor(58, 68, 80, 150)),
            ([0, 1, 5, 4], QtGui.QColor(98, 108, 120, 160)),
            ([1, 2, 6, 5], QtGui.QColor(118, 128, 140, 168)),
            ([2, 3, 7, 6], QtGui.QColor(92, 102, 114, 156)),
            ([3, 0, 4, 7], QtGui.QColor(78, 88, 100, 148)),
        ]
        float_faces = [
            ([4, 5, 6, 7], QtGui.QColor(74, 148, 214, 196)),
            ([0, 1, 2, 3], QtGui.QColor(40, 96, 152, 150)),
            ([0, 1, 5, 4], QtGui.QColor(58, 122, 186, 174)),
            ([1, 2, 6, 5], QtGui.QColor(84, 162, 226, 186)),
            ([2, 3, 7, 6], QtGui.QColor(58, 122, 186, 174)),
            ([3, 0, 4, 7], QtGui.QColor(40, 96, 152, 150)),
        ]

        all_faces = []
        for indices, color in faces:
            pts3 = [self._rotate_vector(body_vertices[i]) for i in indices]
            all_faces.append((sum(pt[2] for pt in pts3) / len(pts3), color, pts3))
        for verts in (top_float_left, top_float_right):
            for indices, color in float_faces:
                pts3 = [self._rotate_vector(verts[i]) for i in indices]
                all_faces.append((sum(pt[2] for pt in pts3) / len(pts3), color, pts3))

        all_faces.sort()
        painter.setPen(QtGui.QPen(QtGui.QColor(232, 238, 244, 34), 0.8))
        for _, color, pts3 in all_faces:
            poly = QtGui.QPolygonF([self._project_point(pt, center, scale) for pt in pts3])
            painter.setBrush(color)
            painter.drawPolygon(poly)

    def _project_point(self, vec, center: QtCore.QPointF, scale: float):
        perspective = 1.0 / (1.0 + (vec[2] + 1.2) * 0.30)
        return QtCore.QPointF(
            center.x() + vec[0] * scale * perspective,
            center.y() - vec[1] * scale * perspective,
        )

    def _rotate_vector(self, vec):
        roll = math.radians(self._roll)
        pitch = math.radians(self._pitch)
        yaw = math.radians(self._yaw)

        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)

        rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
        ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
        rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
        return rz @ ry @ rx @ vec


class Model3DPanel(QtWidgets.QGroupBox):
    TRAIL_MAX_POINTS = 240
    AXIS_LENGTH = 1.8
    AIRCRAFT_GROUND_OFFSET = 0.24
    SOFTWARE_ROOT = Path(__file__).resolve().parents[3]
    EXTERNAL_ROV_DIR = SOFTWARE_ROOT / "assets" / "models" / "rov"
    MODE_ORDER = ("attitude", "trajectory", "underwater")
    MODE_LABELS = {
        "attitude": "姿态模式",
        "trajectory": "轨迹模式",
        "underwater": "水下场景模式",
    }
    MODEL_LIBRARY = {
        "水下机器人": "rov",
        "飞行器": "aircraft",
        "通用载体": "generic",
    }

    def __init__(self, parent=None):
        super().__init__("3D 模型", parent)
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self._depth = 0.0
        self._depth_by_model = {"rov": 0.0, "aircraft": 0.0, "generic": 0.0}
        self._u_cmd = 0.0
        self._animation_phase = 0.0
        self._virtual_pos = np.zeros(3, dtype=float) if OPENGL_AVAILABLE else None
        self._trail_points = deque(maxlen=self.TRAIL_MAX_POINTS)
        self._last_update_time = time.monotonic()

        self._body_item = None
        self._nose_item = None
        self._left_fin_item = None
        self._right_fin_item = None
        self._top_fin_item = None
        self._trail_item = None
        self._shadow_item = None
        self._grid_item = None
        self._axes_items = []
        self._axis_label_items = []
        self._water_plane_item = None
        self._water_haze_upper_item = None
        self._water_haze_lower_item = None
        self._seafloor_item = None
        self._seafloor_marker_item = None
        self._bubble_item = None
        self._bubble_base = None
        self._particle_item = None
        self._particle_base = None
        self._rov_light_left = None
        self._rov_light_right = None
        self._external_rov_item = None
        self._external_rov_loaded = False
        self._external_rov_path = None
        self._external_model_roll = 0.0
        self._external_model_pitch = 90.0
        self._external_model_yaw = 0.0
        self._external_model_scale = 1.0
        self._external_model_color = QtGui.QColor("#bcc3cc")
        self._external_model_alpha = 0.98
        self._external_model_draw_edges = False
        self._default_rov_body_color = QtGui.QColor("#b8c2cb")
        self._default_rov_float_color = QtGui.QColor("#297fce")
        self._aircraft_body_color = QtGui.QColor("#b8c2cb")
        self._aircraft_accent_color = QtGui.QColor("#2f7fd1")
        self._generic_body_color = QtGui.QColor("#a9b5c1")
        self._generic_accent_color = QtGui.QColor("#2f7fd1")
        self._rov_procedural_items = []
        self._mode = "attitude"
        self._model_type = "rov"
        self._model_items = {}
        self._metric_labels = []
        self._scene_hud_labels = []
        self._scene_hud_title_label = None
        self._theme_palette = self._default_theme_palette()

        self._build()
        self.apply_theme(self._theme_palette)

    @staticmethod
    def _default_theme_palette() -> dict:
        return {
            "border_strong": "#bec8d2",
            "model_metric_bg": "rgba(248,251,255,0.96)",
            "model_metric_border": "#d5e1ec",
            "model_metric_text": "#1b3953",
            "model_view_border": "rgba(130,156,182,96)",
            "model_hud_bg": "rgba(18,30,44,178)",
            "model_hud_border": "rgba(255,255,255,74)",
            "model_hud_title": "rgba(245,248,252,232)",
            "model_hud_text": "rgba(226,234,242,215)",
            "model_backgrounds": {
                "aircraft": "#b9dcff",
                "trajectory": "#27425f",
                "underwater": "#4a6a86",
                "attitude": "#314a66",
            },
        }

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.metric_container = QtWidgets.QWidget()
        metric_grid = QtWidgets.QGridLayout(self.metric_container)
        metric_grid.setContentsMargins(0, 0, 0, 0)
        metric_grid.setHorizontalSpacing(6)
        metric_grid.setVerticalSpacing(6)
        self.roll_label = self._create_metric_label("滚转: -180.0°", compact=True)
        self.pitch_label = self._create_metric_label("俯仰: -180.0°", compact=True)
        self.yaw_label = self._create_metric_label("偏航: -180.0°", compact=True)
        self.depth_label = self._create_metric_label("垂向位置: -999.999")
        self.u_cmd_label = self._create_metric_label("控制输出: -999.999")
        metric_grid.addWidget(self.roll_label, 0, 0)
        metric_grid.addWidget(self.pitch_label, 0, 1)
        metric_grid.addWidget(self.yaw_label, 1, 0)
        metric_grid.addWidget(self.depth_label, 1, 1)
        metric_grid.addWidget(self.u_cmd_label, 2, 0, 1, 2)
        metric_grid.setColumnStretch(0, 1)
        metric_grid.setColumnStretch(1, 1)
        layout.addWidget(self.metric_container)

        self.toolbar_container = QtWidgets.QWidget()
        toolbar = QtWidgets.QHBoxLayout(self.toolbar_container)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.mode_combo = QtWidgets.QComboBox()
        self.model_combo = QtWidgets.QComboBox()
        self.mode_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.model_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        for label, value in self.MODEL_LIBRARY.items():
            self.model_combo.addItem(label, value)
        self._sync_mode_combo_labels()
        self.follow_cb = QtWidgets.QCheckBox("视角跟随")
        self.follow_cb.setChecked(True)
        self.action_menu_btn = QtWidgets.QToolButton()
        self.action_menu_btn.setText("3D 设置")
        self.action_menu_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.action_menu_btn.setMinimumWidth(self.fontMetrics().horizontalAdvance("3D 设置") + 38)
        self.action_menu = QtWidgets.QMenu(self.action_menu_btn)
        self.import_model_action = self.action_menu.addAction("导入 ROV 模型")
        self.use_default_action = self.action_menu.addAction("恢复默认 ROV 外形")
        self.action_menu.addSeparator()
        self.builtin_style_menu = self.action_menu.addMenu("内置模型配色")
        self.choose_builtin_primary_action = self.builtin_style_menu.addAction("主体颜色...")
        self.choose_builtin_accent_action = self.builtin_style_menu.addAction("强调色...")
        self.reset_builtin_colors_action = self.builtin_style_menu.addAction("重置内置配色")
        self.external_style_menu = self.action_menu.addMenu("外部模型设置")
        self.external_pose_dialog_action = self.external_style_menu.addAction("姿态与缩放...")
        self.external_material_dialog_action = self.external_style_menu.addAction("外观与边线...")
        self.external_style_menu.addSeparator()
        self.reset_external_pose_action = self.external_style_menu.addAction("重置姿态")
        self.reset_external_material_action = self.external_style_menu.addAction("重置外观")
        self.action_menu.addSeparator()
        self.reset_view_action = self.action_menu.addAction("重置视角")
        self.clear_trail_action = self.action_menu.addAction("清空轨迹")
        self.action_menu_btn.setMenu(self.action_menu)
        toolbar.addWidget(QtWidgets.QLabel("模型库"))
        toolbar.addWidget(self.model_combo)
        toolbar.addWidget(QtWidgets.QLabel("场景模式"))
        toolbar.addWidget(self.mode_combo)
        toolbar.addWidget(self.follow_cb)
        toolbar.addWidget(self.action_menu_btn)
        toolbar.addStretch(1)
        layout.addWidget(self.toolbar_container)

        self.model_hint_label = QtWidgets.QLabel("")
        self.model_hint_label.setWordWrap(True)
        layout.addWidget(self.model_hint_label)

        self.settings_bar_widget = QtWidgets.QWidget()
        self.settings_combo = QtWidgets.QComboBox()
        self.settings_combo.addItem("内置模型配色", "builtin")
        self.settings_combo.addItem("外部模型姿态", "external_pose")
        self.settings_combo.addItem("外部模型外观", "external_material")
        settings_bar = QtWidgets.QHBoxLayout(self.settings_bar_widget)
        settings_bar.setContentsMargins(0, 0, 0, 0)
        settings_bar.setSpacing(8)
        settings_bar.addWidget(QtWidgets.QLabel("选项面板"))
        settings_bar.addWidget(self.settings_combo)
        settings_bar.addStretch(1)
        layout.addWidget(self.settings_bar_widget)

        self.settings_stack = QtWidgets.QStackedWidget()

        builtin_page = QtWidgets.QWidget()
        builtin_layout = QtWidgets.QHBoxLayout(builtin_page)
        builtin_layout.setContentsMargins(0, 0, 0, 0)
        builtin_layout.setSpacing(8)
        self.default_color_group_label = QtWidgets.QLabel("内置模型")
        self.default_body_color_btn = QtWidgets.QPushButton("主体颜色")
        self.default_float_color_btn = QtWidgets.QPushButton("强调色")
        self.reset_default_colors_btn = QtWidgets.QPushButton("重置内置配色")
        builtin_layout.addWidget(self.default_color_group_label)
        builtin_layout.addWidget(self.default_body_color_btn)
        builtin_layout.addWidget(self.default_float_color_btn)
        builtin_layout.addWidget(self.reset_default_colors_btn)
        builtin_layout.addStretch(1)
        self.settings_stack.addWidget(builtin_page)

        external_pose_page = QtWidgets.QWidget()
        adjust_row = QtWidgets.QHBoxLayout(external_pose_page)
        adjust_row.setContentsMargins(0, 0, 0, 0)
        adjust_row.setSpacing(8)
        self.model_roll_spin = QtWidgets.QDoubleSpinBox()
        self.model_roll_spin.setRange(-180.0, 180.0)
        self.model_roll_spin.setDecimals(1)
        self.model_roll_spin.setSingleStep(5.0)
        self.model_roll_spin.setValue(self._external_model_roll)
        self.model_pitch_spin = QtWidgets.QDoubleSpinBox()
        self.model_pitch_spin.setRange(-180.0, 180.0)
        self.model_pitch_spin.setDecimals(1)
        self.model_pitch_spin.setSingleStep(5.0)
        self.model_pitch_spin.setValue(self._external_model_pitch)
        self.model_yaw_spin = QtWidgets.QDoubleSpinBox()
        self.model_yaw_spin.setRange(-180.0, 180.0)
        self.model_yaw_spin.setDecimals(1)
        self.model_yaw_spin.setSingleStep(5.0)
        self.model_yaw_spin.setValue(self._external_model_yaw)
        self.model_scale_spin = QtWidgets.QDoubleSpinBox()
        self.model_scale_spin.setRange(0.1, 10.0)
        self.model_scale_spin.setDecimals(2)
        self.model_scale_spin.setSingleStep(0.05)
        self.model_scale_spin.setValue(self._external_model_scale)
        self.reset_model_pose_btn = QtWidgets.QPushButton("重置模型姿态")
        adjust_row.addWidget(QtWidgets.QLabel("模型滚转"))
        adjust_row.addWidget(self.model_roll_spin)
        adjust_row.addWidget(QtWidgets.QLabel("模型俯仰"))
        adjust_row.addWidget(self.model_pitch_spin)
        adjust_row.addWidget(QtWidgets.QLabel("模型偏航"))
        adjust_row.addWidget(self.model_yaw_spin)
        adjust_row.addWidget(QtWidgets.QLabel("模型缩放"))
        adjust_row.addWidget(self.model_scale_spin)
        adjust_row.addWidget(self.reset_model_pose_btn)
        adjust_row.addStretch(1)
        self.settings_stack.addWidget(external_pose_page)

        external_material_page = QtWidgets.QWidget()
        material_row = QtWidgets.QHBoxLayout(external_material_page)
        material_row.setContentsMargins(0, 0, 0, 0)
        material_row.setSpacing(8)
        self.model_color_btn = QtWidgets.QPushButton("模型颜色")
        self.model_alpha_spin = QtWidgets.QDoubleSpinBox()
        self.model_alpha_spin.setRange(0.10, 1.00)
        self.model_alpha_spin.setDecimals(2)
        self.model_alpha_spin.setSingleStep(0.05)
        self.model_alpha_spin.setValue(self._external_model_alpha)
        self.model_edges_cb = QtWidgets.QCheckBox("显示边线")
        self.model_edges_cb.setChecked(self._external_model_draw_edges)
        self.reset_model_material_btn = QtWidgets.QPushButton("重置外观")
        material_row.addWidget(self.model_color_btn)
        material_row.addWidget(QtWidgets.QLabel("透明度"))
        material_row.addWidget(self.model_alpha_spin)
        material_row.addWidget(self.model_edges_cb)
        material_row.addWidget(self.reset_model_material_btn)
        material_row.addStretch(1)
        self.settings_stack.addWidget(external_material_page)
        layout.addWidget(self.settings_stack)

        if not OPENGL_AVAILABLE:
            note = QtWidgets.QLabel(f"当前环境缺少 3D 渲染依赖，无法显示模型。\n原因: {OPENGL_IMPORT_ERROR}")
            note.setWordWrap(True)
            layout.addWidget(note)
            return

        self.view = gl.GLViewWidget()
        self.view.setMinimumHeight(320)
        self.view.setBackgroundColor("#22364c")
        self.view.setStyleSheet("border: 1px solid rgba(210, 228, 242, 70); border-radius: 12px;")

        self.view_container = QtWidgets.QWidget()
        view_layout = QtWidgets.QVBoxLayout(self.view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.addWidget(self.view)

        self.scene_hud_card = self._build_scene_hud_widget()
        self.scene_hud_card.setParent(self.view_container)
        self.scene_hud_card.raise_()

        self.view_container.installEventFilter(self)

        layout.addWidget(self.view_container, 1)

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.settings_combo.currentIndexChanged.connect(self._on_settings_panel_changed)
        self.import_model_action.triggered.connect(self.import_rov_model)
        self.use_default_action.triggered.connect(self.use_default_rov_model)
        self.choose_builtin_primary_action.triggered.connect(self._choose_default_body_color)
        self.choose_builtin_accent_action.triggered.connect(self._choose_default_float_color)
        self.reset_builtin_colors_action.triggered.connect(self._reset_default_rov_colors)
        self.external_pose_dialog_action.triggered.connect(self.open_external_pose_dialog)
        self.external_material_dialog_action.triggered.connect(self.open_external_material_dialog)
        self.reset_external_pose_action.triggered.connect(self._reset_external_model_adjust)
        self.reset_external_material_action.triggered.connect(self._reset_external_model_material)
        self.model_roll_spin.valueChanged.connect(self._on_external_model_adjust_changed)
        self.model_pitch_spin.valueChanged.connect(self._on_external_model_adjust_changed)
        self.model_yaw_spin.valueChanged.connect(self._on_external_model_adjust_changed)
        self.model_scale_spin.valueChanged.connect(self._on_external_model_adjust_changed)
        self.reset_model_pose_btn.clicked.connect(self._reset_external_model_adjust)
        self.model_color_btn.clicked.connect(self._choose_external_model_color)
        self.model_alpha_spin.valueChanged.connect(self._on_external_model_material_changed)
        self.model_edges_cb.toggled.connect(self._on_external_model_material_changed)
        self.reset_model_material_btn.clicked.connect(self._reset_external_model_material)
        self.default_body_color_btn.clicked.connect(self._choose_default_body_color)
        self.default_float_color_btn.clicked.connect(self._choose_default_float_color)
        self.reset_default_colors_btn.clicked.connect(self._reset_default_rov_colors)
        self.reset_view_action.triggered.connect(self.reset_view)
        self.clear_trail_action.triggered.connect(self.clear_trail)

        self._add_scene()
        self._apply_mode_style()
        self.reset_view()
        self._update_labels()
        self._update_model_hint()
        self._update_scene_hud()
        self._sync_external_model_material_controls()
        self._sync_builtin_color_controls()
        self._apply_builtin_model_colors()
        self._on_settings_panel_changed()
        self._update_external_control_state()
        self._position_overlay_widgets()
        self._update_model_transform()

    def set_embedded_controls_visible(self, visible: bool):
        for widget in (
            getattr(self, "toolbar_container", None),
            getattr(self, "model_hint_label", None),
            getattr(self, "settings_bar_widget", None),
            getattr(self, "settings_stack", None),
        ):
            if widget is not None:
                widget.setVisible(visible)

    def _create_metric_label(self, sample_text: str, compact: bool = False):
        label = QtWidgets.QLabel(sample_text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setMinimumHeight(30 if compact else 32)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        label.setStyleSheet(self._metric_label_stylesheet())
        self._metric_labels.append(label)
        return label

    def _build_scene_hud_widget(self):
        box = QtWidgets.QFrame()
        box.setStyleSheet(self._scene_hud_card_stylesheet())
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        title = QtWidgets.QLabel("场景信息")
        title.setStyleSheet(self._scene_hud_title_stylesheet())
        layout.addWidget(title)
        self._scene_hud_title_label = title

        self.scene_mode_label = QtWidgets.QLabel("模式: 姿态模式")
        self.scene_model_label = QtWidgets.QLabel("模型: 水下机器人")
        self.scene_depth_label = QtWidgets.QLabel("深度: 0.000")
        self.scene_output_label = QtWidgets.QLabel("输出: 0.000")
        for label in (
            self.scene_mode_label,
            self.scene_model_label,
            self.scene_depth_label,
            self.scene_output_label,
        ):
            label.setStyleSheet(self._scene_hud_text_stylesheet())
            self._scene_hud_labels.append(label)
            layout.addWidget(label)

        return box

    def _metric_label_stylesheet(self) -> str:
        return (
            "QLabel { background: %(bg)s; border: 1px solid %(border)s; "
            "border-radius: 10px; padding: 4px 8px; color: %(text)s; font-weight: 600; }"
            % {
                "bg": self._theme_palette["model_metric_bg"],
                "border": self._theme_palette["model_metric_border"],
                "text": self._theme_palette["model_metric_text"],
            }
        )

    def _scene_hud_card_stylesheet(self) -> str:
        return (
            "QFrame { background: %(bg)s; border: 1px solid %(border)s; border-radius: 12px; }"
            % {
                "bg": self._theme_palette["model_hud_bg"],
                "border": self._theme_palette["model_hud_border"],
            }
        )

    def _scene_hud_title_stylesheet(self) -> str:
        return "color: %s; font-weight: 700;" % self._theme_palette["model_hud_title"]

    def _scene_hud_text_stylesheet(self) -> str:
        return "color: %s;" % self._theme_palette["model_hud_text"]

    def _make_color_button_style(self, color: QtGui.QColor) -> str:
        text_color = "#111111" if color.lightness() > 128 else "#f3f4f6"
        return (
            "QPushButton { background-color: %(bg)s; color: %(fg)s; "
            "border: 1px solid %(border)s; border-radius: 6px; padding: 5px 10px; }"
            % {
                "bg": color.name(),
                "fg": text_color,
                "border": self._theme_palette.get("border_strong", "#bec8d2"),
            }
        )

    def apply_theme(self, theme: dict):
        self._theme_palette = {**self._default_theme_palette(), **(theme or {})}

        for label in self._metric_labels:
            label.setStyleSheet(self._metric_label_stylesheet())
        if hasattr(self, "scene_hud_card"):
            self.scene_hud_card.setStyleSheet(self._scene_hud_card_stylesheet())
        if self._scene_hud_title_label is not None:
            self._scene_hud_title_label.setStyleSheet(self._scene_hud_title_stylesheet())
        for label in self._scene_hud_labels:
            label.setStyleSheet(self._scene_hud_text_stylesheet())
        if OPENGL_AVAILABLE and hasattr(self, "view"):
            self.view.setStyleSheet(
                "border: 1px solid %s; border-radius: 12px;" % self._theme_palette["model_view_border"]
            )
        self._sync_external_model_material_controls()
        self._sync_builtin_color_controls()
        if OPENGL_AVAILABLE:
            self._apply_mode_style()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "view_container", None) and event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show):
            self._position_overlay_widgets()
        return super().eventFilter(obj, event)

    def _position_overlay_widgets(self):
        if not hasattr(self, "view_container"):
            return
        margin = 12
        if hasattr(self, "scene_hud_card"):
            self.scene_hud_card.adjustSize()
            self.scene_hud_card.move(margin, margin)
    def _add_scene(self):
        self._grid_item = gl.GLGridItem()
        self._grid_item.scale(1.0, 1.0, 1.0)
        self._grid_item.setSize(x=20, y=20)
        self._grid_item.setColor((0.72, 0.84, 0.96, 0.24))
        self.view.addItem(self._grid_item)

        self._add_axes()
        self._add_environment()
        self._add_rov_model()

        self._add_aircraft_model()
        self._add_generic_model()

        self._trail_item = gl.GLLinePlotItem(
            pos=np.zeros((0, 3), dtype=float),
            color=(0.48, 0.86, 1.0, 0.95),
            width=2,
            antialias=True,
        )
        self.view.addItem(self._trail_item)

        self._depth_guide_item = gl.GLLinePlotItem(
            pos=np.zeros((2, 3), dtype=float),
            color=(0.44, 0.88, 1.0, 0.85),
            width=3,
            antialias=True,
        )
        self.view.addItem(self._depth_guide_item)

        self._shadow_item = gl.GLScatterPlotItem(
            pos=np.zeros((1, 3), dtype=float),
            color=(0.95, 0.95, 0.95, 0.55),
            size=10,
            pxMode=True,
        )
        self.view.addItem(self._shadow_item)

    def _add_axes(self):
        axis_length = self.AXIS_LENGTH
        axes = [
            (np.array([[0, 0, 0], [axis_length, 0, 0]], dtype=float), (1.0, 0.35, 0.35, 0.95)),
            (np.array([[0, 0, 0], [0, axis_length, 0]], dtype=float), (0.35, 1.0, 0.45, 0.95)),
            (np.array([[0, 0, 0], [0, 0, axis_length]], dtype=float), (0.35, 0.72, 1.0, 0.95)),
        ]
        for pos, color in axes:
            item = gl.GLLinePlotItem(pos=pos, color=color, width=3, antialias=True)
            self.view.addItem(item)
            self._axes_items.append(item)

    def _add_environment(self):
        self._water_plane_item = None
        self._water_haze_upper_item = None
        self._water_haze_lower_item = None

        self._air_ground_item = gl.GLMeshItem(
            meshdata=self._create_plane_mesh(size_x=28.0, size_y=28.0, z=0.0),
            smooth=True,
            drawEdges=False,
            edgeColor=(0.76, 0.88, 0.70, 0.08),
            color=(0.72, 0.82, 0.64, 0.94),
            shader="shaded",
        )
        self.view.addItem(self._air_ground_item)

        self._air_runway_item = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=12.0, width=2.8, height=0.04, chamfer=0.02),
            smooth=True,
            drawEdges=False,
            color=(0.82, 0.84, 0.86, 0.98),
            shader="shaded",
        )
        self._air_runway_item.translate(0.0, 0.0, 0.02)
        self.view.addItem(self._air_runway_item)

        self._air_runway_stripe_item = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=7.0, width=0.18, height=0.02, chamfer=0.01),
            smooth=True,
            drawEdges=False,
            color=(0.98, 0.98, 0.97, 0.98),
            shader="shaded",
        )
        self._air_runway_stripe_item.translate(0.0, 0.0, 0.05)
        self.view.addItem(self._air_runway_stripe_item)

        self._seafloor_item = gl.GLMeshItem(
            meshdata=self._create_terrain_mesh(size_x=24.0, size_y=24.0, base_z=-3.35, steps=18),
            smooth=True,
            drawEdges=False,
            edgeColor=(0.90, 0.82, 0.66, 0.10),
            color=(0.82, 0.74, 0.58, 0.92),
            shader="shaded",
        )
        self.view.addItem(self._seafloor_item)

        self._seafloor_marker_item = None

        self._bubble_base = None
        self._bubble_item = None
        self._particle_base = None
        self._particle_item = None

    def reset_view(self):
        if not OPENGL_AVAILABLE:
            return
        center = self._virtual_pos if self._virtual_pos is not None else np.zeros(3, dtype=float)
        distance, elevation, azimuth, follow, center_z_bias = self._get_view_preset()
        self.view.opts["distance"] = distance
        self.view.opts["elevation"] = elevation
        self.view.opts["azimuth"] = azimuth
        self.follow_cb.setChecked(follow)
        self.view.opts["center"] = self._make_vector(center[0], center[1], center[2] + center_z_bias)
        self.view.update()

    def _get_view_preset(self):
        if self._mode == "trajectory":
            return 22, 76, -18, False, -0.15
        if self._mode == "underwater":
            if self._model_type == "aircraft":
                return 17, 12, -30, True, -0.05
            if self._model_type == "generic":
                return 16, 14, 28, True, -0.10
            return 16, 20, 44, True, -0.18

        if self._model_type == "aircraft":
            return 15, 18, -36, True, 0.00
        if self._model_type == "generic":
            return 14, 20, 32, True, -0.02
        return 14, 18, 52, True, -0.10

    def clear_trail(self):
        self._trail_points.clear()
        self._virtual_pos = np.zeros(3, dtype=float)
        if OPENGL_AVAILABLE and self._trail_item is not None:
            self._trail_item.setData(pos=np.zeros((0, 3), dtype=float))
        self._update_model_transform()

    def set_follow_enabled(self, enabled: bool):
        self.follow_cb.setChecked(enabled)

    def is_follow_enabled(self) -> bool:
        return self.follow_cb.isChecked()

    def get_status_summary(self) -> str:
        model_text = self.model_combo.currentText() if hasattr(self, "model_combo") else "3D 模型"
        mode_text = self.mode_combo.currentText() if hasattr(self, "mode_combo") else "姿态模式"
        if self._model_type == "rov" and self._external_rov_loaded and self._external_rov_path is not None:
            source_text = f"外部模型: {self._external_rov_path.name}"
        elif self._model_type == "rov":
            source_text = "系统默认 ROV"
        else:
            source_text = "系统内置模型"
        return f"3D 场景: {model_text} / {mode_text} / {source_text}"

    def current_model_type(self) -> str:
        return self._model_type

    def get_state(self) -> dict:
        return {
            "model_type": self._model_type,
            "mode": self._mode,
            "follow": self.follow_cb.isChecked(),
            "settings_page": self.settings_combo.currentData() if hasattr(self, "settings_combo") else "builtin",
            "builtin_colors": {
                "rov_body": self._default_rov_body_color.name(),
                "rov_accent": self._default_rov_float_color.name(),
                "aircraft_body": self._aircraft_body_color.name(),
                "aircraft_accent": self._aircraft_accent_color.name(),
                "generic_body": self._generic_body_color.name(),
                "generic_accent": self._generic_accent_color.name(),
            },
            "external_model": {
                "enabled": bool(self._external_rov_loaded),
                "path": str(self._external_rov_path) if self._external_rov_path is not None else "",
                "roll": float(self._external_model_roll),
                "pitch": float(self._external_model_pitch),
                "yaw": float(self._external_model_yaw),
                "scale": float(self._external_model_scale),
                "color": self._external_model_color.name(),
                "alpha": float(self._external_model_alpha),
                "draw_edges": bool(self._external_model_draw_edges),
            },
        }

    def apply_state(self, state: dict):
        if not isinstance(state, dict):
            return

        builtin_colors = state.get("builtin_colors")
        if isinstance(builtin_colors, dict):
            for attr_name, key in (
                ("_default_rov_body_color", "rov_body"),
                ("_default_rov_float_color", "rov_accent"),
                ("_aircraft_body_color", "aircraft_body"),
                ("_aircraft_accent_color", "aircraft_accent"),
                ("_generic_body_color", "generic_body"),
                ("_generic_accent_color", "generic_accent"),
            ):
                color_value = builtin_colors.get(key)
                color = QtGui.QColor(str(color_value))
                if color.isValid():
                    setattr(self, attr_name, color)
            self._sync_builtin_color_controls()
            self._apply_builtin_model_colors()

        model_type = state.get("model_type")
        if model_type is not None:
            index = self.model_combo.findData(model_type)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

        external_state = state.get("external_model")
        if isinstance(external_state, dict):
            color = QtGui.QColor(str(external_state.get("color", "")))
            if color.isValid():
                self._external_model_color = color
            try:
                self.model_roll_spin.setValue(float(external_state.get("roll", self._external_model_roll)))
                self.model_pitch_spin.setValue(float(external_state.get("pitch", self._external_model_pitch)))
                self.model_yaw_spin.setValue(float(external_state.get("yaw", self._external_model_yaw)))
                self.model_scale_spin.setValue(float(external_state.get("scale", self._external_model_scale)))
                self.model_alpha_spin.setValue(float(external_state.get("alpha", self._external_model_alpha)))
            except (TypeError, ValueError):
                pass
            self.model_edges_cb.setChecked(bool(external_state.get("draw_edges", self._external_model_draw_edges)))
            self._sync_external_model_material_controls()

            external_enabled = bool(external_state.get("enabled"))
            external_path = str(external_state.get("path", "")).strip()
            if external_enabled and external_path:
                path = Path(external_path)
                if path.exists():
                    self._set_external_rov_model(path)
                else:
                    self.use_default_rov_model()
            elif not external_enabled:
                self.use_default_rov_model()

        mode_key = state.get("mode")
        if mode_key is not None:
            index = self.mode_combo.findData(mode_key)
            if index >= 0:
                self.mode_combo.setCurrentIndex(index)

        if "follow" in state:
            self.follow_cb.setChecked(bool(state.get("follow")))

        settings_page = state.get("settings_page")
        if settings_page is not None and hasattr(self, "settings_combo"):
            index = self.settings_combo.findData(settings_page)
            if index >= 0:
                self.settings_combo.setCurrentIndex(index)

        self._sync_builtin_color_controls()
        self._apply_builtin_model_colors()
        self._sync_external_model_material_controls()
        self._update_external_control_state()
        self._update_model_hint()
        self._update_scene_hud()

    def reset_to_defaults(self):
        model_index = self.model_combo.findData("rov")
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        self._mode = "attitude"
        mode_index = self.mode_combo.findData("attitude")
        if mode_index >= 0:
            self.mode_combo.setCurrentIndex(mode_index)
        self.follow_cb.setChecked(True)
        settings_index = self.settings_combo.findData("builtin")
        if settings_index >= 0:
            self.settings_combo.setCurrentIndex(settings_index)
        self._default_rov_body_color = QtGui.QColor("#b8c2cb")
        self._default_rov_float_color = QtGui.QColor("#297fce")
        self._aircraft_body_color = QtGui.QColor("#b8c2cb")
        self._aircraft_accent_color = QtGui.QColor("#2f7fd1")
        self._generic_body_color = QtGui.QColor("#a9b5c1")
        self._generic_accent_color = QtGui.QColor("#2f7fd1")
        self._reset_external_model_adjust()
        self._reset_external_model_material()
        self.use_default_rov_model()
        self._sync_builtin_color_controls()
        self._apply_builtin_model_colors()
        self.clear_trail()
        self.reset_view()

    def vertical_metric_label(self) -> str:
        if self._model_type == "aircraft":
            return "高度"
        if self._model_type == "generic":
            return "垂向位置"
        return "深度"

    def vertical_rate_metric_label(self) -> str:
        if self._model_type == "aircraft":
            return "高度变化率"
        if self._model_type == "generic":
            return "垂向速度"
        return "深度变化率"

    def _on_mode_changed(self):
        self._mode = self.mode_combo.currentData()
        self._apply_mode_style()
        self._update_scene_hud()
        self.reset_view()
        self._update_model_transform()

    def _on_model_changed(self):
        previous_model = self._model_type
        self._depth_by_model[previous_model] = float(self._depth)
        self._model_type = self.model_combo.currentData()
        self._depth = float(self._depth_by_model.get(self._model_type, 0.0))
        self.clear_trail()
        self._sync_mode_combo_labels()
        self._apply_mode_style()
        self._apply_model_visibility()
        self._sync_builtin_color_controls()
        self._update_labels()
        self._update_scene_hud()
        self._update_model_hint()
        self.reset_view()
        self._update_model_transform()

    def _on_settings_panel_changed(self):
        page_key = self.settings_combo.currentData() if hasattr(self, "settings_combo") else "builtin"
        page_index = {
            "builtin": 0,
            "external_pose": 1,
            "external_material": 2,
        }.get(page_key, 0)
        if hasattr(self, "settings_stack"):
            self.settings_stack.setCurrentIndex(page_index)

    def _get_mode_display_label(self, mode_value: str):
        if self._model_type == "aircraft" and mode_value == "underwater":
            return "空中场景模式"
        return self.MODE_LABELS.get(mode_value, mode_value)

    def _sync_mode_combo_labels(self):
        if not hasattr(self, "mode_combo"):
            return
        current_mode = self.mode_combo.currentData() if self.mode_combo.count() else self._mode
        blocker = QtCore.QSignalBlocker(self.mode_combo)
        self.mode_combo.clear()
        for mode_value in self.MODE_ORDER:
            self.mode_combo.addItem(self._get_mode_display_label(mode_value), mode_value)
        target_index = self.mode_combo.findData(current_mode)
        if target_index < 0:
            target_index = 0
        self.mode_combo.setCurrentIndex(target_index)
        self._mode = self.mode_combo.currentData()
        del blocker

    def _on_external_model_adjust_changed(self):
        self._external_model_roll = float(self.model_roll_spin.value())
        self._external_model_pitch = float(self.model_pitch_spin.value())
        self._external_model_yaw = float(self.model_yaw_spin.value())
        self._external_model_scale = float(self.model_scale_spin.value())
        self._update_model_transform()

    def _reset_external_model_adjust(self):
        self.model_roll_spin.setValue(0.0)
        self.model_pitch_spin.setValue(90.0)
        self.model_yaw_spin.setValue(0.0)
        self.model_scale_spin.setValue(1.0)

    def _on_external_model_material_changed(self):
        self._external_model_alpha = float(self.model_alpha_spin.value())
        self._external_model_draw_edges = bool(self.model_edges_cb.isChecked())
        self._apply_external_model_material()

    def _choose_external_model_color(self):
        color = QtWidgets.QColorDialog.getColor(self._external_model_color, self, "选择模型颜色")
        if not color.isValid():
            return
        self._external_model_color = color
        self._sync_external_model_material_controls()
        self._apply_external_model_material()

    def _reset_external_model_material(self):
        self._external_model_color = QtGui.QColor("#bcc3cc")
        self._external_model_alpha = 0.98
        self._external_model_draw_edges = False
        self.model_alpha_spin.setValue(self._external_model_alpha)
        self.model_edges_cb.setChecked(self._external_model_draw_edges)
        self._sync_external_model_material_controls()
        self._apply_external_model_material()

    def open_external_pose_dialog(self):
        if not (self._model_type == "rov" and self._external_rov_loaded):
            QtWidgets.QMessageBox.information(self, "提示", "请先切换到水下机器人，并导入外部模型后再调整姿态。")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("外部模型姿态")
        dialog.setModal(True)
        layout = QtWidgets.QVBoxLayout(dialog)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        roll_spin = QtWidgets.QDoubleSpinBox()
        roll_spin.setRange(-180.0, 180.0)
        roll_spin.setDecimals(1)
        roll_spin.setSingleStep(5.0)
        roll_spin.setValue(self._external_model_roll)

        pitch_spin = QtWidgets.QDoubleSpinBox()
        pitch_spin.setRange(-180.0, 180.0)
        pitch_spin.setDecimals(1)
        pitch_spin.setSingleStep(5.0)
        pitch_spin.setValue(self._external_model_pitch)

        yaw_spin = QtWidgets.QDoubleSpinBox()
        yaw_spin.setRange(-180.0, 180.0)
        yaw_spin.setDecimals(1)
        yaw_spin.setSingleStep(5.0)
        yaw_spin.setValue(self._external_model_yaw)

        scale_spin = QtWidgets.QDoubleSpinBox()
        scale_spin.setRange(0.10, 10.0)
        scale_spin.setDecimals(2)
        scale_spin.setSingleStep(0.05)
        scale_spin.setValue(self._external_model_scale)

        form.addRow("模型滚转", roll_spin)
        form.addRow("模型俯仰", pitch_spin)
        form.addRow("模型偏航", yaw_spin)
        form.addRow("模型缩放", scale_spin)
        layout.addLayout(form)

        reset_btn = QtWidgets.QPushButton("恢复推荐值")

        def reset_values():
            roll_spin.setValue(0.0)
            pitch_spin.setValue(90.0)
            yaw_spin.setValue(0.0)
            scale_spin.setValue(1.0)

        reset_btn.clicked.connect(reset_values)
        layout.addWidget(reset_btn, 0, QtCore.Qt.AlignLeft)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        self.model_roll_spin.setValue(roll_spin.value())
        self.model_pitch_spin.setValue(pitch_spin.value())
        self.model_yaw_spin.setValue(yaw_spin.value())
        self.model_scale_spin.setValue(scale_spin.value())

    def open_external_material_dialog(self):
        if not (self._model_type == "rov" and self._external_rov_loaded):
            QtWidgets.QMessageBox.information(self, "提示", "请先切换到水下机器人，并导入外部模型后再调整外观。")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("外部模型外观")
        dialog.setModal(True)
        layout = QtWidgets.QVBoxLayout(dialog)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        temp_color = QtGui.QColor(self._external_model_color)
        color_btn = QtWidgets.QPushButton("模型颜色")

        def sync_color_button():
            color_btn.setStyleSheet(
                "QPushButton { background-color: %s; color: %s; }"
                % (
                    temp_color.name(),
                    "#111111" if temp_color.lightness() > 128 else "#f3f4f6",
                )
            )

        def choose_color():
            nonlocal temp_color
            color = QtWidgets.QColorDialog.getColor(temp_color, dialog, "选择模型颜色")
            if not color.isValid():
                return
            temp_color = color
            sync_color_button()

        color_btn.clicked.connect(choose_color)
        sync_color_button()

        alpha_spin = QtWidgets.QDoubleSpinBox()
        alpha_spin.setRange(0.10, 1.00)
        alpha_spin.setDecimals(2)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(self._external_model_alpha)

        edges_cb = QtWidgets.QCheckBox("显示边线")
        edges_cb.setChecked(self._external_model_draw_edges)

        form.addRow("模型颜色", color_btn)
        form.addRow("透明度", alpha_spin)
        form.addRow("边线", edges_cb)
        layout.addLayout(form)

        reset_btn = QtWidgets.QPushButton("恢复默认外观")

        def reset_values():
            nonlocal temp_color
            temp_color = QtGui.QColor("#bcc3cc")
            alpha_spin.setValue(0.98)
            edges_cb.setChecked(False)
            sync_color_button()

        reset_btn.clicked.connect(reset_values)
        layout.addWidget(reset_btn, 0, QtCore.Qt.AlignLeft)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        self._external_model_color = temp_color
        self.model_alpha_spin.setValue(alpha_spin.value())
        self.model_edges_cb.setChecked(edges_cb.isChecked())
        self._sync_external_model_material_controls()
        self._apply_external_model_material()

    def _choose_default_body_color(self):
        current, title = self._get_builtin_color_targets(primary=True)
        color = QtWidgets.QColorDialog.getColor(current, self, title)
        if not color.isValid():
            return
        self._set_builtin_primary_color(color)

    def _choose_default_float_color(self):
        current, title = self._get_builtin_color_targets(primary=False)
        color = QtWidgets.QColorDialog.getColor(current, self, title)
        if not color.isValid():
            return
        self._set_builtin_accent_color(color)

    def _reset_default_rov_colors(self):
        if self._model_type == "aircraft":
            self._aircraft_body_color = QtGui.QColor("#b8c2cb")
            self._aircraft_accent_color = QtGui.QColor("#2f7fd1")
        elif self._model_type == "generic":
            self._generic_body_color = QtGui.QColor("#a9b5c1")
            self._generic_accent_color = QtGui.QColor("#2f7fd1")
        else:
            self._default_rov_body_color = QtGui.QColor("#b8c2cb")
            self._default_rov_float_color = QtGui.QColor("#297fce")
        self._sync_builtin_color_controls()
        self._apply_builtin_model_colors()

    def _get_builtin_color_targets(self, primary: bool):
        if self._model_type == "aircraft":
            return (
                (self._aircraft_body_color, "选择飞行器主体颜色")
                if primary
                else (self._aircraft_accent_color, "选择飞行器强调色")
            )
        if self._model_type == "generic":
            return (
                (self._generic_body_color, "选择通用载体主体颜色")
                if primary
                else (self._generic_accent_color, "选择通用载体强调色")
            )
        return (
            (self._default_rov_body_color, "选择机身颜色")
            if primary
            else (self._default_rov_float_color, "选择浮力块颜色")
        )

    def _set_builtin_primary_color(self, color: QtGui.QColor):
        if self._model_type == "aircraft":
            self._aircraft_body_color = color
        elif self._model_type == "generic":
            self._generic_body_color = color
        else:
            self._default_rov_body_color = color
        self._sync_builtin_color_controls()
        self._apply_builtin_model_colors()

    def _set_builtin_accent_color(self, color: QtGui.QColor):
        if self._model_type == "aircraft":
            self._aircraft_accent_color = color
        elif self._model_type == "generic":
            self._generic_accent_color = color
        else:
            self._default_rov_float_color = color
        self._sync_builtin_color_controls()
        self._apply_builtin_model_colors()

    def _create_box_mesh(self, length: float, width: float, height: float):
        lx = length / 2.0
        wy = width / 2.0
        hz = height / 2.0
        verts = np.array(
            [
                [-lx, -wy, -hz],
                [lx, -wy, -hz],
                [lx, wy, -hz],
                [-lx, wy, -hz],
                [-lx, -wy, hz],
                [lx, -wy, hz],
                [lx, wy, hz],
                [-lx, wy, hz],
            ],
            dtype=float,
        )
        faces = np.array(
            [
                [0, 1, 2],
                [0, 2, 3],
                [4, 6, 5],
                [4, 7, 6],
                [0, 4, 5],
                [0, 5, 1],
                [1, 5, 6],
                [1, 6, 2],
                [2, 6, 7],
                [2, 7, 3],
                [3, 7, 4],
                [3, 4, 0],
            ],
            dtype=int,
        )
        return gl.MeshData(vertexes=verts, faces=faces)

    def _create_chamfered_box_mesh(self, length: float, width: float, height: float, chamfer: float):
        lx = length / 2.0
        wy = width / 2.0
        hz = height / 2.0
        cut = max(0.0, min(chamfer, wy * 0.45, hz * 0.45))
        profile = [
            (-wy + cut, -hz),
            (wy - cut, -hz),
            (wy, -hz + cut),
            (wy, hz - cut),
            (wy - cut, hz),
            (-wy + cut, hz),
            (-wy, hz - cut),
            (-wy, -hz + cut),
        ]

        verts = []
        for x in (-lx, lx):
            for y, z in profile:
                verts.append([x, y, z])
        verts.append([-lx, 0.0, 0.0])
        verts.append([lx, 0.0, 0.0])

        faces = []
        for i in range(len(profile)):
            j = (i + 1) % len(profile)
            faces.append([i, j, 8 + j])
            faces.append([i, 8 + j, 8 + i])

        front_center = 16
        back_center = 17
        for i in range(len(profile)):
            j = (i + 1) % len(profile)
            faces.append([front_center, j, i])
            faces.append([back_center, 8 + i, 8 + j])

        return gl.MeshData(vertexes=np.array(verts, dtype=float), faces=np.array(faces, dtype=int))

    def _create_cylinder_mesh(self, length: float, radius: float, segments: int = 20):
        half = length / 2.0
        angles = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
        verts = []
        for x in (-half, half):
            for angle in angles:
                verts.append([x, math.cos(angle) * radius, math.sin(angle) * radius])
        verts.append([-half, 0.0, 0.0])
        verts.append([half, 0.0, 0.0])

        faces = []
        front_center = segments * 2
        rear_center = segments * 2 + 1
        for i in range(segments):
            j = (i + 1) % segments
            faces.append([i, j, segments + j])
            faces.append([i, segments + j, segments + i])
            faces.append([front_center, j, i])
            faces.append([rear_center, segments + i, segments + j])

        return gl.MeshData(vertexes=np.array(verts, dtype=float), faces=np.array(faces, dtype=int))

    def _create_nose_mesh(self, length: float, radius: float):
        verts = np.array(
            [
                [0.0, 0.0, 0.0],
                [length, 0.0, 0.0],
                [0.0, radius, radius],
                [0.0, -radius, radius],
                [0.0, -radius, -radius],
                [0.0, radius, -radius],
            ],
            dtype=float,
        )
        faces = np.array(
            [
                [0, 2, 3],
                [0, 3, 4],
                [0, 4, 5],
                [0, 5, 2],
                [1, 3, 2],
                [1, 4, 3],
                [1, 5, 4],
                [1, 2, 5],
            ],
            dtype=int,
        )
        return gl.MeshData(vertexes=verts, faces=faces)

    def _create_fin_mesh(self, length: float, span: float, thickness: float):
        tl = thickness / 2.0
        verts = np.array(
            [
                [0.0, 0.0, -tl],
                [0.0, 0.0, tl],
                [length, 0.0, -tl],
                [length, 0.0, tl],
                [0.15 * length, span, -tl],
                [0.15 * length, span, tl],
            ],
            dtype=float,
        )
        faces = np.array(
            [
                [0, 2, 4],
                [1, 5, 3],
                [0, 1, 3],
                [0, 3, 2],
                [2, 3, 5],
                [2, 5, 4],
                [4, 5, 1],
                [4, 1, 0],
            ],
            dtype=int,
        )
        return gl.MeshData(vertexes=verts, faces=faces)

    def _create_plane_mesh(self, size_x: float, size_y: float, z: float):
        sx = size_x / 2.0
        sy = size_y / 2.0
        verts = np.array(
            [
                [-sx, -sy, z],
                [sx, -sy, z],
                [sx, sy, z],
                [-sx, sy, z],
            ],
            dtype=float,
        )
        faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
        return gl.MeshData(vertexes=verts, faces=faces)

    def _create_terrain_mesh(self, size_x: float, size_y: float, base_z: float, steps: int):
        xs = np.linspace(-size_x / 2.0, size_x / 2.0, steps + 1)
        ys = np.linspace(-size_y / 2.0, size_y / 2.0, steps + 1)
        verts = []
        for y in ys:
            for x in xs:
                ripple = 0.22 * math.sin(x * 0.42) + 0.16 * math.cos(y * 0.55)
                mound = 0.28 * math.exp(-((x - 2.8) ** 2 + (y + 1.2) ** 2) / 18.0)
                trench = -0.24 * math.exp(-((x + 3.2) ** 2 + (y - 2.6) ** 2) / 14.0)
                z = base_z + ripple + mound + trench
                verts.append([x, y, z])

        faces = []
        row = steps + 1
        for iy in range(steps):
            for ix in range(steps):
                a = iy * row + ix
                b = a + 1
                c = a + row
                d = c + 1
                faces.append([a, b, d])
                faces.append([a, d, c])

        return gl.MeshData(vertexes=np.array(verts, dtype=float), faces=np.array(faces, dtype=int))

    def _register_model_item(self, model_type: str, item):
        self._model_items.setdefault(model_type, []).append(item)

    def _register_rov_procedural_item(self, item):
        self._rov_procedural_items.append(item)
        self._register_model_item("rov", item)

    def _create_blade_item(self, length: float, color):
        item = gl.GLLinePlotItem(
            pos=np.array([[-length / 2.0, 0.0, 0.0], [length / 2.0, 0.0, 0.0]], dtype=float),
            color=color,
            width=3,
            antialias=True,
        )
        return item

    def _create_line_item(self, points, color, width: int = 2):
        return gl.GLLinePlotItem(pos=np.array(points, dtype=float), color=color, width=width, antialias=True)

    def _create_ring_line_item(self, radius: float, color, points: int = 48):
        angles = np.linspace(0.0, 2.0 * math.pi, points)
        pos = np.stack(
            [np.cos(angles) * radius, np.sin(angles) * radius, np.zeros_like(angles)],
            axis=1,
        )
        return gl.GLLinePlotItem(pos=pos, color=color, width=2, antialias=True)

    def _load_obj_mesh(self, obj_path: Path):
        vertices = []
        faces = []
        for raw_line in obj_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith("f "):
                raw_face = line.split()[1:]
                face_indices = []
                for token in raw_face:
                    idx_text = token.split("/")[0]
                    if not idx_text:
                        continue
                    idx = int(idx_text)
                    idx = idx - 1 if idx > 0 else len(vertices) + idx
                    face_indices.append(idx)
                if len(face_indices) >= 3:
                    for i in range(1, len(face_indices) - 1):
                        faces.append([face_indices[0], face_indices[i], face_indices[i + 1]])

        return self._build_mesh_data(vertices, faces, "OBJ 文件中缺少有效的顶点或面数据")

    def _load_stl_mesh(self, stl_path: Path):
        raw = stl_path.read_bytes()
        if len(raw) < 84:
            raise ValueError("STL 文件过小或已损坏")

        expected_triangles = struct.unpack("<I", raw[80:84])[0]
        expected_size = 84 + expected_triangles * 50
        if expected_size == len(raw):
            vertices = []
            faces = []
            offset = 84
            for tri_index in range(expected_triangles):
                offset += 12  # skip normal
                tri_vertices = []
                for _ in range(3):
                    x, y, z = struct.unpack("<fff", raw[offset : offset + 12])
                    vertices.append([x, y, z])
                    tri_vertices.append(len(vertices) - 1)
                    offset += 12
                faces.append(tri_vertices)
                offset += 2  # skip attribute byte count
            return self._build_mesh_data(vertices, faces, "STL 文件中缺少有效的三角面数据")

        vertices = []
        faces = []
        for raw_line in raw.decode("utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if line.lower().startswith("vertex "):
                parts = line.split()
                if len(parts) >= 4:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    if len(vertices) % 3 == 0:
                        idx = len(vertices)
                        faces.append([idx - 3, idx - 2, idx - 1])
        return self._build_mesh_data(vertices, faces, "STL 文件中缺少有效的三角面数据")

    def _load_off_mesh(self, off_path: Path):
        lines = [line.strip() for line in off_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
        if not lines or lines[0] != "OFF":
            raise ValueError("OFF 文件头无效")
        if len(lines) < 2:
            raise ValueError("OFF 文件缺少尺寸信息")

        counts = lines[1].split()
        if len(counts) < 2:
            raise ValueError("OFF 文件尺寸信息无效")
        vertex_count = int(counts[0])
        face_count = int(counts[1])
        if len(lines) < 2 + vertex_count + face_count:
            raise ValueError("OFF 文件内容不完整")

        vertices = []
        for line in lines[2 : 2 + vertex_count]:
            parts = line.split()
            if len(parts) >= 3:
                vertices.append([float(parts[0]), float(parts[1]), float(parts[2])])

        faces = []
        for line in lines[2 + vertex_count : 2 + vertex_count + face_count]:
            parts = line.split()
            if len(parts) < 4:
                continue
            point_count = int(parts[0])
            indices = [int(idx) for idx in parts[1 : 1 + point_count]]
            for i in range(1, len(indices) - 1):
                faces.append([indices[0], indices[i], indices[i + 1]])

        return self._build_mesh_data(vertices, faces, "OFF 文件中缺少有效的面数据")

    def _build_mesh_data(self, vertices, faces, empty_error: str):
        if not vertices or not faces:
            raise ValueError(empty_error)
        verts = np.array(vertices, dtype=float)
        verts = verts - verts.mean(axis=0)
        extents = np.ptp(verts, axis=0)
        max_extent = float(np.max(extents)) if extents.size else 0.0
        if max_extent <= 1e-6:
            raise ValueError("模型尺寸无效")
        verts = verts * (2.4 / max_extent)
        return gl.MeshData(vertexes=verts, faces=np.array(faces, dtype=int))

    def _load_mesh_by_suffix(self, model_path: Path):
        suffix = model_path.suffix.lower()
        if suffix == ".obj":
            return self._load_obj_mesh(model_path)
        if suffix == ".stl":
            return self._load_stl_mesh(model_path)
        if suffix == ".off":
            return self._load_off_mesh(model_path)
        raise ValueError(f"暂不支持的模型格式: {suffix}")

    def _set_external_rov_model(self, model_path: Path):
        try:
            mesh = self._load_mesh_by_suffix(model_path)
        except Exception:
            return False

        if self._external_rov_item is None:
            self._external_rov_item = gl.GLMeshItem(
                meshdata=mesh,
                smooth=True,
                drawEdges=self._external_model_draw_edges,
                color=self._get_external_model_rgba(),
                shader="shaded",
            )
            self.view.addItem(self._external_rov_item)
            self._register_model_item("rov", self._external_rov_item)
        else:
            self._external_rov_item.setMeshData(meshdata=mesh)
        self._external_rov_loaded = True
        self._external_rov_path = model_path
        self._apply_external_model_material()
        self._apply_model_visibility()
        self._update_model_hint()
        self._update_model_transform()
        return True

    def import_rov_model(self):
        if not OPENGL_AVAILABLE:
            return
        self.EXTERNAL_ROV_DIR.mkdir(parents=True, exist_ok=True)
        selected_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "导入 ROV 模型",
            str(self.EXTERNAL_ROV_DIR),
            "模型文件 (*.obj *.stl *.off);;OBJ 模型 (*.obj);;STL 模型 (*.stl);;OFF 模型 (*.off)",
        )
        if not selected_path:
            return
        if not self._set_external_rov_model(Path(selected_path)):
            QtWidgets.QMessageBox.warning(self, "模型导入失败", "所选模型文件无法解析，请检查格式或文件内容。")

    def use_default_rov_model(self):
        self._external_rov_loaded = False
        self._external_rov_path = None
        if self._external_rov_item is not None:
            self._external_rov_item.setVisible(False)
        self._apply_model_visibility()
        self._update_model_hint()
        self._update_model_transform()

    def _add_rov_model(self):
        float_color = (0.16, 0.50, 0.84, 0.97)
        pod_color = (0.18, 0.20, 0.24, 0.98)
        accent_color = (0.18, 0.69, 0.98, 0.92)
        metal_primary = (0.72, 0.76, 0.80, 0.96)
        metal_highlight = (0.84, 0.87, 0.91, 0.82)

        self._body_item = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=1.70, width=1.06, height=0.34, chamfer=0.14),
            smooth=True,
            drawEdges=False,
            color=metal_primary,
            shader="shaded",
        )
        self.view.addItem(self._body_item)
        self._register_rov_procedural_item(self._body_item)
        self._body_highlight_item = None

        self._nose_item = None

        self._left_fin_item = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=1.32, width=0.32, height=0.27, chamfer=0.05),
            smooth=True,
            drawEdges=False,
            color=float_color,
            shader="shaded",
        )
        self._right_fin_item = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=1.32, width=0.32, height=0.27, chamfer=0.05),
            smooth=True,
            drawEdges=False,
            color=float_color,
            shader="shaded",
        )
        self.view.addItem(self._left_fin_item)
        self.view.addItem(self._right_fin_item)
        self._register_rov_procedural_item(self._left_fin_item)
        self._register_rov_procedural_item(self._right_fin_item)
        self._top_fin_item = None
        self._rov_lower_frame = None

        self._rov_float_link_left_front = None
        self._rov_float_link_left_rear = None
        self._rov_float_link_right_front = None
        self._rov_float_link_right_rear = None
        self._rov_float_brace_left = None
        self._rov_float_brace_right = None

        self._rov_skid_left = None
        self._rov_skid_right = None
        self._rov_skid_bridge_front = None
        self._rov_skid_bridge_rear = None
        self._rov_thruster_pod_left = None
        self._rov_thruster_pod_right = None
        self._rov_front_hoop = None
        self._rov_battery_tube = None
        self._rov_skid_post_left_front = None
        self._rov_skid_post_left_rear = None
        self._rov_skid_post_right_front = None
        self._rov_skid_post_right_rear = None
        self._rov_pod_link_left = None
        self._rov_pod_link_right = None
        self._rov_top_thruster_mounts = []
        self._rov_top_thruster_ducts = []
        self._rov_top_thruster_blades = []
        self._rov_bottom_thruster_mounts = []
        self._rov_bottom_thruster_ducts = []
        self._rov_bottom_thruster_blades = []

        self._rov_prop_a = None
        self._rov_prop_b = None
        self._rov_prop_c = None
        self._rov_prop_d = None
        self._rov_duct_left = None
        self._rov_duct_right = None
        self._rov_duct_top_left = None
        self._rov_duct_top_right = None

        self._rov_arm_base = None
        self._rov_arm_fore = None
        self._rov_claw = None
        self._rov_tether = None

        self._rov_camera_left = None
        self._rov_camera_right = None
        self._rov_light_left = None
        self._rov_light_right = None

    def _add_aircraft_model(self):
        body_color = (0.72, 0.76, 0.80, 0.96)
        accent_blue = (0.18, 0.50, 0.82, 0.94)
        accent_dark = (0.26, 0.30, 0.36, 0.94)
        body = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=2.7, width=0.42, height=0.36, chamfer=0.08),
            smooth=True,
            drawEdges=False,
            color=body_color,
            shader="shaded",
        )
        wing = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=0.54, width=3.0, height=0.10, chamfer=0.03),
            smooth=True,
            drawEdges=False,
            color=accent_blue,
            shader="shaded",
        )
        tail_h = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=0.72, width=1.0, height=0.08, chamfer=0.02),
            smooth=True,
            drawEdges=False,
            color=accent_dark,
            shader="shaded",
        )
        tail_v = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=0.46, width=0.10, height=0.78, chamfer=0.02),
            smooth=True,
            drawEdges=False,
            color=accent_dark,
            shader="shaded",
        )
        for item in (body, wing, tail_h, tail_v):
            self.view.addItem(item)
            self._register_model_item("aircraft", item)

        self._aircraft_body = body
        self._aircraft_wing = wing
        self._aircraft_tail_h = tail_h
        self._aircraft_tail_v = tail_v
        self._aircraft_nose = None
        self._aircraft_prop_a = None
        self._aircraft_prop_b = None

    def _add_generic_model(self):
        body_color = (0.66, 0.71, 0.76, 0.95)
        accent_blue = (0.20, 0.54, 0.86, 0.94)
        accent_dark = (0.28, 0.32, 0.38, 0.92)
        main = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=2.0, width=1.1, height=0.55, chamfer=0.10),
            smooth=True,
            drawEdges=False,
            color=body_color,
            shader="shaded",
        )
        cap = gl.GLMeshItem(
            meshdata=self._create_chamfered_box_mesh(length=0.56, width=0.66, height=0.46, chamfer=0.10),
            smooth=True,
            drawEdges=False,
            color=accent_blue,
            shader="shaded",
        )
        for item in (main, cap):
            self.view.addItem(item)
            self._register_model_item("generic", item)

        self._generic_main = main
        self._generic_cap = cap
        self._generic_ring = None
        self._generic_halo_a = None
        self._generic_halo_b = None

    def update_pose(self, roll: float, pitch: float, yaw: float, depth: Optional[float] = None, u_cmd: float = 0.0):
        now = time.monotonic()
        dt = max(1e-3, min(0.2, now - self._last_update_time))
        self._last_update_time = now

        self._roll = float(roll)
        self._pitch = float(pitch)
        self._yaw = float(yaw)
        self._u_cmd = float(u_cmd)
        if depth is not None:
            self._depth = float(depth)
            self._depth_by_model[self._model_type] = self._depth

        spin_rate = 70.0 + abs(self._u_cmd) * 28.0
        self._animation_phase = (self._animation_phase + dt * spin_rate) % 360.0
        self._append_trail_point(dt)
        self._update_labels()
        self._update_model_transform()

    def update_depth(self, depth: float):
        self._depth = float(depth)
        self._depth_by_model[self._model_type] = self._depth
        if self._trail_points:
            self._trail_points[-1][2] = self._get_vertical_position_value()
        self._update_labels()
        self._update_model_transform()

    def _append_trail_point(self, dt: float):
        if not OPENGL_AVAILABLE or self._virtual_pos is None:
            return

        yaw_rad = math.radians(self._yaw)
        forward_step = max(0.06, 0.18 + abs(self._u_cmd) * 0.05) * dt * 8.0
        self._virtual_pos[0] += math.cos(yaw_rad) * forward_step
        self._virtual_pos[1] += math.sin(yaw_rad) * forward_step
        self._virtual_pos[2] = self._get_vertical_position_value()
        self._trail_points.append(self._virtual_pos.copy())

    def _update_labels(self):
        self.roll_label.setText(f"滚转: {self._roll:.1f}°")
        self.pitch_label.setText(f"俯仰: {self._pitch:.1f}°")
        self.yaw_label.setText(f"偏航: {self._yaw:.1f}°")
        self.depth_label.setText(f"{self.vertical_metric_label()}: {self._depth:.3f}")
        self.u_cmd_label.setText(f"控制输出: {self._u_cmd:.3f}")
        self._update_scene_hud()

    def _update_scene_hud(self):
        if not hasattr(self, "scene_mode_label"):
            return
        mode_label = self.mode_combo.currentText() if hasattr(self, "mode_combo") else "姿态模式"
        model_label = self.model_combo.currentText() if hasattr(self, "model_combo") else "水下机器人"
        self.scene_mode_label.setText(f"模式: {mode_label}")
        self.scene_model_label.setText(f"模型: {model_label}")
        if self._model_type == "aircraft":
            self.scene_depth_label.setText(f"高度: {self._depth:.3f}")
            self.scene_output_label.setText(f"推力输出: {self._u_cmd:.3f}")
        elif self._model_type == "generic":
            self.scene_depth_label.setText(f"垂向位置: {self._depth:.3f}")
            self.scene_output_label.setText(f"输出: {self._u_cmd:.3f}")
        elif self._mode == "underwater":
            self.scene_depth_label.setText(f"潜深: {self._depth:.3f}")
            self.scene_output_label.setText(f"推进输出: {self._u_cmd:.3f}")
        else:
            self.scene_depth_label.setText(f"深度: {self._depth:.3f}")
            self.scene_output_label.setText(f"输出: {self._u_cmd:.3f}")

    def _update_model_transform(self):
        if not OPENGL_AVAILABLE or self._body_item is None:
            return

        center = self._virtual_pos if self._virtual_pos is not None else np.zeros(3, dtype=float)

        self._update_rov_pose(center)
        self._update_aircraft_pose(center)
        self._update_generic_pose(center)
        self._update_underwater_effects(center)

        if self._trail_item is not None:
            trail_array = np.array(self._trail_points, dtype=float) if self._trail_points else np.zeros((0, 3), dtype=float)
            self._trail_item.setData(pos=trail_array)

        if self._shadow_item is not None:
            self._shadow_item.setData(pos=np.array([[center[0], center[1], 0.0]], dtype=float))

        if self.follow_cb.isChecked():
            if self._model_type == "aircraft":
                z_bias = 0.12
                center_z = center[2] + z_bias
            elif self._mode == "underwater" and self._model_type == "rov":
                center_z = center[2] * 0.60 - 0.20
            else:
                z_bias = -0.1 if self._mode == "underwater" else 0.0
                center_z = center[2] + z_bias
            self.view.opts["center"] = self._make_vector(center[0], center[1], center_z)
            self.view.update()

    def _update_rov_pose(self, center):
        if self._external_rov_loaded and self._external_rov_item is not None:
            self._set_external_model_pose(self._external_rov_item, center[0], center[1], center[2] - 0.08)
        else:
            self._set_item_pose(self._body_item, center[0], center[1], center[2] - 0.02)
            self._set_item_pose(self._left_fin_item, center[0] - 0.04, center[1] + 0.46, center[2] + 0.26)
            self._set_item_pose(self._right_fin_item, center[0] - 0.04, center[1] - 0.46, center[2] + 0.26)
    def _update_aircraft_pose(self, center):
        if not hasattr(self, "_aircraft_body"):
            return
        base_z = center[2] + self.AIRCRAFT_GROUND_OFFSET
        self._set_item_pose(self._aircraft_body, center[0], center[1], base_z, extra_roll=0.0)
        self._set_item_pose(self._aircraft_wing, center[0] - 0.1, center[1], base_z)
        self._set_item_pose(self._aircraft_tail_h, center[0] - 1.0, center[1], base_z + 0.02)
        self._set_item_pose(self._aircraft_tail_v, center[0] - 1.05, center[1], base_z + 0.36)
        self._set_item_pose(self._aircraft_nose, center[0] + 1.35, center[1], base_z)

    def _update_generic_pose(self, center):
        if not hasattr(self, "_generic_main"):
            return
        self._set_item_pose(self._generic_main, center[0], center[1], center[2])
        self._set_item_pose(self._generic_cap, center[0] + 1.0, center[1], center[2])
        self._set_item_pose(self._generic_ring, center[0] - 0.2, center[1], center[2])

    def _update_underwater_effects(self, center):
        if not hasattr(self, "_depth_guide_item") or self._depth_guide_item is None:
            return
        if self._mode == "underwater" and self._model_type == "rov":
            self._depth_guide_item.setVisible(True)
            self._depth_guide_item.setData(
                pos=np.array(
                    [
                        [center[0], center[1], 0.0],
                        [center[0], center[1], center[2]],
                    ],
                    dtype=float,
                )
            )
        else:
            self._depth_guide_item.setVisible(False)

    def _apply_mode_style(self):
        if not OPENGL_AVAILABLE:
            return

        backgrounds = self._theme_palette.get("model_backgrounds", {})
        aircraft_bg = backgrounds.get("aircraft", "#b9dcff")
        trajectory_bg = backgrounds.get("trajectory", "#27425f")
        underwater_bg = backgrounds.get("underwater", "#4a6a86")
        attitude_bg = backgrounds.get("attitude", "#314a66")

        if self._model_type == "aircraft":
            self.view.setBackgroundColor(aircraft_bg)
            if self._grid_item is not None:
                self._grid_item.setVisible(False)
            for item in self._axes_items:
                item.setVisible(False)
            if hasattr(self, "_depth_guide_item") and self._depth_guide_item is not None:
                self._depth_guide_item.setVisible(False)
            if self._trail_item is not None:
                self._trail_item.setVisible(True)
                self._trail_item.setData(
                    color=(0.44, 0.73, 0.98, 0.92),
                    pos=np.array(self._trail_points, dtype=float) if self._trail_points else np.zeros((0, 3), dtype=float),
                )
            if self._shadow_item is not None:
                self._shadow_item.setVisible(True)
                self._shadow_item.setData(
                    pos=np.array([[self._virtual_pos[0], self._virtual_pos[1], 0.0]], dtype=float),
                    color=(0.18, 0.24, 0.30, 0.24),
                    size=20,
                    pxMode=True,
                )
            if hasattr(self, "_air_ground_item") and self._air_ground_item is not None:
                self._air_ground_item.setColor((0.80, 0.88, 0.68, 0.96))
                self._air_ground_item.setVisible(True)
            if hasattr(self, "_air_runway_item") and self._air_runway_item is not None:
                self._air_runway_item.setColor((0.86, 0.88, 0.90, 0.98))
                self._air_runway_item.setVisible(True)
            if hasattr(self, "_air_runway_stripe_item") and self._air_runway_stripe_item is not None:
                self._air_runway_stripe_item.setColor((0.99, 0.99, 0.98, 0.98))
                self._air_runway_stripe_item.setVisible(True)
            if self._seafloor_item is not None:
                self._seafloor_item.setVisible(False)
            return

        if self._mode == "trajectory":
            self.view.setBackgroundColor(trajectory_bg)
            if hasattr(self, "_air_ground_item") and self._air_ground_item is not None:
                self._air_ground_item.setVisible(False)
            if hasattr(self, "_air_runway_item") and self._air_runway_item is not None:
                self._air_runway_item.setVisible(False)
            if hasattr(self, "_air_runway_stripe_item") and self._air_runway_stripe_item is not None:
                self._air_runway_stripe_item.setVisible(False)
            if hasattr(self, "_depth_guide_item") and self._depth_guide_item is not None:
                self._depth_guide_item.setVisible(False)
            if self._grid_item is not None:
                self._grid_item.setVisible(True)
            for item in self._axes_items:
                item.setVisible(True)
            if self._seafloor_item is not None:
                self._seafloor_item.opts["drawEdges"] = False
                self._seafloor_item.setColor((0.82, 0.74, 0.58, 0.92))
            if self._trail_item is not None:
                self._trail_item.setVisible(True)
            if self._shadow_item is not None:
                self._shadow_item.setVisible(True)
            if self._seafloor_item is not None:
                self._seafloor_item.setVisible(False)
        elif self._mode == "underwater":
            self.view.setBackgroundColor(underwater_bg)
            if hasattr(self, "_air_ground_item") and self._air_ground_item is not None:
                self._air_ground_item.setVisible(False)
            if hasattr(self, "_air_runway_item") and self._air_runway_item is not None:
                self._air_runway_item.setVisible(False)
            if hasattr(self, "_air_runway_stripe_item") and self._air_runway_stripe_item is not None:
                self._air_runway_stripe_item.setVisible(False)
            if self._grid_item is not None:
                self._grid_item.setVisible(False)
            for item in self._axes_items:
                item.setVisible(False)
            if self._seafloor_item is not None:
                self._seafloor_item.opts["drawEdges"] = False
                self._seafloor_item.setColor((0.88, 0.80, 0.64, 0.96))
            if self._trail_item is not None:
                self._trail_item.setVisible(True)
            if self._shadow_item is not None:
                self._shadow_item.setVisible(False)
            if self._seafloor_item is not None:
                self._seafloor_item.setVisible(True)
        else:
            self.view.setBackgroundColor(attitude_bg)
            if hasattr(self, "_air_ground_item") and self._air_ground_item is not None:
                self._air_ground_item.setVisible(False)
            if hasattr(self, "_air_runway_item") and self._air_runway_item is not None:
                self._air_runway_item.setVisible(False)
            if hasattr(self, "_air_runway_stripe_item") and self._air_runway_stripe_item is not None:
                self._air_runway_stripe_item.setVisible(False)
            if hasattr(self, "_depth_guide_item") and self._depth_guide_item is not None:
                self._depth_guide_item.setVisible(False)
            if self._grid_item is not None:
                self._grid_item.setVisible(True)
            for item in self._axes_items:
                item.setVisible(True)
            if self._seafloor_item is not None:
                self._seafloor_item.opts["drawEdges"] = False
                self._seafloor_item.setColor((0.82, 0.74, 0.58, 0.92))
            if self._trail_item is not None:
                self._trail_item.setVisible(True)
            if self._shadow_item is not None:
                self._shadow_item.setVisible(True)
            if self._seafloor_item is not None:
                self._seafloor_item.setVisible(False)

        self._apply_model_visibility()

    def _get_vertical_position_value(self):
        if self._model_type != "rov":
            return self._depth
        return -self._depth

    def uses_sim_depth(self):
        return True

    def _apply_model_visibility(self):
        if not OPENGL_AVAILABLE:
            return
        for model_type, items in self._model_items.items():
            visible = model_type == self._model_type
            for item in items:
                item.setVisible(visible)
        if self._model_type == "rov" and self._external_rov_loaded:
            for item in self._rov_procedural_items:
                item.setVisible(False)
            if self._external_rov_item is not None:
                self._external_rov_item.setVisible(True)
        self._update_external_control_state()

    def _update_model_hint(self):
        if not hasattr(self, "model_hint_label"):
            return
        if not OPENGL_AVAILABLE:
            self.model_hint_label.setText("")
            if hasattr(self, "action_menu_btn"):
                self.action_menu_btn.setToolTip("")
            return
        if self._external_rov_loaded and self._external_rov_path is not None:
            text = f"ROV 外部模型已加载: {self._external_rov_path.name}。可在顶部菜单继续调整模型参数。"
        else:
            text = "当前使用系统默认模型。可在顶部菜单或工具栏切换模型、导入外部模型并调整外观。"
        self.model_hint_label.setText(text)
        if hasattr(self, "action_menu_btn"):
            self.action_menu_btn.setToolTip(text)

    def _update_external_control_state(self):
        enabled = self._model_type == "rov" and self._external_rov_loaded
        for widget in (
            self.model_roll_spin,
            self.model_pitch_spin,
            self.model_yaw_spin,
            self.model_scale_spin,
            self.reset_model_pose_btn,
            self.model_color_btn,
            self.model_alpha_spin,
            self.model_edges_cb,
            self.reset_model_material_btn,
        ):
            widget.setEnabled(enabled)

        default_enabled = self._model_type == "rov" and not self._external_rov_loaded
        if self._model_type in ("aircraft", "generic"):
            default_enabled = True
        for widget in (
            self.default_body_color_btn,
            self.default_float_color_btn,
            self.reset_default_colors_btn,
        ):
            widget.setEnabled(default_enabled)

        self.import_model_action.setEnabled(self._model_type == "rov")
        self.use_default_action.setEnabled(self._model_type == "rov")
        self.choose_builtin_primary_action.setEnabled(default_enabled)
        self.choose_builtin_accent_action.setEnabled(default_enabled)
        self.reset_builtin_colors_action.setEnabled(default_enabled)
        self.external_pose_dialog_action.setEnabled(enabled)
        self.external_material_dialog_action.setEnabled(enabled)
        self.reset_external_pose_action.setEnabled(enabled)
        self.reset_external_material_action.setEnabled(enabled)

        self._set_settings_option_enabled("builtin", default_enabled)
        self._set_settings_option_enabled("external_pose", enabled)
        self._set_settings_option_enabled("external_material", enabled)

        current_key = self.settings_combo.currentData() if hasattr(self, "settings_combo") else "builtin"
        if current_key in ("external_pose", "external_material") and not enabled:
            target = self.settings_combo.findData("builtin")
            if target >= 0:
                self.settings_combo.setCurrentIndex(target)
        self._on_settings_panel_changed()

    def _set_settings_option_enabled(self, option_key: str, enabled: bool):
        if not hasattr(self, "settings_combo"):
            return
        for index in range(self.settings_combo.count()):
            if self.settings_combo.itemData(index) != option_key:
                continue
            item = self.settings_combo.model().item(index)
            if item is not None:
                item.setEnabled(enabled)
            break

    def _sync_external_model_material_controls(self):
        self.model_color_btn.setStyleSheet(self._make_color_button_style(self._external_model_color))

    def _sync_builtin_color_controls(self):
        if self._model_type == "aircraft":
            primary_color = self._aircraft_body_color
            accent_color = self._aircraft_accent_color
            self.default_color_group_label.setText("飞行器")
            self.default_body_color_btn.setText("主体颜色")
            self.default_float_color_btn.setText("翼面颜色")
        elif self._model_type == "generic":
            primary_color = self._generic_body_color
            accent_color = self._generic_accent_color
            self.default_color_group_label.setText("通用载体")
            self.default_body_color_btn.setText("主体颜色")
            self.default_float_color_btn.setText("前舱/外框")
        else:
            primary_color = self._default_rov_body_color
            accent_color = self._default_rov_float_color
            self.default_color_group_label.setText("内置模型")
            self.default_body_color_btn.setText("机身颜色")
            self.default_float_color_btn.setText("浮力块颜色")

        self.default_body_color_btn.setStyleSheet(self._make_color_button_style(primary_color))
        self.default_float_color_btn.setStyleSheet(self._make_color_button_style(accent_color))
        self._sync_menu_action_texts()

    def _sync_menu_action_texts(self):
        if not hasattr(self, "choose_builtin_primary_action"):
            return
        self.choose_builtin_primary_action.setText(f"{self.default_body_color_btn.text()}...")
        self.choose_builtin_accent_action.setText(f"{self.default_float_color_btn.text()}...")
        self.reset_builtin_colors_action.setText(f"重置{self.default_color_group_label.text()}配色")

    def _set_external_model_pose(self, item, x: float, y: float, z: float):
        if item is None:
            return
        item.resetTransform()
        item.scale(self._external_model_scale, self._external_model_scale, self._external_model_scale)
        item.translate(x, y, z)
        item.rotate(self._yaw + self._external_model_yaw, 0, 0, 1, local=False)
        item.rotate(self._pitch + self._external_model_pitch, 0, 1, 0, local=False)
        item.rotate(self._roll + self._external_model_roll, 1, 0, 0, local=False)

    def _get_external_model_rgba(self):
        return (
            self._external_model_color.redF(),
            self._external_model_color.greenF(),
            self._external_model_color.blueF(),
            self._external_model_alpha,
        )

    def _apply_external_model_material(self):
        if self._external_rov_item is None:
            return
        self._external_rov_item.setColor(self._get_external_model_rgba())
        self._external_rov_item.opts["drawEdges"] = self._external_model_draw_edges
        self._external_rov_item.update()

    def _apply_builtin_model_colors(self):
        body_rgba = (
            self._default_rov_body_color.redF(),
            self._default_rov_body_color.greenF(),
            self._default_rov_body_color.blueF(),
            0.96,
        )
        float_rgba = (
            self._default_rov_float_color.redF(),
            self._default_rov_float_color.greenF(),
            self._default_rov_float_color.blueF(),
            0.97,
        )
        if self._body_item is not None:
            self._body_item.setColor(body_rgba)
        if self._left_fin_item is not None:
            self._left_fin_item.setColor(float_rgba)
        if self._right_fin_item is not None:
            self._right_fin_item.setColor(float_rgba)

        aircraft_body_rgba = (
            self._aircraft_body_color.redF(),
            self._aircraft_body_color.greenF(),
            self._aircraft_body_color.blueF(),
            0.96,
        )
        aircraft_accent_rgba = (
            self._aircraft_accent_color.redF(),
            self._aircraft_accent_color.greenF(),
            self._aircraft_accent_color.blueF(),
            0.94,
        )
        if hasattr(self, "_aircraft_body") and self._aircraft_body is not None:
            self._aircraft_body.setColor(aircraft_body_rgba)
        if hasattr(self, "_aircraft_nose") and self._aircraft_nose is not None:
            self._aircraft_nose.setColor(aircraft_body_rgba)
        if hasattr(self, "_aircraft_wing") and self._aircraft_wing is not None:
            self._aircraft_wing.setColor(aircraft_accent_rgba)
        if hasattr(self, "_aircraft_tail_h") and self._aircraft_tail_h is not None:
            self._aircraft_tail_h.setColor(aircraft_accent_rgba)
        if hasattr(self, "_aircraft_tail_v") and self._aircraft_tail_v is not None:
            self._aircraft_tail_v.setColor(aircraft_accent_rgba)

        generic_body_rgba = (
            self._generic_body_color.redF(),
            self._generic_body_color.greenF(),
            self._generic_body_color.blueF(),
            0.95,
        )
        generic_accent_rgba = (
            self._generic_accent_color.redF(),
            self._generic_accent_color.greenF(),
            self._generic_accent_color.blueF(),
            0.94,
        )
        if hasattr(self, "_generic_main") and self._generic_main is not None:
            self._generic_main.setColor(generic_body_rgba)
        if hasattr(self, "_generic_cap") and self._generic_cap is not None:
            self._generic_cap.setColor(generic_accent_rgba)
        if hasattr(self, "_generic_ring") and self._generic_ring is not None:
            self._generic_ring.setColor(generic_accent_rgba)

    def _set_item_pose(
        self,
        item,
        x: float,
        y: float,
        z: float,
        extra_roll: float = 0.0,
        extra_pitch: float = 0.0,
        extra_yaw: float = 0.0,
    ):
        if item is None:
            return
        item.resetTransform()
        item.translate(x, y, z)
        item.rotate(self._yaw + extra_yaw, 0, 0, 1, local=False)
        item.rotate(self._pitch + extra_pitch, 0, 1, 0, local=False)
        item.rotate(self._roll + extra_roll, 1, 0, 0, local=False)

    def _make_vector(self, x: float, y: float, z: float):
        return QtGui.QVector3D(x, y, z)
