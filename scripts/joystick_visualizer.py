"""Interactive joystick test that renders a 3D ROV orientation preview."""

import math
import sys
import threading
import time
from typing import Dict, Iterable, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pygame
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

try:
    import rclpy
    from geometry_msgs.msg import Vector3
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from std_msgs.msg import Float32MultiArray
except ImportError:  # Allow standalone usage when ROS is unavailable.
    rclpy = None
    Vector3 = None
    SingleThreadedExecutor = None
    Node = None
    Float32MultiArray = None


class Controller:
    """Minimal joystick helper replicating PySticks behavior."""

    STICK_DEADBAND = 0.05

    def __init__(self, axis_map):
        self.joystick = None
        self.axis_map = axis_map

    def update(self) -> None:
        pygame.event.pump()

    def getThrottle(self) -> float:
        return self._getAxis(0)

    def getRoll(self) -> float:
        return self._getAxis(1)

    def getPitch(self) -> float:
        return self._getAxis(2)

    def getYaw(self) -> float:
        return self._getAxis(3)

    def getHat(self, index: int = 0) -> Tuple[int, int]:
        if self.joystick is None or self.joystick.get_numhats() <= index:
            return (0, 0)
        return self.joystick.get_hat(index)

    def _getAxis(self, k: int) -> float:
        j = self.axis_map[k]
        val = self.joystick.get_axis(abs(j))
        if abs(val) < Controller.STICK_DEADBAND:
            val = 0.0
        return (-1 if j < 0 else 1) * val


class _SpringyThrottleController(Controller):
    def __init__(self, axis_map, button_id):
        super().__init__(axis_map)
        self.button_id = button_id
        self.throttleval = -1.0
        self.prevtime = time.time()

    def _getAuxValue(self) -> bool:
        return bool(self.button_id is not None and self.joystick.get_button(self.button_id))

    def getThrottle(self) -> float:
        currtime = time.time()
        self.throttleval += self._getAxis(0) * (currtime - self.prevtime)
        self.throttleval = min(max(self.throttleval, -1.0), 1.0)
        self.prevtime = currtime
        return self.throttleval


class _Xbox360(_SpringyThrottleController):
    def __init__(self, axes, aux):
        super().__init__(axes, None)
        self.aux = aux

    def _getAuxValue(self) -> bool:
        return self.joystick.get_axis(self.aux) < -0.5


class _Playstation(_SpringyThrottleController):
    def __init__(self, axes):
        super().__init__(axes, 7)


class _GameController(Controller):
    def __init__(self, axis_map, button_id):
        super().__init__(axis_map)
        self.button_id = button_id

    def _getAuxValue(self) -> bool:
        return bool(self.joystick.get_button(self.button_id))


class _RcTransmitter(Controller):
    def __init__(self, axis_map, aux_id):
        super().__init__(axis_map)
        self.aux_id = aux_id

    def getAux(self) -> float:
        return 1.0 if self.joystick.get_axis(self.aux_id) > 0 else -1.0


controllers: Dict[str, Controller] = {
    "Controller (Rock Candy Gamepad for Xbox 360)": _Xbox360((-1, 4, -3, 0), 2),
    "Rock Candy Gamepad for Xbox 360": _Xbox360((-1, 3, -4, 0), 5),
    "2In1 USB Joystick": _Playstation((-1, 2, -3, 0)),
    "Wireless Controller": _Playstation((-1, 2, -3, 0)),
    "MY-POWER CO.,LTD. 2In1 USB Joystick": _Playstation((-1, 2, -3, 0)),
    "Sony Interactive Entertainment Wireless Controller": _Playstation((-1, 3, -4, 0)),
    "Logitech Extreme 3D": _GameController((-2, 0, -1, 3), 0),
    "Logitech Logitech Extreme 3D": _GameController((-3, 0, -1, 2), 0),
    "Logitech Extreme 3D pro": _GameController((3, 0, -1, 2), 0),
    "Extreme 3D pro": _GameController((3, 0, -1, 2), 0),
    "FrSky Taranis Joystick": _RcTransmitter((0, 1, 2, 5), 3),
    "FrSky FrSky Taranis Joystick": _RcTransmitter((0, 1, 2, 3), 5),
    "SPEKTRUM RECEIVER": _RcTransmitter((1, 2, 5, 0), 4),
    "Horizon Hobby SPEKTRUM RECEIVER": _RcTransmitter((1, 2, 3, 0), 4),
}


def get_controller() -> Controller:
    pygame.display.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No joystick detected. Connect a controller and retry.")

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    controller_name = joystick.get_name()
    controller = controllers.get(controller_name)
    if controller is None:
        raise RuntimeError(f"Unrecognized controller: {controller_name}")
    controller.joystick = joystick
    return controller

# Simple wireframe model for visualization (meters).
_HALF_LENGTH = 0.28
_HALF_WIDTH = 0.22
_HALF_HEIGHT = 0.08

BODY_POINTS = np.array(
    [
        [_HALF_LENGTH, _HALF_WIDTH, _HALF_HEIGHT],     # Front-left top
        [_HALF_LENGTH, -_HALF_WIDTH, _HALF_HEIGHT],    # Front-right top
        [-_HALF_LENGTH, -_HALF_WIDTH, _HALF_HEIGHT],   # Rear-right top
        [-_HALF_LENGTH, _HALF_WIDTH, _HALF_HEIGHT],    # Rear-left top
        [_HALF_LENGTH, _HALF_WIDTH, -_HALF_HEIGHT],    # Front-left bottom
        [_HALF_LENGTH, -_HALF_WIDTH, -_HALF_HEIGHT],   # Front-right bottom
        [-_HALF_LENGTH, -_HALF_WIDTH, -_HALF_HEIGHT],  # Rear-right bottom
        [-_HALF_LENGTH, _HALF_WIDTH, -_HALF_HEIGHT],   # Rear-left bottom
        [0.0, 0.0, _HALF_HEIGHT + 0.06],               # Electronics bay top
        [0.0, 0.0, -_HALF_HEIGHT - 0.06],              # Keel anchor
    ],
    dtype=float,
)

# Pairs of indices describing the wireframe edges.
BODY_EDGES: Iterable[Tuple[int, int]] = (
    (0, 1), (1, 2), (2, 3), (3, 0),  # Top rectangle
    (4, 5), (5, 6), (6, 7), (7, 4),  # Bottom rectangle
    (0, 4), (1, 5), (2, 6), (3, 7),  # Uprights
    (0, 8), (1, 8), (2, 8), (3, 8),  # Mast struts
    (4, 9), (5, 9), (6, 9), (7, 9),  # Keel struts
)
BODY_PANELS: Iterable[Tuple[int, ...]] = (
    (0, 1, 2, 3),  # Top deck
    (4, 5, 6, 7),  # Bottom frame
    (0, 1, 5, 4),  # Sides
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
)
THRUSTER_LAYOUT = (
    {"pos": np.array([0.22, 0.18, 0.0]), "dir": np.array([1.0, -1.0, 0.0]), "type": "horizontal"},
    {"pos": np.array([0.22, -0.18, 0.0]), "dir": np.array([1.0, 1.0, 0.0]), "type": "horizontal"},
    {"pos": np.array([-0.22, 0.18, 0.0]), "dir": np.array([-1.0, -1.0, 0.0]), "type": "horizontal"},
    {"pos": np.array([-0.22, -0.18, 0.0]), "dir": np.array([-1.0, 1.0, 0.0]), "type": "horizontal"},
    {"pos": np.array([0.0, 0.24, 0.02]), "dir": np.array([0.0, 0.0, 1.0]), "type": "vertical"},
    {"pos": np.array([0.0, -0.24, 0.02]), "dir": np.array([0.0, 0.0, 1.0]), "type": "vertical"},
    {"pos": np.array([-0.3, 0.0, -0.04]), "dir": np.array([0.0, 0.0, -1.0]), "type": "vertical"},
)
THRUSTER_RADIUS = 0.035
THRUSTER_LENGTH = 0.16
THRUSTER_SEGMENTS = 18

MAX_ANGLE_DEG = 45.0  # Maximum virtual attitude command to visualize.
HAT_STEP_DEG = 2.0
HAT_REPEAT_PERIOD = 0.12
TRANSLATION_GAIN = 0.3  # m/s equivalent per stick unit.
YAW_STEP_DEG = 3.0
YAW_EVENT_THRESHOLD = 0.2
YAW_REPEAT_PERIOD = 0.12
DEPTH_STEP = 0.02
DEPTH_REPEAT_PERIOD = 0.12
DEPTH_UP_BUTTON = 5   # pygame button index (physical button 6)
DEPTH_DOWN_BUTTON = 3 # pygame button index (physical button 4)
RESET_ATTITUDE_BUTTON = 1  # pygame button index (physical button 2)
GRIPPER_LEFT_BUTTON = 4
GRIPPER_RIGHT_BUTTON = 2
VIEW_SPAN = 0.8
SEA_BG_COLOR = (0.015, 0.08, 0.14)
ROV_FRAME_COLOR = "#0f1a24"
ROV_PANEL_COLOR = "#1c4464"
ROV_THRUSTER_COLOR = "#2cc6ff"
ROV_VERTICAL_THRUSTER_COLOR = "#58b0ff"
PID_SERIES_LABELS = ("Vx", "Vy", "Yaw", "Depth", "Roll", "Pitch")


class TelemetryBuffer:
    """Thread-safe store for live PID telemetry."""

    def __init__(self):
        self._lock = threading.Lock()
        self._angles = (0.0, 0.0, 0.0)
        self._pid_error = (0.0,) * len(PID_SERIES_LABELS)
        self._pid_output = (0.0,) * len(PID_SERIES_LABELS)
        self._angles_stamp = 0.0
        self._pid_error_stamp = 0.0
        self._pid_output_stamp = 0.0
        self._have_angles = False
        self._have_pid_error = False
        self._have_pid_output = False

    def update_angles(self, roll: float, pitch: float, yaw: float) -> None:
        with self._lock:
            self._angles = (roll, pitch, yaw)
            self._angles_stamp = time.time()
            self._have_angles = True

    def update_errors(self, values: Iterable[float]) -> None:
        with self._lock:
            self._pid_error = self._to_series(values)
            self._pid_error_stamp = time.time()
            self._have_pid_error = True

    def update_outputs(self, values: Iterable[float]) -> None:
        with self._lock:
            self._pid_output = self._to_series(values)
            self._pid_output_stamp = time.time()
            self._have_pid_output = True

    def snapshot(self) -> Dict[str, object]:
        now = time.time()
        with self._lock:
            return {
                "angles": self._angles,
                "pid_error": self._pid_error,
                "pid_output": self._pid_output,
                "angles_available": self._have_angles,
                "pid_error_available": self._have_pid_error,
                "pid_output_available": self._have_pid_output,
                "angles_age": None if not self._have_angles else max(now - self._angles_stamp, 0.0),
                "pid_error_age": None if not self._have_pid_error else max(now - self._pid_error_stamp, 0.0),
                "pid_output_age": None if not self._have_pid_output else max(now - self._pid_output_stamp, 0.0),
            }

    def _to_series(self, values: Iterable[float]) -> Tuple[float, ...]:
        series = list(values)[: len(PID_SERIES_LABELS)]
        while len(series) < len(PID_SERIES_LABELS):
            series.append(0.0)
        return tuple(float(v) for v in series)


class TelemetryListener:
    """Runs a ROS subscriber to feed the telemetry buffer."""

    def __init__(self):
        self.buffer = TelemetryBuffer()
        self._thread = None
        self._executor = None
        self._node = None

    def start(self) -> bool:
        if rclpy is None or Node is None or SingleThreadedExecutor is None:
            return False

        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return True

    def _spin(self) -> None:
        try:
            rclpy.init(args=None)
        except Exception:
            return

        class _TelemetryNode(Node):
            def __init__(self, buffer: TelemetryBuffer):
                super().__init__("joystick_visualizer_telemetry")
                self._buffer = buffer
                self.create_subscription(Vector3, "ROV/angles", self._angles_cb, 10)
                self.create_subscription(Float32MultiArray, "ROV/pid_error", self._err_cb, 10)
                self.create_subscription(Float32MultiArray, "ROV/pid_output", self._out_cb, 10)

            def _angles_cb(self, msg: Vector3) -> None:
                self._buffer.update_angles(msg.x, msg.y, msg.z)

            def _err_cb(self, msg: Float32MultiArray) -> None:
                self._buffer.update_errors(msg.data)

            def _out_cb(self, msg: Float32MultiArray) -> None:
                self._buffer.update_outputs(msg.data)

        node = _TelemetryNode(self.buffer)
        executor = SingleThreadedExecutor()
        self._node = node
        self._executor = executor
        executor.add_node(node)
        try:
            executor.spin()
        finally:
            executor.remove_node(node)
            node.destroy_node()
            self._node = None
            self._executor = None
            rclpy.shutdown()

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def snapshot(self) -> Dict[str, object]:
        return self.buffer.snapshot()


def _format_pid_line(prefix: str, values: Iterable[float]) -> str:
    return f"{prefix}: " + " ".join(
        f"{label}:{value:+.2f}" for label, value in zip(PID_SERIES_LABELS, values)
    )


def _format_telemetry_text(snapshot: Dict[str, object], active: bool) -> str:
    if not active:
        return "Telemetry disabled (ROS link unavailable)."
    if snapshot is None:
        return "Telemetry connecting..."

    lines = []
    if snapshot.get("angles_available"):
        roll, pitch, yaw = snapshot["angles"]
        lines.append(f"Actual Roll {roll:+5.1f}° Pitch {pitch:+5.1f}° Yaw {yaw:+5.1f}°")
    else:
        lines.append("Actual angles: waiting for topic...")

    if snapshot.get("pid_error_available"):
        lines.append(_format_pid_line("PID Err", snapshot["pid_error"]))
    else:
        lines.append("PID Err: waiting for topic...")

    if snapshot.get("pid_output_available"):
        lines.append(_format_pid_line("PID Out", snapshot["pid_output"]))
    else:
        lines.append("PID Out: waiting for topic...")

    return "\n".join(lines)


def euler_rotation(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Return ZYX rotation matrix for the provided Euler angles."""

    c_r, s_r = math.cos(roll), math.sin(roll)
    c_p, s_p = math.cos(pitch), math.sin(pitch)
    c_y, s_y = math.cos(yaw), math.sin(yaw)

    rx = np.array([[1, 0, 0], [0, c_r, -s_r], [0, s_r, c_r]])
    ry = np.array([[c_p, 0, s_p], [0, 1, 0], [-s_p, 0, c_p]])
    rz = np.array([[c_y, -s_y, 0], [s_y, c_y, 0], [0, 0, 1]])
    return rz @ ry @ rx


def orthonormal_basis(direction: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create a right-handed basis aligned with direction for cylinder generation."""

    w = direction / np.linalg.norm(direction)
    # Choose helper vector that is not parallel to w
    helper = np.array([0.0, 0.0, 1.0]) if abs(w[2]) < 0.95 else np.array([0.0, 1.0, 0.0])
    u = np.cross(helper, w)
    if np.linalg.norm(u) < 1e-6:
        helper = np.array([1.0, 0.0, 0.0])
        u = np.cross(helper, w)
    u = u / np.linalg.norm(u)
    v = np.cross(w, u)
    v = v / np.linalg.norm(v)
    return u, v, w


def cylinder_faces(center: np.ndarray, u: np.ndarray, v: np.ndarray, w: np.ndarray,
                   radius: float, length: float, segments: int) -> Iterable[np.ndarray]:
    """Return polygon faces approximating a cylinder oriented by (u, v, w)."""

    top_center = center + 0.5 * length * w
    bottom_center = center - 0.5 * length * w
    angles = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    ring_offsets = [radius * (math.cos(a) * u + math.sin(a) * v) for a in angles]
    top_ring = [top_center + offset for offset in ring_offsets]
    bottom_ring = [bottom_center + offset for offset in ring_offsets]
    faces = []
    for idx in range(segments):
        nxt = (idx + 1) % segments
        faces.append([
            bottom_ring[idx],
            bottom_ring[nxt],
            top_ring[nxt],
            top_ring[idx],
        ])
    faces.append(top_ring)
    faces.append(bottom_ring[::-1])
    return faces


def main() -> None:
    controller = get_controller()
    telemetry_listener = TelemetryListener()
    telemetry_active = telemetry_listener.start()

    plt.ion()
    fig = plt.figure("ROV Joystick Visualizer", figsize=(10, 8))
    manager = plt.get_current_fig_manager()
    try:
        manager.window.showMaximized()
    except Exception:
        try:
            manager.full_screen_toggle()
        except Exception:
            pass
    ax = fig.add_subplot(111, projection="3d")
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
    ax.set_position([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(-0.5, 0.5)
    ax.set_zlim(-0.5, 0.5)
    ax.set_xlabel("X (forward)", color="white")
    ax.set_ylabel("Y (starboard)", color="white")
    ax.set_zlabel("Z (up)", color="white")
    ax.view_init(elev=25, azim=180)
    fig.patch.set_facecolor(SEA_BG_COLOR)
    ax.set_facecolor(SEA_BG_COLOR)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane = getattr(axis, "pane", None)
        if pane is not None:
            pane.set_facecolor((*SEA_BG_COLOR, 0.85))
            pane.set_edgecolor("none")
        axinfo = getattr(axis, "_axinfo", None)
        if axinfo and "grid" in axinfo:
            axinfo["grid"].update({"color": "#184c6b"})
        axis.line.set_color("white")
        axis.set_tick_params(colors="white")
    ax.tick_params(colors="white")
    gripper_text = fig.text(0.02, 0.96, "Grippers L:OPEN R:OPEN", fontsize=10, color="white")
    pose_text = fig.text(0.5, 0.97, "", fontsize=12, color="white", ha="center", va="top")
    telemetry_text = fig.text(
        0.02,
        0.88,
        _format_telemetry_text(None, telemetry_active),
        fontsize=9,
        color="white",
        va="top",
    )

    lines = []
    for start, end in BODY_EDGES:
        line, = ax.plot([], [], [], color=ROV_FRAME_COLOR, linewidth=2)
        lines.append((start, end, line))
    panel_collection = Poly3DCollection([], facecolor=ROV_PANEL_COLOR, edgecolor=ROV_FRAME_COLOR,
                                        linewidths=1.2, alpha=0.65)
    ax.add_collection3d(panel_collection)
    thruster_frames = []
    thruster_meshes = []
    for layout in THRUSTER_LAYOUT:
        u_vec, v_vec, w_vec = orthonormal_basis(layout["dir"])
        thruster_frames.append({
            "center": layout["pos"],
            "u": u_vec,
            "v": v_vec,
            "w": w_vec,
            "type": layout["type"],
        })
        color = ROV_THRUSTER_COLOR if layout["type"] == "horizontal" else ROV_VERTICAL_THRUSTER_COLOR
        mesh = Poly3DCollection([], facecolor=color, edgecolor="#0a6c94", linewidths=0.6, alpha=0.95)
        ax.add_collection3d(mesh)
        thruster_meshes.append(mesh)

    roll_deg = 0.0
    pitch_deg = 0.0
    yaw_deg = 0.0
    hat_state = (0, 0)
    hat_repeat_accum = HAT_REPEAT_PERIOD
    position = np.zeros(3)
    yaw_repeat_accum = YAW_REPEAT_PERIOD
    prev_depth_up = False
    prev_depth_down = False
    prev_reset = False
    depth_repeat_up = DEPTH_REPEAT_PERIOD
    depth_repeat_down = DEPTH_REPEAT_PERIOD
    gripper_left = False
    gripper_right = False
    prev_left_grip = False
    prev_right_grip = False
    last_update = time.time()
    try:
        while plt.fignum_exists(fig.number):
            controller.update()

            new_hat = controller.getHat()
            if new_hat != hat_state:
                if new_hat[0] != 0:
                    roll_deg = float(
                        np.clip(roll_deg + new_hat[0] * HAT_STEP_DEG, -MAX_ANGLE_DEG, MAX_ANGLE_DEG)
                    )
                if new_hat[1] != 0:
                    pitch_deg = float(
                        np.clip(pitch_deg + new_hat[1] * HAT_STEP_DEG, -MAX_ANGLE_DEG, MAX_ANGLE_DEG)
                    )
                hat_repeat_accum = 0.0 if (new_hat[0] or new_hat[1]) else HAT_REPEAT_PERIOD
                hat_state = new_hat

            now = time.time()
            dt = max(now - last_update, 1e-3)
            vx_cmd = controller.getPitch()
            vy_cmd = -controller.getRoll()
            yaw_axis = controller.getYaw()
            throttle_scale = (1.0 - controller.getThrottle()) * 0.5
            depth_up = controller.joystick.get_button(DEPTH_UP_BUTTON)
            depth_down = controller.joystick.get_button(DEPTH_DOWN_BUTTON)
            reset_attitude = controller.joystick.get_button(RESET_ATTITUDE_BUTTON)
            left_button = controller.joystick.get_button(GRIPPER_LEFT_BUTTON)
            right_button = controller.joystick.get_button(GRIPPER_RIGHT_BUTTON)

            depth_step = DEPTH_STEP * throttle_scale
            if depth_up and depth_step > 0.0:
                if not prev_depth_up:
                    position[2] += depth_step
                    depth_repeat_up = 0.0
                else:
                    depth_repeat_up += dt
                    if depth_repeat_up >= DEPTH_REPEAT_PERIOD:
                        position[2] += depth_step
                        depth_repeat_up = 0.0
            else:
                depth_repeat_up = DEPTH_REPEAT_PERIOD

            if depth_down and depth_step > 0.0:
                if not prev_depth_down:
                    position[2] -= depth_step
                    depth_repeat_down = 0.0
                else:
                    depth_repeat_down += dt
                    if depth_repeat_down >= DEPTH_REPEAT_PERIOD:
                        position[2] -= depth_step
                        depth_repeat_down = 0.0
            else:
                depth_repeat_down = DEPTH_REPEAT_PERIOD
            if reset_attitude and not prev_reset:
                roll_deg = 0.0
                pitch_deg = 0.0

            prev_depth_up = depth_up
            prev_depth_down = depth_down
            prev_reset = reset_attitude
            if left_button and not prev_left_grip:
                gripper_left = not gripper_left
            if right_button and not prev_right_grip:
                gripper_right = not gripper_right
            prev_left_grip = left_button
            prev_right_grip = right_button
            if abs(yaw_axis) > YAW_EVENT_THRESHOLD:
                yaw_repeat_accum += dt
                if yaw_repeat_accum >= YAW_REPEAT_PERIOD:
                    yaw_step = YAW_STEP_DEG * throttle_scale
                    if yaw_step > 0.0:
                        yaw_deg -= math.copysign(yaw_step, yaw_axis)
                    yaw_repeat_accum = 0.0
            else:
                yaw_repeat_accum = YAW_REPEAT_PERIOD

            if (new_hat[0] != 0 or new_hat[1] != 0):
                hat_repeat_accum += dt
                if hat_repeat_accum >= HAT_REPEAT_PERIOD:
                    if new_hat[0] != 0:
                        roll_deg = float(
                            np.clip(roll_deg + new_hat[0] * HAT_STEP_DEG, -MAX_ANGLE_DEG, MAX_ANGLE_DEG)
                        )
                    if new_hat[1] != 0:
                        pitch_deg = float(
                            np.clip(pitch_deg + new_hat[1] * HAT_STEP_DEG, -MAX_ANGLE_DEG, MAX_ANGLE_DEG)
                        )
                    hat_repeat_accum = 0.0
            else:
                hat_repeat_accum = HAT_REPEAT_PERIOD

            rotation = euler_rotation(
                math.radians(roll_deg),
                math.radians(pitch_deg),
                math.radians(yaw_deg),
            )
            body_velocity = np.array([vx_cmd, vy_cmd, 0.0])
            world_velocity = rotation @ body_velocity
            position += world_velocity * (TRANSLATION_GAIN * throttle_scale) * dt
            last_update = now
            ax.set_xlim(position[0] - VIEW_SPAN, position[0] + VIEW_SPAN)
            ax.set_ylim(position[1] - VIEW_SPAN, position[1] + VIEW_SPAN)
            ax.set_zlim(position[2] - VIEW_SPAN, position[2] + VIEW_SPAN)

            rotated = (rotation @ BODY_POINTS.T).T + position
            panel_collection.set_verts([rotated[list(face)] for face in BODY_PANELS])

            for start, end, line in lines:
                segment = rotated[[start, end], :]
                line.set_data(segment[:, 0], segment[:, 1])
                line.set_3d_properties(segment[:, 2])

            for frame, mesh in zip(thruster_frames, thruster_meshes):
                center = rotation @ frame["center"] + position
                u_world = rotation @ frame["u"]
                v_world = rotation @ frame["v"]
                w_world = rotation @ frame["w"]
                length = THRUSTER_LENGTH if frame["type"] == "horizontal" else THRUSTER_LENGTH * 0.9
                faces = cylinder_faces(center, u_world, v_world, w_world,
                                       THRUSTER_RADIUS, length, THRUSTER_SEGMENTS)
                mesh.set_verts(faces)

            pose_text.set_text(
                f"Roll {roll_deg: .1f}°, Pitch {pitch_deg: .1f}°, Yaw {yaw_deg: .1f}° | "
                f"Vx {vx_cmd:+.2f}, Vy {vy_cmd:+.2f}"
            )
            telemetry_snapshot = telemetry_listener.snapshot()
            telemetry_text.set_text(_format_telemetry_text(telemetry_snapshot, telemetry_active))
            gripper_text.set_text(
                f"Grippers L:{'CLOSED' if gripper_left else 'OPEN'} R:{'CLOSED' if gripper_right else 'OPEN'}"
            )

            plt.pause(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        telemetry_listener.stop()
        plt.ioff()
        plt.close(fig)
        pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except (pygame.error, RuntimeError) as exc:
        print(f"Unable to initialize joystick: {exc}", file=sys.stderr)
        sys.exit(1)
