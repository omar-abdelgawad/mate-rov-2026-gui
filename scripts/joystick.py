#!/usr/bin/env python3
"""ROV Joystick Control Node.

Reads physical joystick inputs and publishes ROS2 messages for
movement (Twist), grippers (Bool), rotation mode (Bool), and pitch (Float32).

All angular axes (wx, wy, wz) are sent as RATES that return to zero
when the input is released. The kinematic model integrates them.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
try:
    import pygame
except ImportError:
    pygame = None
import sys
import time

from pysticks import get_controller

# --- Configuration Constants ---
ROLL_RATE = 0.1        # deg/tick rate when D-pad left/right is held
PITCH_RATE = 0.1       # deg/tick rate when D-pad up/down is held
YAW_RATE = 0.25        # deg/tick rate for max horizontal stick deflection (25 deg/sec)
DEPTH_STEP = 0.005
DEPTH_REPEAT_PERIOD = 0.5
DEPTH_LIMIT = 4
DEPTH_UP_BUTTON = 5
DEPTH_DOWN_BUTTON = 3
RESET_ATTITUDE_BUTTON = 1


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))

def render_bar(val: float, max_val: float, half_width: int = 10) -> str:
    """Returns a string bar rendering the value, e.g. [      ████|          ]"""
    try:
        ratio = clamp(val / max_val, -1.0, 1.0)
    except ZeroDivisionError:
        ratio = 0.0
        
    bars = int(abs(ratio) * half_width)
    spaces = half_width - bars
    
    if ratio < -0.05:
        # Avoid zero-width bar formatting issues
        bar_str = '█' * max(0, bars - 1) + '▌' if bars > 0 else '▌'
        return f"[{' ' * spaces}{bar_str}|{' ' * half_width}]"
    elif ratio > 0.05:
        bar_str = '▐' + '█' * max(0, bars - 1) if bars > 0 else '▐'
        return f"[{' ' * half_width}|{bar_str}{' ' * spaces}]"
    else:
        return f"[{' ' * half_width}│{' ' * half_width}]"


class JoyStickNode(Node):
    def __init__(self):
        super().__init__("joystick")

        # Publishers
        self.joystick_publisher = self.create_publisher(Twist, "ROV/joystick", 10)
        self.gripper_r_publisher = self.create_publisher(Bool, "ROV/gripper_right", 1)
        self.gripper_l_publisher = self.create_publisher(Bool, "ROV/gripper_left", 1)

        # Initialize controller
        self.controller = get_controller()
        if self.controller is None:
            self.get_logger().error("No physical joystick found (or pygame missing). Joystick node will remain idle.")
            return

        # Timer (only started if controller is present)
        self.timer = self.create_timer(0.01, self.update)
        
        # TUI Display Timer (updates 10x per second to avoid terminal flicker)
        self.tui_timer = self.create_timer(0.1, self.render_tui)

        # Message state
        self.twist_msg = Twist()

        self.gripper_r_msg = Bool()
        self.gripper_r_msg.data = False
        self.prev_gripper_r = False

        self.gripper_l_msg = Bool()
        self.gripper_l_msg.data = False
        self.prev_gripper_l = False

        # Control state
        self.prev_reset = False
        self.last_update_time = time.time()
        self.first_render = True

    def render_tui(self):
        """Renders the minimal terminal UI showing current controller state."""
        # Using ANSI escape codes to clear screen and reposition cursor
        if self.first_render:
            sys.stdout.write('\033[2J')
            self.first_render = False
            
        sys.stdout.write('\033[H')  # Move cursor to top left
        
        lin_x = self.twist_msg.linear.x
        lin_y = self.twist_msg.linear.y
        lin_z = self.twist_msg.linear.z
        
        ang_x = self.twist_msg.angular.x
        ang_y = self.twist_msg.angular.y
        ang_z = self.twist_msg.angular.z
        
        grip_l = "[CLOSED]" if self.gripper_l_msg.data else "[OPEN]  "
        grip_r = "[CLOSED]" if self.gripper_r_msg.data else "[OPEN]  "
        
        lines = [
            "╔═══════════════════ ROV JOYSTICK TELEMETRY ═══════════════════╗",
            "║                                                              ║",
            "║  [ Linear Velocity Cmd ]                                     ║",
            f"║  Vx (Fwd/Rev):  {lin_x:+5.2f}  {render_bar(lin_x, 1.0, 12)}       ║",
            f"║  Vy (Strafe) :  {lin_y:+5.2f}  {render_bar(lin_y, 1.0, 12)}       ║",
            f"║  Vz (Depth)  :  {lin_z:+5.2f}  {render_bar(lin_z, DEPTH_STEP, 12)}       ║",
            "║                                                              ║",
            "║  [ Angular Rate Cmd ]                                        ║",
            f"║  Wx (Roll)   :  {ang_x:+5.2f}  {render_bar(ang_x, ROLL_RATE, 12)}       ║",
            f"║  Wy (Pitch)  :  {ang_y:+5.2f}  {render_bar(ang_y, PITCH_RATE, 12)}       ║",
            f"║  Wz (Yaw)    :  {ang_z:+5.2f}  {render_bar(ang_z, YAW_RATE, 12)}       ║",
            "║                                                              ║",
            "║  [ Actuators ]                                               ║",
            f"║  Gripper L   : {grip_l}     Gripper R   : {grip_r}           ║",
            "║                                                              ║",
            "╚══════════════════════════════════════════════════════════════╝"
        ]
        
        # Ensure we pad empty lines after TUI to overwrite any terminal garbage
        lines.extend([""] * 3) 
        
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    def update(self):
        """Main control loop — called every 10ms by the timer."""
        self.controller.update()

        now = time.time()
        # dt = max(now - self.last_update_time, 1e-3)
        self.last_update_time = now

        # --- Stick Axes → vX, vY ---
        throttle_scale = clamp((1.0 - self.controller.getThrottle()) * 0.5, 0.0, 1.0)
        vx_cmd = float(self.controller.getPitch()) * throttle_scale
        vy_cmd = float(-self.controller.getRoll()) * throttle_scale

        # --- Yaw axis → wz rate (returns to 0 when centered) ---
        yaw_axis = float(self.controller.getYaw())
        wz_cmd = -yaw_axis * throttle_scale * YAW_RATE

        # --- Hat (D-Pad) → Roll & Pitch RATES (returns to 0 when released) ---
        hat = self.controller.getAimball()
        wx_cmd = hat[0] * ROLL_RATE    # left/right → roll rate
        wy_cmd = hat[1] * PITCH_RATE   # up/down → pitch rate

        # --- Buttons → Depth RATE ---
        depth_up = bool(self.controller.joystick.get_button(DEPTH_UP_BUTTON))
        depth_down = bool(self.controller.joystick.get_button(DEPTH_DOWN_BUTTON))
        reset_attitude = bool(self.controller.joystick.get_button(RESET_ATTITUDE_BUTTON))

        vz_cmd = 0.0
        if depth_up:
            vz_cmd = DEPTH_STEP * throttle_scale
        elif depth_down:
            vz_cmd = -DEPTH_STEP * throttle_scale

        # --- Update gripper/rotation states ---
        self.controller.leftGripper()
        self.controller.rightGripper()

        # --- Build Twist message ---
        # linear: vx, vy are proportional to stick, depth is accumulated
        # angular: ALL are rates (zero when input released)
        self.twist_msg.linear.x = float(vx_cmd)
        self.twist_msg.linear.y = float(vy_cmd)
        self.twist_msg.linear.z = float(vz_cmd)
        self.twist_msg.angular.x = float(wx_cmd)   # roll rate
        self.twist_msg.angular.y = float(wy_cmd)   # pitch rate
        self.twist_msg.angular.z = float(wz_cmd)   # yaw rate

        # --- Publish gripper changes ---
        self.gripper_r_msg.data = self.controller.right_gripper
        self.gripper_l_msg.data = self.controller.left_gripper

        if self.gripper_r_msg.data != self.prev_gripper_r:
            self.gripper_r_publisher.publish(self.gripper_r_msg)
            self.prev_gripper_r = self.gripper_r_msg.data

        if self.gripper_l_msg.data != self.prev_gripper_l:
            self.gripper_l_publisher.publish(self.gripper_l_msg)
            self.prev_gripper_l = self.gripper_l_msg.data

        # --- E-Stop ---
        if self.controller.stopAll():
            self.twist_msg = Twist()

        # --- Reset attitude (zeros the accumulated angles in the kinematic model) ---
        # Send a special signal: all angular set to NaN to tell the model to reset
        if reset_attitude and not self.prev_reset:
            self.twist_msg.angular.x = float('nan')
            self.twist_msg.angular.y = float('nan')
            self.twist_msg.angular.z = float('nan')
        self.prev_reset = reset_attitude

        # --- Publish main command ---
        self.joystick_publisher.publish(self.twist_msg)


def main(args=None):
    rclpy.init(args=args)
    joystick_node = JoyStickNode()
    rclpy.spin(joystick_node)
    joystick_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
