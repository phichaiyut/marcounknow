# -*- coding: utf-8 -*-
"""
Robot Hotkey Macro (ฉบับปรับปรุง)
=================================
กดคีย์ลัด -> พิมพ์โค้ดหุ่นยนต์ลง IDE (Arduino IDE / VS Code) ที่บรรทัดปัจจุบัน แล้วขึ้นบรรทัดใหม่ให้อัตโนมัติ
ชุดคำสั่ง: ไลบรารี UnknowRobot_STORMXII_V3_BNO085 (STORM-XII V3 16CH + BNO085)
ค่า speed / cm / ms / dir / angle / action char ดึงจากหน้าต่างโพย (Always-on-Top) แบบสด ๆ

ปิดโปรแกรม: Ctrl+Shift+Q  (หรือปิดหน้าต่าง)

โหมดพิเศษ (ไม่กดคีย์ใส่ IDE):
    python macro.py --selftest      ตรวจผลลัพธ์ทุกคำสั่ง + คีย์ลัดไม่ซ้ำ + ชื่อฟังก์ชันมีจริงในไลบรารี
    python macro.py --table         พิมพ์ตารางคีย์ลัดเป็น Markdown (ใช้ทำ README / MACRO_CHEATSHEET)
    python macro.py --sketch        พิมพ์ Mission.ino ที่รวมทุกคำสั่ง (ใช้ทดสอบคอมไพล์ใน Arduino IDE)
    python macro.py --gui-test      สร้างหน้าต่าง GUI แล้วปิดทันที (เช็กว่า Tk ใช้ได้)

หมายเหตุทางเทคนิค
- คีย์ลัดใช้ Win32 RegisterHotKey (ไม่ใช้ hook ของไลบรารี keyboard) จึงไม่ทำให้ปุ่มค้าง,
  กินคีย์ลัดไม่ให้หลุดไปถึง IDE และทำงานได้แม้คีย์บอร์ดเป็นภาษาไทย (อ้างอิง virtual-key ไม่ใช่ตัวอักษร)
- การพิมพ์ใช้ Clipboard + Ctrl+V (ไม่เพี้ยนเป็นภาษาไทย และไม่โดน IDE เติมวงเล็บ/ฟันหนูซ้ำ)
  แล้วคืนค่า Clipboard เดิมให้
"""

import ctypes
import os
import queue
import sys
import threading
import time
from ctypes import wintypes

# ============================================================================
# 1) ค่าตั้งต้น (แก้ตรงนี้ได้เลย)
#    ค่าเริ่มต้นอิงจากตัวอย่างในไลบรารี UnknowRobot_STORMXII_V3_BNO085 (examples/ + Manual.ino)
#    เช่น FFL(50, 'l'), FFcm(50, 100, 's'), FFtimer(50, 1000, 's'), FFcmG(60, 30, 's'), spinDirection(90)
# ============================================================================
DEFAULT_SPEED = 50        # ความเร็วปกติ           (Ctrl+Alt+9)
FAST_SPEED = 80           # ความเร็วสูง            (Ctrl+Alt+0)
SLOW_SPEED = 30           # ความเร็วต่ำ/งานละเอียด (Ctrl+Alt+8)
DEFAULT_CM = 30           # ระยะทาง (cm)
DEFAULT_MS = 1000         # เวลา (ms)
DEFAULT_DIR = 0           # ทิศสัมบูรณ์ 0 / 90 / 180 / 270 (นับจาก resetAngles() ครั้งล่าสุด)
DEFAULT_ANGLE = 90        # องศาสัมพัทธ์ (SpinLG / TurnRG / spinDegree ... บวก = ขวา ลบ = ซ้าย)
DEFAULT_ACTION = 'p'      # ตัวอักษร select เมื่อเจอแยก
DEFAULT_N = 7             # n: ตำแหน่งเซนเซอร์ FFNUM (0-15) / ผลรวม FFSUM / จำนวนครั้ง Balance / เลขเซอร์โว
N_PRESETS = (1, 7, 8, 4000)
DEFAULT_L = 60            # ความเร็วล้อซ้าย (Move / Motor / rotateDegree / rotateDir)
DEFAULT_R = 20            # ความเร็วล้อขวา
FORCED_ACTION = 'p'       # คำสั่งที่บังคับ select (ชุด ffdirclg / ffdirg / ffdirf ...) แต่ผู้ใช้เลือก None -> ใช้ตัวนี้แทน

SPEED_STEP = 5            # Ctrl+Alt+= / Ctrl+Alt+-
CM_STEP = 5               # Ctrl+Alt+] / Ctrl+Alt+[
MS_STEP = 100             # Ctrl+Alt+Shift+] / Ctrl+Alt+Shift+[
ANGLE_STEP = 5            # ปุ่มบนจอ
SPEED_MIN, SPEED_MAX = 0, 100
DIR_CHOICES = (0, 90, 180, 270)

# ---- พฤติกรรมการพิมพ์ ----
PRESS_END_BEFORE = True   # กด End ก่อนพิมพ์ (ต่อท้ายบรรทัด)
PRESS_ENTER_AFTER = True  # กด Enter หลังพิมพ์ (ขึ้นบรรทัดใหม่ + IDE จัดย่อหน้าให้)
USE_SHORT_ALIAS = False   # True = ใช้ชื่อย่อของไลบรารี เช่น sdg / tdg แทน spinDirection / turnDirection
GYRO_INCLUDE_ACT = True   # FFcmG/BBcmG/FFcmGS/BBcmGS/FFtimerG/BBtimerG: ใส่ select (optional) ไหม
GYRO_INCLUDE_DIR = False  # FFcmG/.../FFBG/BBBG: ใส่ dir ต่อท้าย (optional) ไหม
OPT_SPEED_INCLUDE = True  # SpinL/SpinR/... + SpinLG/spinDirection/spinDegree ...: ใส่ speed (optional) ไหม
TYPE_METHOD = 'clipboard' # 'clipboard' (แนะนำ) หรือ 'unicode' (ใช้ keyboard.write)
RESTORE_CLIPBOARD = True  # คืนค่า Clipboard เดิมหลังวาง

# ---- จังหวะเวลา (วินาที) ปรับเพิ่มถ้าเครื่องช้าแล้วพิมพ์ไม่ครบ ----
MODIFIER_RELEASE_TIMEOUT = 10.0 # รอให้ปล่อย Ctrl/Alt/Shift ก่อนพิมพ์ (กดค้างแล้วรัวหลายคำสั่งได้)
FOCUS_DELAY = 0.12              # รอหลังสลับกลับไปหน้าต่าง IDE (กรณีกดปุ่มบนจอ)
KEY_GAP = 0.02                  # เว้นระหว่างปุ่ม
PASTE_SETTLE = 0.06             # รอหลัง Ctrl+V ก่อนกด Enter
CLIPBOARD_RESTORE_DELAY = 0.30  # รอก่อนคืนค่า Clipboard
FOCUS_RETRIES = 3               # สลับกลับ IDE ไม่ติด -> ลองใหม่กี่รอบก่อนแจ้งเตือน
HOVER_DEBOUNCE_MS = 30          # หน่วงพรีวิวตอนชี้ปุ่ม (ms) กัน UI รีเฟรชรัวตอนลากเมาส์ผ่านหลายปุ่ม

# ---- หน้าต่าง ----
WINDOW_ALPHA = 1.0        # 0.85 - 1.0 (โปร่งใส)
ALWAYS_ON_TOP = True
CODE_FONT = ('Consolas', 10)
UI_FONT = ('Segoe UI', 9)

EXIT_HOTKEY = 'ctrl+shift+q'

# ---- ไลบรารีที่ใช้ตรวจชื่อฟังก์ชัน (--selftest) ----
LIB_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'Arduino', 'libraries', 'UnknowRobot_STORMXII_V3_BNO085')
ARDUINO_BUILTINS = {'delay'}   # ฟังก์ชันพื้นฐานของ Arduino ที่อนุญาต

# ============================================================================
# 2) ตัวอักษรคำสั่งเจอแยก (select) — อิงจาก TrackSelectF / TrackSelectB (Unknow_PID.h)
#    และ TrackSelectG / TrackSelectGB (Unknow_IMU.h)
#    (ตัวอักษร, ความหมายในคำสั่งตามเส้น FF/BB, ความหมายในคำสั่ง Gyro *G)
#    ตัวที่ไม่อยู่ในตารางของคำสั่งนั้น = หยุดมอเตอร์
# ============================================================================
ACTION_CHARS = [
    ('s', 'เบรกหยุด', 'เบรกหยุด'),
    ('S', 'ToFront (bb: ToBack) แล้วเบรก', 'ToFront แล้วเบรก (bb: ถอยให้หลังเจอเส้นก่อน)'),
    ('p', 'วิ่งผ่านแยกต่อ', 'วิ่งผ่านแยกต่อ'),
    ('P', 'ToFront แล้วผ่านแยก (bb = p)', 'ToFront แล้วผ่านแยก (bb = p)'),
    ('c', 'เข้ากลางหุ่นแล้วหยุด', 'เข้ากลางหุ่นแล้วหยุด'),
    ('C', 'ToFront/ToBack + เข้ากลางหุ่น', 'ff: เข้ากลางหุ่น / bb: ToFront + ถอยเข้ากลาง'),
    ('l', 'เข้ากลาง + SpinL()', 'เข้ากลาง + หมุน -90°'),
    ('L', 'ToFront/ToBack + เข้ากลาง + SpinL()', 'หมุน -90° ทันที (ไม่เข้ากลาง)'),
    ('r', 'เข้ากลาง + SpinR()', 'เข้ากลาง + หมุน +90°'),
    ('R', 'ToFront/ToBack + เข้ากลาง + SpinR()', 'หมุน +90° ทันที (ไม่เข้ากลาง)'),
    ('q', 'เลี้ยวล้อเดียว TurnLeft() (bb: TurnRightB)', 'ToFront + เลี้ยว -90° (bb: เลี้ยวถอย +90°)'),
    ('Q', 'ToFront + q (bb: ToBack + q)', 'เลี้ยว -90° ทันที (bb: เลี้ยวถอย +90°)'),
    ('e', 'เลี้ยวล้อเดียว TurnRight() (bb: TurnLeftB)', 'ToFront + เลี้ยว +90° (bb: เลี้ยวถอย -90°)'),
    ('E', 'ToFront + e (bb: ToBack + e)', 'เลี้ยว +90° ทันที (bb: เลี้ยวถอย -90°)'),
    ('a', 'เข้ากลาง + SpinLB() (เซนเซอร์หลัง)', '- (ไม่มี = หยุด)'),
    ('A', 'ToFront/ToBack + a', '- (ไม่มี = หยุด)'),
    ('d', 'เข้ากลาง + SpinRB() (เซนเซอร์หลัง)', '- (ไม่มี = หยุด)'),
    ('D', 'ToFront/ToBack + d', '- (ไม่มี = หยุด)'),
    ('b', '- (ไม่มี = หยุด)', 'วิ่งต่อจนเซนเซอร์หลังเจอเส้น'),
    ('B', '- (ไม่มี = หยุด)', 'วิ่งต่อจนเซนเซอร์หลังเจอเส้น'),
    ('g', 'ค้างมุม SetFG / SetBG นาน = speed (ms)', 'ค้างมุม SetG นาน = speed (ms)'),
    ('G', 'ToFront/ToBack + ค้างมุม', 'ค้างมุม SetG นาน = speed (ms)'),
    ('n', 'ชุด *dir* / *deg* / rotateDir: ไหลต่อ ไม่เบรก (คำสั่งอื่น = หยุด)',
     'ชุด *dir* / *deg* / rotateDir: ไหลต่อ ไม่เบรก (คำสั่งอื่น = หยุด)'),
    ('f', 'ชุด *dir* / *deg* / rotateDir: เบรกไจโร + ล็อกมุม (คำสั่งอื่น = หยุด)',
     'ชุด *dir* / *deg* / rotateDir: เบรกไจโร + ล็อกมุม (คำสั่งอื่น = หยุด)'),
]
ACTION_LIST = [c for c, _, _ in ACTION_CHARS]
ACTION_INFO = {c: (line, gyro) for c, line, gyro in ACTION_CHARS}
ACT_NONE = ''   # ปุ่ม None = ไม่ใส่ตัวอักษร (ใช้กับคำสั่งที่ select เป็น optional)

# คำย่อบรรทัดล่างบนปุ่ม Action Pad
ACTION_SHORT = {
    's': 'เบรกหยุด', 'S': 'หน้าเส้นหยุด', 'c': 'กลางหยุด', 'C': 'กลางหยุด',
    'p': 'ผ่านแยก', 'P': 'ผ่านแยก', 'b': 'ทะลุ (G)', 'B': 'ทะลุ (G)',
    'l': 'กลาง+ซ้าย', 'L': 'ซ้าย', 'r': 'กลาง+ขวา', 'R': 'ขวา',
    'q': 'เลี้ยวซ้าย', 'Q': 'เลี้ยวซ้าย', 'e': 'เลี้ยวขวา', 'E': 'เลี้ยวขวา',
    'a': 'หลังซ้าย', 'A': 'หลังซ้าย', 'd': 'หลังขวา', 'D': 'หลังขวา',
    'g': 'ค้างมุม', 'G': 'ค้างมุม', 'n': 'ไหลต่อ', 'f': 'เบรกไจโร',
    ACT_NONE: 'ไม่ใส่ตัวอักษร',
}

# หมวดสีของ Action Pad: (ชื่อหมวด, สีพื้นอ่อน, สีเข้ม, ตัวอักษร)
ACTION_GROUPS = [
    ('หยุด', '#fde2e2', '#c53030', ['s', 'S', 'c', 'C']),
    ('ผ่าน/ทะลุ', '#dcfce7', '#2f855a', ['p', 'P', 'b', 'B']),
    ('หมุนแยก', '#dbeafe', '#1d4ed8', ['l', 'L', 'r', 'R']),
    ('เลี้ยวโค้ง', '#ffedd5', '#c05621', ['q', 'Q', 'e', 'E']),
    ('หลัง/ค้าง', '#ede9fe', '#6b21a8', ['a', 'A', 'd', 'D', 'g', 'G']),
    ('จบทิศ', '#ccfbf1', '#0f766e', ['n', 'f']),
]
ACTION_NONE_COLORS = ('#eeeeee', '#4a5568')
ACTION_COLOR = {ch: (light, strong) for _, light, strong, chars in ACTION_GROUPS for ch in chars}
ACTION_COLOR[ACT_NONE] = ACTION_NONE_COLORS
ACTION_FONT = ('Consolas', 16, 'bold')     # ตัวอักษรบนปุ่ม (ใหญ่ แยกเล็ก/ใหญ่ชัด)
ACTION_SUB_FONT = ('Segoe UI', 8)          # คำย่อบรรทัดล่าง
ACTION_CYCLE = ['p', 'c', 'l', 'r', 's', 'b', 'q', 'e', 'a', 'd', 'g', 'n', 'f']  # Ctrl+Alt+/ วนตัวถัดไป

# ============================================================================
# 3) ตารางคำสั่ง (MACROS) — ทุกชื่อ/ลำดับพารามิเตอร์ตรงกับไฟล์ .h ของ UnknowRobot_STORMXII_V3_BNO085
#    params: speed cm cmi ms dir angle act n L R  + เครื่องหมายท้ายชื่อ:
#       (ไม่มี)  บังคับใส่เสมอ
#       ?        optional ตามติ๊กในหน้าต่าง (act? / dir? = "Gyro ใส่ act/dir", speed? = "ใส่ speed (opt.)")
#                ไลบรารีแยก overload ด้วยชนิด (char = select, int = dir) จึงใส่/ไม่ใส่แต่ละตัวได้อิสระ
#       ~        act~ = ใส่เมื่อเลือกตัวอักษร / ตัดทิ้งเมื่อเลือก None
#       !        act! = บังคับมี select ถ้าเลือก None จะใช้ FORCED_ACTION ('p') แทน
#    cmi   : cm แบบจำนวนเต็ม (ชุด FFcmCirCle* รับ int เท่านั้น) — ปัดเศษให้เอง
#    hotkey: None = ไม่มีคีย์ลัด (กดปุ่มบนจออย่างเดียว)   btn: ป้ายสั้นบนปุ่ม (ไม่กระทบโค้ดที่พิมพ์)
#    raw   : ข้อความแม่แบบ ใช้ {speed} {cm} {ms} {dir} {angle} {act} {n} {L} {R} {fast} {slow} ได้
#    หมายเหตุ: ไม่มีคำสั่งแบบใส่ kp/kd เอง เพราะถ้าจำนวนอาร์กิวเมนต์ไปตรงกับ overload kp
#    ตัวอักษร/ตัวเลขจะถูกแปลงชนิดเงียบ ๆ (เช่น 'p' กลายเป็น kp = 112) — พิมพ์ kp/kd เองใน IDE แทน
# ============================================================================


class Cmd:
    """คำสั่งที่พิมพ์โค้ดลง IDE"""
    _count = 0

    def __init__(self, cat, hotkey, name, params='', alias=None, desc='', raw=None, btn=None):
        Cmd._count += 1
        self.btn = btn          # ป้ายสั้นบนปุ่ม (เฉพาะชื่อยาวมาก) — โค้ดที่พิมพ์ยังเป็นชื่อเต็ม
        self.cat = cat
        self.hotkey = hotkey
        self.name = name
        self.params = params.split()
        self.alias = alias
        self.desc = desc
        self.raw = raw
        # คีย์ลัดไม่ซ้ำกัน -> ใช้เป็น id; ปุ่มที่ไม่มีคีย์ลัดใช้ลำดับแทน
        self.id = 'cmd:' + (hotkey if hotkey else f'btn{Cmd._count}')

    def label(self, short=False):
        if self.raw:
            return self.name
        return self.alias if (short and self.alias) else self.name


CAT_LINE = 'ตามเส้นจนเจอแยก'
CAT_DIST = 'ตามเวลา / ระยะ / ขาว-ดำ'
CAT_SPIN_LINE = 'หมุน/เลี้ยวหาเส้น'
CAT_CENTER = 'เข้ากลาง / จัดตรงเส้น'
CAT_CURVE = 'กินโค้ง CirCle'
CAT_DIR_LINE = 'ตามเส้นจนถึงทิศ (จบโหมดเส้น)'
CAT_DIR_G = 'ตามเส้นจนถึงทิศ (จบ TrackSelectG)'
CAT_DEG = 'ตามเส้นจนหมุนครบองศา'
CAT_GYRO = 'Gyro วิ่งตรง'
CAT_TURN = 'Gyro หมุน/เลี้ยว'
CAT_GYRO_ADV = 'Gyro ขั้นสูง (โค้ง S / arc / คอมโบ)'
CAT_HOLD = 'ตั้งทิศ / ค้างมุม'
CAT_SERVO = 'Servo (ฟังก์ชันใน Servo.ino)'
CAT_SERVO2 = 'Servo ท่าผสม'
CAT_SERVO1 = 'Servo ทีละข้าง'
CAT_MOTOR = 'มอเตอร์ / ออกตัว'
CAT_SETUP = 'ตั้งค่า / เซนเซอร์ (ค่าจากตัวอย่าง)'
CAT_CUSTOM = 'กำหนดเอง'

MACROS = [
    # ---------- ตามเส้นจนเจอแยก: Ctrl+Alt+1..4 = ไปหน้า / +Shift = ถอยหลัง ----------
    Cmd(CAT_LINE, 'ctrl+alt+1', 'FFC', 'speed act', desc='ตามเส้น จับแยกด้วยเซนเซอร์คู่กลาง'),
    Cmd(CAT_LINE, 'ctrl+alt+2', 'FFC2', 'speed act', desc='ตามเส้น จับแยกด้วยริมซ้าย+ขวา (0,15)'),
    Cmd(CAT_LINE, 'ctrl+alt+3', 'FFL', 'speed act', desc='ตามเส้น จับแยกด้วยเซนเซอร์คู่ซ้าย'),
    Cmd(CAT_LINE, 'ctrl+alt+4', 'FFR', 'speed act', desc='ตามเส้น จับแยกด้วยเซนเซอร์คู่ขวา'),
    Cmd(CAT_LINE, 'ctrl+alt+shift+1', 'BBC', 'speed act', desc='ถอยตามเส้น จับแยกคู่กลาง'),
    Cmd(CAT_LINE, 'ctrl+alt+shift+2', 'BBC2', 'speed act', desc='ถอยตามเส้น จับแยกริมซ้าย+ขวา'),
    Cmd(CAT_LINE, 'ctrl+alt+shift+3', 'BBL', 'speed act', desc='ถอยตามเส้น จับแยกคู่ซ้าย'),
    Cmd(CAT_LINE, 'ctrl+alt+shift+4', 'BBR', 'speed act', desc='ถอยตามเส้น จับแยกคู่ขวา'),
    Cmd(CAT_LINE, None, 'FFL0', 'speed act', desc='เหมือน FFL + ริมซ้ายสุด (แยกกว้าง)'),
    Cmd(CAT_LINE, None, 'FFR15', 'speed act', desc='เหมือน FFR + ริมขวาสุด (แยกกว้าง)'),
    Cmd(CAT_LINE, None, 'BBL0', 'speed act', desc='ถอย BBL + ริมซ้ายสุด'),
    Cmd(CAT_LINE, None, 'BBR15', 'speed act', desc='ถอย BBR + ริมขวาสุด'),
    Cmd(CAT_LINE, None, 'FFNUM', 'speed act n', desc='ตามเส้น จับแยกที่เซนเซอร์ตัวที่ n (0-15)'),
    Cmd(CAT_LINE, None, 'BBNUM', 'speed act n', desc='ถอยตามเส้น จับแยกที่เซนเซอร์ตัวที่ n'),
    Cmd(CAT_LINE, None, 'FFSUM', 'speed act n', desc='ตามเส้นจนผลรวมเซนเซอร์หน้า >= n (เช่น 4000)'),
    Cmd(CAT_LINE, None, 'BBSUM', 'speed act n', desc='ถอยตามเส้นจนผลรวม >= n'),

    # ---------- ตามเวลา / ระยะ / ขาว-ดำ: Ctrl+Alt+5..7 / +Shift = ถอยหลัง ----------
    Cmd(CAT_DIST, 'ctrl+alt+5', 'FFcm', 'speed cm act~', desc='ตามเส้นตามระยะ cm (+select ถ้าเลือก)'),
    Cmd(CAT_DIST, 'ctrl+alt+shift+5', 'BBcm', 'speed cm act~', desc='ถอยตามเส้นตามระยะ cm'),
    Cmd(CAT_DIST, 'ctrl+alt+6', 'FFtimer', 'speed ms act~', desc='ตามเส้นตามเวลา ms (+select ถ้าเลือก)'),
    Cmd(CAT_DIST, 'ctrl+alt+shift+6', 'BBtimer', 'speed ms act~', desc='ถอยตามเส้นตามเวลา ms'),
    Cmd(CAT_DIST, 'ctrl+alt+7', 'FFWhite', 'speed act', desc='ตามเส้นจนเซนเซอร์หน้าขาวหมด'),
    Cmd(CAT_DIST, 'ctrl+alt+shift+7', 'BBWhite', 'speed act', desc='ถอยตามเส้นจนเซนเซอร์หลังขาวหมด'),
    Cmd(CAT_DIST, None, 'FFBlack', 'speed act', desc='เดินหน้า (ไม่ PID) จนเซนเซอร์หน้าเจอดำ'),
    Cmd(CAT_DIST, None, 'BBBlack', 'speed act', desc='ถอยหลัง (ไม่ PID) จนเซนเซอร์หลังเจอดำ'),

    # ---------- หมุน/เลี้ยวหาเส้น: Shift+A/D = 1 เส้น, Shift+J/L = เส้นที่ 2 ----------
    Cmd(CAT_SPIN_LINE, 'ctrl+alt+shift+a', 'SpinL', 'speed?', desc='หมุนซ้ายหาเส้น (เซนเซอร์หน้า)'),
    Cmd(CAT_SPIN_LINE, 'ctrl+alt+shift+d', 'SpinR', 'speed?', desc='หมุนขวาหาเส้น (เซนเซอร์หน้า)'),
    Cmd(CAT_SPIN_LINE, 'ctrl+alt+shift+j', 'SpinL2', 'speed?', desc='หมุนซ้ายข้ามไปเส้นที่ 2'),
    Cmd(CAT_SPIN_LINE, 'ctrl+alt+shift+l', 'SpinR2', 'speed?', desc='หมุนขวาข้ามไปเส้นที่ 2'),
    Cmd(CAT_SPIN_LINE, None, 'SpinLB', 'speed?', desc='หมุนซ้ายหาเส้น (เซนเซอร์หลัง)'),
    Cmd(CAT_SPIN_LINE, None, 'SpinRB', 'speed?', desc='หมุนขวาหาเส้น (เซนเซอร์หลัง)'),
    Cmd(CAT_SPIN_LINE, None, 'SpinL2B', 'speed?', desc='หมุนซ้ายเส้นที่ 2 (เซนเซอร์หลัง)'),
    Cmd(CAT_SPIN_LINE, None, 'SpinR2B', 'speed?', desc='หมุนขวาเส้นที่ 2 (เซนเซอร์หลัง)'),
    Cmd(CAT_SPIN_LINE, None, 'TurnLeft', desc='เลี้ยวซ้ายล้อเดียว (เซนเซอร์หน้า)'),
    Cmd(CAT_SPIN_LINE, None, 'TurnRight', desc='เลี้ยวขวาล้อเดียว (เซนเซอร์หน้า)'),
    Cmd(CAT_SPIN_LINE, None, 'TurnLeftB', desc='เลี้ยวถอยหลังซ้ายล้อเดียว'),
    Cmd(CAT_SPIN_LINE, None, 'TurnRightB', desc='เลี้ยวถอยหลังขวาล้อเดียว'),

    # ---------- เข้ากลาง / จัดตรงเส้น ----------
    Cmd(CAT_CENTER, 'ctrl+alt+shift+c', 'ToCenter', desc='เดินหน้าเข้ากลางหุ่น (กลางซ้ายหรือขวา)'),
    Cmd(CAT_CENTER, None, 'ToCenterL', desc='เดินหน้าจนกลางซ้ายเจอเส้น'),
    Cmd(CAT_CENTER, None, 'ToCenterR', desc='เดินหน้าจนกลางขวาเจอเส้น'),
    Cmd(CAT_CENTER, None, 'BackCenter', desc='ถอยหลังเข้ากลางหุ่น'),
    Cmd(CAT_CENTER, None, 'LF', 'ms', desc='จัดตรงเส้นอยู่กับที่ (เซนเซอร์หน้า) ms'),
    Cmd(CAT_CENTER, None, 'LB', 'ms', desc='จัดตรงเส้นอยู่กับที่ (เซนเซอร์หลัง) ms'),
    Cmd(CAT_CENTER, None, 'BalanceF', 'n', desc='จัดหุ่นตรงเส้น เซนเซอร์หน้า n ครั้ง'),
    Cmd(CAT_CENTER, None, 'BalanceB', 'n', desc='จัดหุ่นตรงเส้น เซนเซอร์หลัง n ครั้ง'),
    Cmd(CAT_CENTER, None, 'BalanceFC', 'n', desc='จัดตรง คู่กลาง (ขยับหน้า) n ครั้ง'),
    Cmd(CAT_CENTER, None, 'BalanceBC', 'n', desc='จัดตรง คู่กลาง (ขยับถอย) n ครั้ง'),

    # ---------- กินโค้ง CirCle: T / Y (+Shift = ถอยหลัง) ----------
    Cmd(CAT_CURVE, 'ctrl+alt+t', 'FFcmCirCleL', 'speed cmi act~', desc='กินโค้งซ้ายตามระยะ (cm จำนวนเต็ม)'),
    Cmd(CAT_CURVE, 'ctrl+alt+y', 'FFcmCirCleR', 'speed cmi act~', desc='กินโค้งขวาตามระยะ (cm จำนวนเต็ม)'),
    Cmd(CAT_CURVE, 'ctrl+alt+shift+t', 'BBcmCirCleL', 'speed cmi act~', desc='ถอยกินโค้งซ้ายตามระยะ'),
    Cmd(CAT_CURVE, 'ctrl+alt+shift+y', 'BBcmCirCleR', 'speed cmi act~', desc='ถอยกินโค้งขวาตามระยะ'),
    Cmd(CAT_CURVE, None, 'FFCirCleL', 'speed act', desc='กินโค้งซ้ายจนเจอแยก'),
    Cmd(CAT_CURVE, None, 'FFCirCleR', 'speed act', desc='กินโค้งขวาจนเจอแยก'),
    Cmd(CAT_CURVE, None, 'BBCirCleL', 'speed act', desc='ถอยกินโค้งซ้ายจนเจอแยก'),
    Cmd(CAT_CURVE, None, 'BBCirCleR', 'speed act', desc='ถอยกินโค้งขวาจนเจอแยก'),
    Cmd(CAT_CURVE, None, 'FFtimerCirCleL', 'speed ms act~', desc='กินโค้งซ้ายตามเวลา'),
    Cmd(CAT_CURVE, None, 'FFtimerCirCleR', 'speed ms act~', desc='กินโค้งขวาตามเวลา'),
    Cmd(CAT_CURVE, None, 'BBtimerCirCleL', 'speed ms act~', desc='ถอยกินโค้งซ้ายตามเวลา'),
    Cmd(CAT_CURVE, None, 'BBtimerCirCleR', 'speed ms act~', desc='ถอยกินโค้งขวาตามเวลา'),

    # ---------- ตามเส้นจนถึงทิศ จบโหมดเส้น: ; / ' (+Shift = ถอยหลัง)  ลำดับ: speed, [select,] dir ----------
    Cmd(CAT_DIR_LINE, 'ctrl+alt+;', 'ffdircl', 'speed act~ dir', desc='เกาะโค้งซ้ายจนหันถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, "ctrl+alt+'", 'ffdircr', 'speed act~ dir', desc='เกาะโค้งขวาจนหันถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, 'ctrl+alt+shift+;', 'bbdircl', 'speed act~ dir', desc='ถอยเกาะโค้งซ้ายจนถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, "ctrl+alt+shift+'", 'bbdircr', 'speed act~ dir', desc='ถอยเกาะโค้งขวาจนถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, None, 'FFdir', 'speed dir act~', desc='ตามเส้นจนหันถึงทิศ dir (select ไว้ท้าย)'),
    Cmd(CAT_DIR_LINE, None, 'BBdir', 'speed dir act~', desc='ถอยตามเส้นจนถึงทิศ dir (select ไว้ท้าย)'),
    Cmd(CAT_DIR_LINE, None, 'FFdirCirCleL', 'speed dir act~', desc='กินโค้งซ้ายจนถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, None, 'FFdirCirCleR', 'speed dir act~', desc='กินโค้งขวาจนถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, None, 'BBdirCirCleL', 'speed dir act~', desc='ถอยกินโค้งซ้ายจนถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, None, 'BBdirCirCleR', 'speed dir act~', desc='ถอยกินโค้งขวาจนถึงทิศ dir'),
    Cmd(CAT_DIR_LINE, None, 'ffdirf', 'speed dir act!', desc="ตามเส้นถึงทิศ → TrackSelectF (None→'p')"),
    Cmd(CAT_DIR_LINE, None, 'bbdirb', 'speed dir act!', desc="ถอยตามเส้นถึงทิศ → TrackSelectB (None→'p')"),

    # ---------- ตามเส้นจนถึงทิศ จบ TrackSelectG: Z / X (+Shift = ถอยหลัง)  select บังคับ (None -> 'p') ----------
    Cmd(CAT_DIR_G, 'ctrl+alt+z', 'ffdirclg', 'speed act! dir', desc="เกาะโค้งซ้ายถึง dir → TrackSelectG (None→'p')"),
    Cmd(CAT_DIR_G, 'ctrl+alt+x', 'ffdircrg', 'speed act! dir', desc="เกาะโค้งขวาถึง dir → TrackSelectG (None→'p')"),
    Cmd(CAT_DIR_G, 'ctrl+alt+shift+z', 'bbdirclg', 'speed act! dir', desc="ถอยเกาะโค้งซ้ายถึง dir → GB (None→'p')"),
    Cmd(CAT_DIR_G, 'ctrl+alt+shift+x', 'bbdircrg', 'speed act! dir', desc="ถอยเกาะโค้งขวาถึง dir → GB (None→'p')"),
    Cmd(CAT_DIR_G, None, 'ffdirg', 'speed act! dir', desc="ตามเส้นถึงทิศ dir → TrackSelectG (None→'p')"),
    Cmd(CAT_DIR_G, None, 'bbdirg', 'speed act! dir', desc="ถอยตามเส้นถึงทิศ dir → TrackSelectGB (None→'p')"),

    # ---------- ตามเส้นจนหมุนครบองศา (angle: + = ขวา) ----------
    Cmd(CAT_DEG, None, 'ffdeg', 'speed act~ angle', desc='ตามเส้นจนหมุนครบ angle → TrackSelectF'),
    Cmd(CAT_DEG, None, 'bbdeg', 'speed act~ angle', desc='ถอยตามเส้นจนหมุนครบ angle → TrackSelectB'),
    Cmd(CAT_DEG, None, 'ffdegg', 'speed act! angle', desc="เหมือน ffdeg จบ TrackSelectG (None→'p')"),
    Cmd(CAT_DEG, None, 'bbdegg', 'speed act! angle', desc="เหมือน bbdeg จบ TrackSelectGB (None→'p')"),
    Cmd(CAT_DEG, None, 'ffdegcl', 'speed act~ angle', desc='เกาะโค้งซ้ายจนหมุนครบ angle'),
    Cmd(CAT_DEG, None, 'ffdegcr', 'speed act~ angle', desc='เกาะโค้งขวาจนหมุนครบ angle'),
    Cmd(CAT_DEG, None, 'bbdegcl', 'speed act~ angle', desc='ถอยเกาะโค้งซ้ายจนหมุนครบ angle'),
    Cmd(CAT_DEG, None, 'bbdegcr', 'speed act~ angle', desc='ถอยเกาะโค้งขวาจนหมุนครบ angle'),
    Cmd(CAT_DEG, None, 'ffdegclg', 'speed act! angle', desc="เกาะโค้งซ้ายครบ angle → G (None→'p')"),
    Cmd(CAT_DEG, None, 'ffdegcrg', 'speed act! angle', desc="เกาะโค้งขวาครบ angle → G (None→'p')"),
    Cmd(CAT_DEG, None, 'bbdegclg', 'speed act! angle', desc="ถอยเกาะโค้งซ้ายครบ angle → GB (None→'p')"),
    Cmd(CAT_DEG, None, 'bbdegcrg', 'speed act! angle', desc="ถอยเกาะโค้งขวาครบ angle → GB (None→'p')"),

    # ---------- Gyro วิ่งตรง: G / H / V / B (+Shift = ถอยหลัง)  + รีเซ็ตมุม = Ctrl+Alt+O (O = 0°) ----------
    Cmd(CAT_GYRO, 'ctrl+alt+o', 'resetAngles', desc='รีเซ็ตมุมไจโร = ทิศ 0 (ตั้งลำ/เช็กพอยต์)'),
    Cmd(CAT_HOLD, 'ctrl+alt+shift+o', 'SetRobotAngle', desc='จำมุมตอนนี้เป็นมุมอ้างอิง (ไม่ reset)'),
    Cmd(CAT_GYRO, 'ctrl+alt+g', 'FFcmG', 'speed cm act? dir?', desc='Gyro ตรงตามระยะ เร่ง/ผ่อน'),
    Cmd(CAT_GYRO, 'ctrl+alt+shift+g', 'BBcmG', 'speed cm act? dir?', desc='Gyro ถอยตรงตามระยะ เร่ง/ผ่อน'),
    Cmd(CAT_GYRO, 'ctrl+alt+h', 'FFcmGS', 'speed cm act? dir?', desc='Gyro ตรงตามระยะ ความเร็วคงที่'),
    Cmd(CAT_GYRO, 'ctrl+alt+shift+h', 'BBcmGS', 'speed cm act? dir?', desc='Gyro ถอยตรงตามระยะ ความเร็วคงที่'),
    Cmd(CAT_GYRO, 'ctrl+alt+v', 'FFtimerG', 'speed ms act? dir?', desc='Gyro ตรงตามเวลา ms'),
    Cmd(CAT_GYRO, 'ctrl+alt+shift+v', 'BBtimerG', 'speed ms act? dir?', desc='Gyro ถอยตรงตามเวลา ms'),
    Cmd(CAT_GYRO, 'ctrl+alt+b', 'FFBG', 'speed act dir?', desc='Gyro ตรงจนเซนเซอร์หน้าเจอเส้น'),
    Cmd(CAT_GYRO, 'ctrl+alt+shift+b', 'BBBG', 'speed act dir?', desc='Gyro ถอยตรงจนเซนเซอร์หลังเจอเส้น'),
    Cmd(CAT_HOLD, None, 'ToCenterG', desc='Gyro เดินตรงเข้ากลางหุ่น'),

    # ---------- Gyro หมุน/เลี้ยว: N / M (ทิศ), A D Q E (องศา), F (องศามีเครื่องหมาย) ----------
    Cmd(CAT_TURN, 'ctrl+alt+n', 'spinDirection', 'speed? dir', alias='sdg', desc='หมุนอยู่กับที่ไปทิศ dir'),
    Cmd(CAT_TURN, 'ctrl+alt+m', 'turnDirection', 'speed? dir', alias='tdg', desc='เลี้ยว(เดินหน้า)ล้อเดียวไปทิศ dir'),
    Cmd(CAT_TURN, 'ctrl+alt+shift+m', 'turnDirectionB', 'speed? dir', alias='tdbg', desc='เลี้ยว(ถอยหลัง)ล้อเดียวไปทิศ dir'),
    Cmd(CAT_TURN, 'ctrl+alt+a', 'SpinLG', 'speed? angle', desc='หมุนซ้ายอยู่กับที่ angle°'),
    Cmd(CAT_TURN, 'ctrl+alt+d', 'SpinRG', 'speed? angle', desc='หมุนขวาอยู่กับที่ angle°'),
    Cmd(CAT_TURN, 'ctrl+alt+q', 'TurnLG', 'speed? angle', desc='เลี้ยวซ้ายล้อเดียว (เดินหน้า)'),
    Cmd(CAT_TURN, 'ctrl+alt+e', 'TurnRG', 'speed? angle', desc='เลี้ยวขวาล้อเดียว (เดินหน้า)'),
    Cmd(CAT_TURN, 'ctrl+alt+shift+q', 'TurnLBG', 'speed? angle', desc='เลี้ยวซ้ายล้อเดียว (ถอยหลัง)'),
    Cmd(CAT_TURN, 'ctrl+alt+shift+e', 'TurnRBG', 'speed? angle', desc='เลี้ยวขวาล้อเดียว (ถอยหลัง)'),
    Cmd(CAT_TURN, 'ctrl+alt+f', 'spinDegree', 'speed? angle', desc='หมุนอยู่กับที่ angle° (+ขวา / -ซ้าย)'),
    Cmd(CAT_TURN, 'ctrl+alt+shift+f', 'turnDegree', 'speed? angle', desc='เลี้ยวหน้าล้อเดียว angle° (+ขวา / -ซ้าย)'),
    Cmd(CAT_TURN, None, 'turnDegreeB', 'speed? angle', desc='เลี้ยวถอยล้อเดียว angle° (+/-)'),

    # ---------- Gyro ขั้นสูง ----------
    Cmd(CAT_GYRO_ADV, None, 'turnDegree_none', 'speed? angle', btn='turnDeg_none', desc='เลี้ยวหน้า angle° ไม่เบรก (ต่อโค้ง)'),
    Cmd(CAT_GYRO_ADV, None, 'turnDegreeb_none', 'speed? angle', btn='turnDegb_none', desc='เลี้ยวถอย angle° ไม่เบรก'),
    Cmd(CAT_GYRO_ADV, None, 'turnDirection_none', 'speed? dir', btn='turnDir_none', alias='turndir_none', desc='เลี้ยวหน้าไปทิศ dir ไม่เบรก'),
    Cmd(CAT_GYRO_ADV, None, 'turnDirectionb_none', 'speed? dir', btn='turnDirb_none', alias='turndirb_none', desc='เลี้ยวถอยไปทิศ dir ไม่เบรก'),
    Cmd(CAT_GYRO_ADV, None, 'TurnLRG', 'speed? angle', desc='ตีโค้ง S เดินหน้า ซ้ายก่อนแล้วสวนขวา'),
    Cmd(CAT_GYRO_ADV, None, 'TurnRLG', 'speed? angle', desc='ตีโค้ง S เดินหน้า ขวาก่อนแล้วสวนซ้าย'),
    Cmd(CAT_GYRO_ADV, None, 'TurnLRBG', 'speed? angle', desc='ตีโค้ง S ถอยหลัง ซ้ายก่อนแล้วสวนขวา'),
    Cmd(CAT_GYRO_ADV, None, 'TurnRLBG', 'speed? angle', desc='ตีโค้ง S ถอยหลัง ขวาก่อนแล้วสวนซ้าย'),
    Cmd(CAT_GYRO_ADV, None, 'rotateDegree', 'L R angle', desc='โค้งกำหนดล้อ L,R จนหมุนครบ angle แล้วเบรก'),
    Cmd(CAT_GYRO_ADV, None, 'rotateDegree_none', 'L R angle', btn='rotateDeg_none', desc='โค้งกำหนดล้อ ครบ angle แล้วไหลต่อ'),
    Cmd(CAT_GYRO_ADV, None, 'rotateDir', 'L R act~ dir', desc="โค้งกำหนดล้อจนหันทิศ dir (+select / 'n' / 'f')"),
    Cmd(CAT_GYRO_ADV, None, 'rotateDir_none', 'L R dir', desc='โค้งกำหนดล้อจนหันทิศ dir แล้วไหลต่อ'),
    Cmd(CAT_GYRO_ADV, None, 'spin_ffcmg', 'speed cm act~ dir', desc='หมุนเข้าทิศ dir แล้ว Gyro วิ่งหน้า cm'),
    Cmd(CAT_GYRO_ADV, None, 'spin_bbcmg', 'speed cm act~ dir', desc='หมุนเข้าทิศ dir แล้ว Gyro ถอย cm'),
    Cmd(CAT_GYRO_ADV, None, 'turn_ffcmg', 'speed cm act~ dir', desc='เลี้ยวหน้าเข้าทิศ dir แล้ววิ่งหน้า cm'),
    Cmd(CAT_GYRO_ADV, None, 'turn_bbcmg', 'speed cm act~ dir', desc='เลี้ยวหน้าเข้าทิศ dir แล้วถอย cm'),
    Cmd(CAT_GYRO_ADV, None, 'turnb_ffcmg', 'speed cm act~ dir', desc='เลี้ยวถอยเข้าทิศ dir แล้ววิ่งหน้า cm'),
    Cmd(CAT_GYRO_ADV, None, 'turnb_bbcmg', 'speed cm act~ dir', desc='เลี้ยวถอยเข้าทิศ dir แล้วถอย cm'),

    # ---------- ตั้งทิศ / ค้างมุม ----------
    Cmd(CAT_HOLD, 'ctrl+alt+shift+n', 'resetAnglesDir', 'dir', desc='วางหุ่นหันทิศ dir แล้วรีเซ็ตมุม'),
    Cmd(CAT_HOLD, None, 'setAngleOffset', desc='ตั้งมุมตอนนี้เป็น 0 (เหมือน resetAngles)'),
    Cmd(CAT_HOLD, None, 'setHeading', 'dir', desc='ตั้งทิศที่ RunG จะล็อก (ไม่หมุนตัว)'),
    Cmd(CAT_HOLD, None, 'SetDirectionG', 'dir', desc='ตั้งทิศที่จะวิ่งตรงเข้าหา'),
    Cmd(CAT_HOLD, None, 'SetG', 'ms', desc='ค้างที่มุมอ้างอิง ms'),
    Cmd(CAT_HOLD, None, 'SetGB', 'ms', desc='ค้างที่มุมอ้างอิง (แบบถอย) ms'),
    Cmd(CAT_HOLD, None, 'SetFG', 'ms', desc='จำมุมตอนนี้แล้วค้าง ms'),
    Cmd(CAT_HOLD, None, 'SetBG', 'ms', desc='จำมุมตอนนี้แล้วค้าง (แบบถอย) ms'),

    # ---------- Servo: Ctrl+Alt+F1..F12 (ฟังก์ชันอยู่ใน Servo.ino ของสเก็ตช์ตัวอย่าง) ----------
    Cmd(CAT_SERVO, 'ctrl+alt+f1', 'Ready', raw='ServoOpen(); ServoUp();', desc='ท่าเตรียม: อ้า + ยก (ตามตัวอย่าง setup)'),
    Cmd(CAT_SERVO, 'ctrl+alt+f2', 'ServoUp', desc='ยกขึ้น'),
    Cmd(CAT_SERVO, 'ctrl+alt+f3', 'ServoUp45', desc='ยกครึ่งทาง'),
    Cmd(CAT_SERVO, 'ctrl+alt+f4', 'ServoDown', desc='วางลง'),
    Cmd(CAT_SERVO, 'ctrl+alt+f5', 'ServoOpen', desc='อ้า'),
    Cmd(CAT_SERVO, 'ctrl+alt+f6', 'ServoClose', desc='หนีบ'),
    Cmd(CAT_SERVO, 'ctrl+alt+f7', 'ServoLOpen', desc='อ้าเฉพาะซ้าย'),
    Cmd(CAT_SERVO, 'ctrl+alt+f8', 'ServoROpen', desc='อ้าเฉพาะขวา'),
    Cmd(CAT_SERVO, 'ctrl+alt+f9', 'ServoOpenMax', desc='อ้าสุด'),
    Cmd(CAT_SERVO, 'ctrl+alt+f10', 'ServoCloseSmall', desc='หนีบชิ้นเล็ก'),
    Cmd(CAT_SERVO, 'ctrl+alt+f11', 'ServoGrip', desc='หนีบแน่น (Close +15°)'),
    Cmd(CAT_SERVO, 'ctrl+alt+f12', 'ServoOpen2', desc='อ้าแบบที่ 2'),
    # ---------- Servo ท่าผสม: Ctrl+Alt+Shift+F1..F8 (พิมพ์ 2 คำสั่งในบรรทัดเดียว) ----------
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f1', 'Open→Down', raw='ServoOpen(); ServoDown();', desc='อ้า → วาง'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f2', 'Down→Open', raw='ServoDown(); ServoOpen();', desc='วาง → อ้า'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f3', 'Open→Up', raw='ServoOpen(); ServoUp();', desc='อ้า → ยก'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f4', 'Up→Open', raw='ServoUp(); ServoOpen();', desc='ยก → อ้า'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f5', 'Down→Close', raw='ServoDown(); ServoClose();', desc='วาง → หนีบ'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f6', 'Close→Down', raw='ServoClose(); ServoDown();', desc='หนีบ → วาง'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f7', 'Up→Close', raw='ServoUp(); ServoClose();', desc='ยก → หนีบ'),
    Cmd(CAT_SERVO2, 'ctrl+alt+shift+f8', 'Close→Up', raw='ServoClose(); ServoUp();', desc='หนีบ → ยก'),
    # ---------- Servo ทีละข้าง / อื่น ๆ ----------
    Cmd(CAT_SERVO1, None, 'ServoOpenMax2', desc='อ้าสุดแบบที่ 2'),
    Cmd(CAT_SERVO1, None, 'ServoLClose', desc='หนีบเฉพาะซ้าย'),
    Cmd(CAT_SERVO1, None, 'ServoRClose', desc='หนีบเฉพาะขวา'),
    Cmd(CAT_SERVO1, None, 'ServoLCloseSmall', desc='หนีบเล็กเฉพาะซ้าย'),
    Cmd(CAT_SERVO1, None, 'ServoRCloseSmall', desc='หนีบเล็กเฉพาะขวา'),
    Cmd(CAT_SERVO1, None, 'ServoLOpenMax', desc='อ้าสุดเฉพาะซ้าย'),
    Cmd(CAT_SERVO1, None, 'ServoROpenMax', desc='อ้าสุดเฉพาะขวา'),
    Cmd(CAT_SERVO1, None, 'ServoLOpenMax2', desc='อ้าสุดแบบ 2 เฉพาะซ้าย'),
    Cmd(CAT_SERVO1, None, 'ServoROpenMax2', desc='อ้าสุดแบบ 2 เฉพาะขวา'),
    Cmd(CAT_SERVO1, None, 'ServoWrite', 'n angle', desc='เซอร์โวเลข n (0 ยก/1 ซ้าย/2 ขวา หรือ 34-39) ไปมุม angle'),

    # ---------- มอเตอร์ / ออกตัว ----------
    Cmd(CAT_MOTOR, 'ctrl+alt+shift+s', 'MotorStop', desc='หยุดมอเตอร์ทันที'),
    Cmd(CAT_MOTOR, None, 'MotorStop', 'ms', desc='หยุดมอเตอร์แล้วหน่วง ms'),
    Cmd(CAT_MOTOR, None, 'Move', 'L R ms', desc='สั่งล้อซ้าย L ขวา R นาน ms'),
    Cmd(CAT_MOTOR, None, 'Motor', 'L R', desc='สั่งล้อซ้าย L ขวา R (ไม่หน่วง)'),
    Cmd(CAT_MOTOR, None, 'GoStart', 'speed', desc='วิ่งจนพ้นจุด Start'),
    Cmd(CAT_MOTOR, None, 'GoEnd', 'speed', desc='วิ่งจนถึงจุด Finish'),
    Cmd(CAT_MOTOR, None, 'TestMotor', desc='ทดสอบมอเตอร์ ซ้ายแล้วขวา'),

    # ---------- ตั้งค่า / เซนเซอร์ (ตัวเลขตามสเก็ตช์ตัวอย่าง แก้ต่อใน IDE) ----------
    Cmd(CAT_SETUP, None, '#include', raw='#include <UnknowRobot_STORMXII_V3_BNO085.h>', desc='include ไลบรารี (บนสุดของไฟล์)'),
    Cmd(CAT_SETUP, None, 'RobotSetup', desc='เริ่มระบบทั้งหมด (บรรทัดแรกของ setup)'),
    Cmd(CAT_SETUP, None, 'LoadCalibrateFromEEPROM', btn='LoadCalib', desc='โหลดค่าคาลิเบรตจาก EEPROM'),
    Cmd(CAT_SETUP, None, 'CalibrateSensor', btn='Calibrate', desc='คาลิเบรตเซนเซอร์ แล้วเซฟ EEPROM'),
    Cmd(CAT_SETUP, None, 'swOK', desc='รอกด OK (กด START = คาลิเบรต)'),
    Cmd(CAT_SETUP, None, 'swSTART', desc='รอกด START'),
    Cmd(CAT_SETUP, None, 'SerialCalibrate_AllSensor', btn='SerialCalib', desc='Serial: ค่าคาลิเบรตทุกเซนเซอร์'),
    Cmd(CAT_SETUP, None, 'SerialPositionFB', btn='SerialPos', desc='Serial: ตำแหน่งเส้น หน้า/หลัง'),
    Cmd(CAT_SETUP, None, 'TrackLineColor', raw='TrackLineColor(BLACK);', desc='สีเส้น BLACK / WHITE'),
    Cmd(CAT_SETUP, None, 'RefLineValue', raw='RefLineValue(500);', desc='ค่าแบ่งขาว/ดำ หน้า-หลัง'),
    Cmd(CAT_SETUP, None, 'RefCenterLineValue', btn='RefCenter', raw='RefCenterLineValue(500);', desc='ค่าแบ่งขาว/ดำ คู่กลาง'),
    Cmd(CAT_SETUP, None, 'SetRobotPID', raw='SetRobotPID(0.009, 0.12);', desc='KP, KD หลักของการวิ่งตามเส้น'),
    Cmd(CAT_SETUP, None, 'SetSensorTrackLine_CH', btn='TrackLine_CH', raw='SetSensorTrackLine_CH(16);', desc='จำนวนเซนเซอร์จับแยก 6-16'),
    Cmd(CAT_SETUP, None, 'set_sensor_track_line', btn='track_line', raw='set_sensor_track_line(0, 15);', desc='ช่วงเซนเซอร์ที่ใช้วิ่ง'),
    Cmd(CAT_SETUP, None, 'set_line_center', btn='line_center', raw='set_line_center(1);', desc='เข้ากลาง 0 = เดินตรง, 1 = ตามเส้น'),
    Cmd(CAT_SETUP, None, 'ModeSpdPID', raw='ModeSpdPID(1, 100, -100);', desc='โหมดจำกัดกำลังล้อ (ตามเส้น)'),
    Cmd(CAT_SETUP, None, 'ModeSpdGyro', btn='ModeGyro', raw='ModeSpdGyro(4, 100, -5);', desc='โหมดจำกัดกำลังล้อ (Gyro)'),
    Cmd(CAT_SETUP, None, 'SetTurnSpeed', raw='SetTurnSpeed(50);', desc='ความเร็ว SpinL/SpinR ที่ไม่ใส่ speed'),
    Cmd(CAT_SETUP, None, 'SetToCenterSpeed', btn='ToCenterSpd', raw='SetToCenterSpeed(30);', desc='ความเร็วเดินเข้ากลางหุ่น'),
    Cmd(CAT_SETUP, None, 'SetGyroRun', raw='SetGyroRun(0.25, 2.5);', desc='kp, kd วิ่งตรงด้วย Gyro'),
    Cmd(CAT_SETUP, None, 'SetGyroSpin', raw='SetGyroSpin(1.3, 0.8, 65, 20, 15.0, 1.0);', desc='ค่าหมุนอยู่กับที่ด้วย Gyro'),
    Cmd(CAT_SETUP, None, 'SetGyroTurn', raw='SetGyroTurn(1.3, 0.8, 65, 20, 15.0, 1.0);', desc='ค่าเลี้ยวล้อเดียวด้วย Gyro'),
    Cmd(CAT_SETUP, None, 'set_auto_align', btn='auto_align', raw='set_auto_align(20);', desc='คลาดเกิน 20° หมุนตั้งลำก่อน (0 = ปิด)'),
    Cmd(CAT_SETUP, None, 'set_track_snap90', btn='snap90', raw='set_track_snap90(true);', desc='ปัดมุมเข้าแกน 90° ที่ทางแยก'),

    # ---------- กำหนดเอง (แก้/เพิ่มได้ตามใจ) ----------
    Cmd(CAT_CUSTOM, 'ctrl+alt+shift+0', 'FFC เร็ว', raw="FFC({fast}, 'p');", desc='FFC ความเร็ว FAST_SPEED'),
    Cmd(CAT_CUSTOM, 'ctrl+alt+shift+9', 'FFC ช้า', raw="FFC({slow}, 'c');", desc='FFC ความเร็ว SLOW_SPEED'),
    Cmd(CAT_CUSTOM, 'ctrl+alt+shift+8', 'delay(ms)', raw='delay({ms});', desc='หน่วงเวลา (Arduino)'),
]

# แท็บปุ่มคำสั่งในหน้าต่าง: (ชื่อแท็บ, หมวด, จำนวนคอลัมน์)  None = แท็บปรับค่า/ระบบ
# จัดให้แต่ละแท็บไม่เกิน ~5 แถว เพื่อให้หน้าต่างพอดีจอ 1080p เหมือนเดิม (ไม่ถูกบังคับเป็นโหมดย่อ)
TABS = [
    ('เส้น', [CAT_LINE, CAT_DIST], 6),
    ('หมุน/กลาง', [CAT_SPIN_LINE, CAT_CENTER], 6),
    ('โค้ง', [CAT_CURVE], 4),
    ('ทิศ/องศา', [CAT_DIR_LINE, CAT_DIR_G, CAT_DEG], 6),
    ('Gyro', [CAT_GYRO, CAT_TURN], 5),
    ('Gyro+', [CAT_GYRO_ADV], 5),
    ('ทิศ/ค้าง', [CAT_HOLD, CAT_MOTOR], 5),
    ('Servo', [CAT_SERVO, CAT_SERVO2], 5),
    ('Servo+', [CAT_SERVO1], 5),
    ('ตั้งค่า', [CAT_SETUP, CAT_CUSTOM], 6),
    ('ค่า/ระบบ', None, 5),
]
SERVO_CATS = (CAT_SERVO, CAT_SERVO1)

# ตรวจช่วงค่า n ตามคำสั่ง (ไลบรารีไม่เช็กให้ เช่น FFNUM อ่าน F[n] ตรง ๆ) -> ค่านอกช่วงจะไม่พิมพ์ และขึ้นเตือน
N_VALID = {
    'FFNUM': (lambda v: 0 <= v <= 15, 'ตำแหน่งเซนเซอร์ 0-15'),
    'BBNUM': (lambda v: 0 <= v <= 15, 'ตำแหน่งเซนเซอร์ 0-15'),
    'FFSUM': (lambda v: 0 < v <= 16000, 'ผลรวม 1-16000 (เช่น 4000)'),
    'BBSUM': (lambda v: 0 < v <= 16000, 'ผลรวม 1-16000 (เช่น 4000)'),
    'BalanceF': (lambda v: 1 <= v <= 20, 'จำนวนครั้ง 1-20'),
    'BalanceB': (lambda v: 1 <= v <= 20, 'จำนวนครั้ง 1-20'),
    'BalanceFC': (lambda v: 1 <= v <= 20, 'จำนวนครั้ง 1-20'),
    'BalanceBC': (lambda v: 1 <= v <= 20, 'จำนวนครั้ง 1-20'),
    'ServoWrite': (lambda v: v in (0, 1, 2) or 34 <= v <= 39, 'เลขเซอร์โว 0/1/2 หรือ 34-39'),
}
# ทิศอยู่ในชื่อคำสั่งแล้ว -> angle ต้องเป็นบวก (ติดลบจะหมุนผิดทาง)
POSITIVE_ANGLE = {'SpinLG', 'SpinRG', 'TurnLG', 'TurnRG', 'TurnLBG', 'TurnRBG',
                  'TurnLRG', 'TurnRLG', 'TurnLRBG', 'TurnRLBG', 'rotateDegree', 'rotateDegree_none'}

# คำสั่งปรับค่า (ไม่พิมพ์ลง IDE)  id -> (hotkey, ป้าย)
PARAM_ACTIONS = [
    ('speed+', 'ctrl+alt+=', f'speed +{SPEED_STEP}'),
    ('speed-', 'ctrl+alt+-', f'speed -{SPEED_STEP}'),
    ('speed_slow', 'ctrl+alt+8', f'speed = SLOW ({SLOW_SPEED})'),
    ('speed_def', 'ctrl+alt+9', f'speed = DEFAULT ({DEFAULT_SPEED})'),
    ('speed_fast', 'ctrl+alt+0', f'speed = FAST ({FAST_SPEED})'),
    ('cm+', 'ctrl+alt+]', f'cm +{CM_STEP}'),
    ('cm-', 'ctrl+alt+[', f'cm -{CM_STEP}'),
    ('ms+', 'ctrl+alt+shift+]', f'ms +{MS_STEP}'),
    ('ms-', 'ctrl+alt+shift+[', f'ms -{MS_STEP}'),
    ('dir0', 'ctrl+alt+i', 'dir = 0   (I = บน)'),
    ('dir90', 'ctrl+alt+l', 'dir = 90  (L = ขวา)'),
    ('dir180', 'ctrl+alt+k', 'dir = 180 (K = ล่าง)'),
    ('dir270', 'ctrl+alt+j', 'dir = 270 (J = ซ้าย)'),
    ('act_p', 'ctrl+alt+p', "act = 'p' ผ่านแยก"),
    ('act_c', 'ctrl+alt+c', "act = 'c' เข้ากลาง"),
    ('act_s', 'ctrl+alt+s', "act = 's' หยุด"),
    ('act_l', 'ctrl+alt+,', "act = 'l' (, = <)"),
    ('act_r', 'ctrl+alt+.', "act = 'r' (. = >)"),
    ('act_next', 'ctrl+alt+/', 'act ตัวถัดไป'),
    ('act_prev', 'ctrl+alt+shift+/', 'act ตัวก่อนหน้า'),
    ('act_case', 'ctrl+alt+u', 'act สลับเล็ก/ใหญ่ (p↔P)'),
    ('repeat', 'ctrl+alt+r', 'พิมพ์คำสั่งล่าสุดซ้ำ (ค่าปัจจุบัน)'),
    ('pause', 'ctrl+alt+shift+p', 'หยุด/เปิด มาโครชั่วคราว'),
    ('window', 'ctrl+alt+shift+w', 'ซ่อน/แสดงหน้าต่าง'),
    ('exit', EXIT_HOTKEY, 'ปิดโปรแกรม'),
]

# ป้ายสั้นบนปุ่มแท็บ "ค่า/ระบบ" (ตารางใน README ใช้ป้ายเต็มด้านบน)
PARAM_SHORT = {
    'speed+': f'speed +{SPEED_STEP}', 'speed-': f'speed -{SPEED_STEP}',
    'speed_slow': f'SLOW {SLOW_SPEED}', 'speed_def': f'DEF {DEFAULT_SPEED}', 'speed_fast': f'FAST {FAST_SPEED}',
    'cm+': f'cm +{CM_STEP}', 'cm-': f'cm -{CM_STEP}', 'ms+': f'ms +{MS_STEP}', 'ms-': f'ms -{MS_STEP}',
    'dir0': 'dir 0', 'dir90': 'dir 90', 'dir180': 'dir 180', 'dir270': 'dir 270',
    'act_p': "'p'", 'act_c': "'c'", 'act_s': "'s'", 'act_l': "'l'", 'act_r': "'r'",
    'act_next': 'act ถัดไป', 'act_prev': 'act ก่อน', 'act_case': 'เล็ก↔ใหญ่',
    'repeat': 'พิมพ์ซ้ำ', 'pause': 'หยุดชั่วคราว', 'window': 'ซ่อนจอ', 'exit': 'ปิดโปรแกรม',
}

# ============================================================================
# 4) แปลงข้อความคีย์ลัด -> (modifiers, virtual-key)  [อิงตำแหน่งปุ่ม ใช้ได้ทั้งแป้นไทย/อังกฤษ]
# ============================================================================
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
MOD_NAMES = {'alt': MOD_ALT, 'ctrl': MOD_CONTROL, 'control': MOD_CONTROL, 'shift': MOD_SHIFT, 'win': MOD_WIN}

VK_NAMES = {str(d): 0x30 + d for d in range(10)}
VK_NAMES.update({chr(c): c for c in range(ord('A'), ord('Z') + 1)})
VK_NAMES.update({chr(c).lower(): c for c in range(ord('A'), ord('Z') + 1)})
VK_NAMES.update({f'f{n}': 0x6F + n for n in range(1, 13)})
VK_NAMES.update({
    '-': 0xBD, '=': 0xBB, '[': 0xDB, ']': 0xDD, ';': 0xBA, "'": 0xDE,
    ',': 0xBC, '.': 0xBE, '/': 0xBF, '`': 0xC0, '\\': 0xDC,
    'space': 0x20, 'insert': 0x2D, 'home': 0x24, 'pageup': 0x21, 'pagedown': 0x22,
})


def parse_hotkey(text):
    """'ctrl+alt+shift+1' -> (mods, vk)  ('+' ตัวสุดท้ายถือเป็นปุ่ม '=' ไม่ได้ ใช้ชื่อปุ่มตรง ๆ)"""
    parts = [p.strip().lower() for p in text.split('+')]
    mods = 0
    for p in parts[:-1]:
        if p not in MOD_NAMES:
            raise ValueError(f'ไม่รู้จัก modifier "{p}" ใน "{text}"')
        mods |= MOD_NAMES[p]
    key = parts[-1]
    if key not in VK_NAMES:
        raise ValueError(f'ไม่รู้จักปุ่ม "{key}" ใน "{text}"')
    return mods, VK_NAMES[key]


def key_on_button(hk):
    """ป้ายคีย์ลัดท้ายปุ่ม: Ctrl+Alt ละไว้ (ทุกคำสั่งใช้ Ctrl+Alt) เช่น ctrl+alt+t -> T, ctrl+alt+shift+t -> S+T"""
    if not hk.startswith('ctrl+alt+'):
        return pretty_hotkey(hk, short=True)
    rest = hk[len('ctrl+alt+'):]
    if rest.startswith('shift+'):
        return 'S+' + rest[len('shift+'):].upper()
    return rest.upper()


def pretty_hotkey(text, short=False):
    parts = text.split('+')
    if short:
        m = ''.join({'ctrl': 'C', 'alt': 'A', 'shift': 'S', 'win': 'W'}[p] for p in parts[:-1])
        key = {'space': 'SPC'}.get(parts[-1], parts[-1].upper())
        return f'{m}+{key}'
    return '+'.join(p.capitalize() if len(p) > 1 else p.upper() for p in parts)


# ============================================================================
# 5) การ render โค้ด
# ============================================================================
def fmt_number(v):
    f = float(v)
    return str(int(f)) if f.is_integer() else ('%g' % f)


def render(cmd, p, opts):
    """p = dict(speed, cm, ms, dir, angle, act, n, L, R) ที่ตรวจแล้ว
    opts = dict(alias, opt_act, opt_dir, opt_speed)
    act = None/'' หมายถึงปุ่ม None (ไม่ใส่ตัวอักษร)
    ถ้าคำสั่งบังคับต้องมี select แต่เลือก None จะ raise ValueError (ยกเว้น act! ที่ใช้ FORCED_ACTION)
    ไลบรารีแยก overload ด้วยชนิด (char = select, int = dir) จึงตัด optional แต่ละตัวได้อิสระ"""
    act = p.get('act') or None
    if cmd.raw:
        if '{act}' in cmd.raw and not act:
            raise ValueError(f'"{cmd.name}" ต้องมี select (เลือกปุ่มตัวอักษรแทน None)')
        return cmd.raw.format(
            speed=fmt_number(p['speed']), cm=fmt_number(p['cm']), ms=fmt_number(p['ms']),
            dir=fmt_number(p['dir']), angle=fmt_number(p['angle']), act=f"'{act}'" if act else '',
            n=fmt_number(p['n']), L=fmt_number(p['L']), R=fmt_number(p['R']),
            fast=FAST_SPEED, slow=SLOW_SPEED, default=DEFAULT_SPEED)

    name = cmd.alias if (opts.get('alias') and cmd.alias) else cmd.name
    if 'n' in cmd.params and cmd.name in N_VALID:
        check, need = N_VALID[cmd.name]
        if not check(p['n']):
            raise ValueError(f'{name}: n = {fmt_number(p["n"])} ใช้ไม่ได้ ต้องเป็น{need}')
    if 'angle' in cmd.params and cmd.name in POSITIVE_ANGLE and p['angle'] < 0:
        raise ValueError(f'{name}: angle ต้องเป็นบวก (ทิศอยู่ในชื่อคำสั่งแล้ว) — ใช้ spinDegree/turnDegree ถ้าต้องการ +/-')
    flags = {
        'act': opts.get('opt_act', True) and bool(act),
        'dir': opts.get('opt_dir', False),
        'speed': opts.get('opt_speed', True),
    }
    args = []
    for tok in cmd.params:
        base, mod = (tok[:-1], tok[-1]) if tok[-1] in '?~!' else (tok, '')
        if mod == '?' and not flags.get(base, False):
            continue
        if mod == '~' and not act:
            continue
        if base == 'act':
            a = act or (FORCED_ACTION if mod == '!' else None)
            if not a:
                raise ValueError(f'{name} ต้องมี select (เลือกปุ่มตัวอักษรแทน None)')
            args.append(f"'{a}'")
        elif base == 'cmi':                       # ชุด FFcmCirCle* รับ cm แบบ int เท่านั้น
            args.append(str(int(float(p['cm']) + 0.5)))   # ปัดเศษครึ่งขึ้น (cm ไม่ติดลบ)
        else:
            args.append(fmt_number(p[base]))
    return f"{name}({', '.join(args)});"


# ============================================================================
# 6) Win32: ส่งปุ่ม / Clipboard / หน้าต่าง
# ============================================================================
IS_WINDOWS = sys.platform == 'win32'
if IS_WINDOWS:
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
    user32.keybd_event.restype = None
    user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    user32.MapVirtualKeyW.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    kernel32.GetConsoleWindow.restype = wintypes.HWND

WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x1, 0x2
VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN = 0x10, 0x11, 0x12, 0x5B, 0x5C
VK_END, VK_RETURN, VK_V, VK_MASK = 0x23, 0x0D, 0x56, 0xE8  # 0xE8 = ปุ่มว่าง ใช้กันเมนู Alt/สลับภาษา
EXTENDED_VKS = {VK_END, 0x24, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E}
IGNORED_TARGET_CLASSES = {'Shell_TrayWnd', 'Shell_SecondaryTrayWnd', 'Progman', 'WorkerW',
                          'ConsoleWindowClass', 'CASCADIA_HOSTING_WINDOW_CLASS',
                          # หน้าต่างของ Windows เอง (thumbnail ทาสก์บาร์, Start, Alt+Tab, ถาด icon)
                          'XamlExplorerHostIslandWindow', 'Windows.UI.Core.CoreWindow', 'TaskListThumbnailWnd',
                          'MultitaskingViewFrame', 'ForegroundStaging', 'NotifyIconOverflowWindow',
                          'TopLevelWindowForOverflowXamlIsland', 'Shell_InputSwitchTopLevelWindow'}


def key_down(vk):
    flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else 0
    user32.keybd_event(vk, user32.MapVirtualKeyW(vk, 0) & 0xFF, flags, 0)


def key_up(vk):
    flags = (KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else 0) | KEYEVENTF_KEYUP
    user32.keybd_event(vk, user32.MapVirtualKeyW(vk, 0) & 0xFF, flags, 0)


def tap(vk, *mods):
    for m in mods:
        key_down(m)
        time.sleep(KEY_GAP / 2)
    key_down(vk)
    key_up(vk)
    for m in reversed(mods):
        time.sleep(KEY_GAP / 2)
        key_up(m)
    time.sleep(KEY_GAP)


def modifiers_down():
    return any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN))


def wait_modifiers_released(timeout):
    end = time.time() + timeout
    while modifiers_down():
        if time.time() > end:
            return False
        time.sleep(0.01)
    time.sleep(0.03)
    return True


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_pid(hwnd):
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def is_own_window(hwnd):
    return bool(hwnd) and window_pid(hwnd) == os.getpid()


def is_valid_target(hwnd):
    if not hwnd or not user32.IsWindow(hwnd) or is_own_window(hwnd):
        return False
    if hwnd == kernel32.GetConsoleWindow():
        return False
    return window_class(hwnd) not in IGNORED_TARGET_CLASSES


def focus_window(hwnd):
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    for _ in range(25):
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.01)
    # วิธีสำรอง: ผูก input thread ชั่วคราวแล้วสั่งอีกครั้ง
    fg = user32.GetForegroundWindow()
    cur = kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    if fg_thread and fg_thread != cur:
        user32.AttachThreadInput(cur, fg_thread, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    if fg_thread and fg_thread != cur:
        user32.AttachThreadInput(cur, fg_thread, False)
    time.sleep(0.05)
    return user32.GetForegroundWindow() == hwnd


# ---- Clipboard: ใช้ pyperclip ถ้ามี ไม่มีก็ใช้ Win32 API ตรง ----
CF_UNICODETEXT, GMEM_MOVEABLE = 13, 0x0002
try:
    import pyperclip  # noqa: E402
except Exception:  # pragma: no cover
    pyperclip = None


def _open_clipboard():
    for _ in range(50):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.01)
    return False


def _win_clip_get():
    if not _open_clipboard():
        raise RuntimeError('เปิด Clipboard ไม่ได้ (โปรแกรมอื่นใช้อยู่)')
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ''
        ptr = kernel32.GlobalLock(h)
        if not ptr:
            return ''
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def _win_clip_set(text):
    data = text.encode('utf-16-le') + b'\x00\x00'
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not h:
        raise RuntimeError('GlobalAlloc ล้มเหลว')
    ptr = kernel32.GlobalLock(h)
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(h)
    if not _open_clipboard():
        kernel32.GlobalFree(h)
        raise RuntimeError('เปิด Clipboard ไม่ได้ (โปรแกรมอื่นใช้อยู่)')
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, h):
            kernel32.GlobalFree(h)
            raise RuntimeError('SetClipboardData ล้มเหลว')
    finally:
        user32.CloseClipboard()


def clip_get():
    try:
        return pyperclip.paste() if pyperclip else _win_clip_get()
    except Exception:
        return None


def clip_set(text):
    if pyperclip:
        pyperclip.copy(text)
    else:
        _win_clip_set(text)


# ============================================================================
# 7) ตัวพิมพ์ (worker thread) — ทำงานทีละงานตามคิว
# ============================================================================
class Typer(threading.Thread):
    def __init__(self, ui_queue):
        super().__init__(daemon=True)
        self.jobs = queue.Queue()
        self.ui_queue = ui_queue
        self.last_target = None   # hwnd หน้าต่าง IDE ล่าสุด (main thread อัปเดต)
        self._clip_lock = threading.Lock()
        self._clip_gen = 0        # เพิ่มทุกครั้งที่เราตั้ง Clipboard
        self._clip_saved = None   # Clipboard เดิมของผู้ใช้ที่รอคืน (None = ไม่มีงานค้าง)

    def submit(self, text, opts):
        self.jobs.put((text, opts))

    def stop(self):
        self.jobs.put(None)

    def status(self, msg, ok=True):
        self.ui_queue.put(('status', msg, ok))

    def run(self):
        while True:
            job = self.jobs.get()
            if job is None:
                return
            text, opts = job
            try:
                self.type_text(text, opts)
            except Exception as exc:  # ไม่ให้ thread ตาย
                self.status(f'พิมพ์ไม่สำเร็จ: {exc}', ok=False)

    def type_text(self, text, opts):
        if not wait_modifiers_released(MODIFIER_RELEASE_TIMEOUT):
            self.status('ยกเลิก: ยังกด Ctrl/Alt/Shift ค้างอยู่ — ปล่อยปุ่มแล้วกดใหม่', ok=False)
            return
        fg = user32.GetForegroundWindow()
        if not is_valid_target(fg):
            target = self.last_target
            if not target or not user32.IsWindow(target):
                self.status('ยังไม่รู้ว่าจะพิมพ์ลงหน้าต่างไหน — คลิกที่ IDE ก่อน 1 ครั้ง', ok=False)
                return
            if not self._ensure_focus(target):
                self.status('สลับไปหน้าต่าง IDE ไม่ได้ — คลิกที่ IDE แล้วใช้คีย์ลัดแทน', ok=False)
                return

        if opts['end']:
            tap(VK_END)

        if opts['method'] == 'unicode':
            import keyboard  # ใช้เฉพาะโหมด unicode
            keyboard.write(text, delay=0.003, exact=True)
            time.sleep(PASTE_SETTLE)
        else:
            with self._clip_lock:
                # เก็บ Clipboard เดิมเฉพาะตอนที่ไม่มีงานคืนค่าค้างอยู่ (กดรัวหลายคำสั่ง -> ของเดิมจริงไม่หาย)
                if RESTORE_CLIPBOARD and self._clip_saved is None:
                    self._clip_saved = clip_get() or ''
                clip_set(text)
                self._clip_gen += 1
                gen = self._clip_gen
            time.sleep(0.03)
            tap(VK_V, VK_CONTROL)
            time.sleep(PASTE_SETTLE)
            if RESTORE_CLIPBOARD:
                threading.Timer(CLIPBOARD_RESTORE_DELAY, self._restore_clip, args=(gen, text)).start()

        if opts['enter']:
            tap(VK_RETURN)
        self.status(f'✓ {text}')

    @staticmethod
    def _ensure_focus(target):
        """สลับกลับไป IDE แล้วยืนยันว่าเป็น Foreground จริง 'หลัง' รอ FOCUS_DELAY ก่อนส่งคีย์
        (เดิมเช็กครั้งเดียวก่อนรอ — ถ้าหน้าต่าง Macro แย่ง Focus คืนระหว่างรอ คีย์จะไปผิดที่/ตกหล่น)"""
        for _ in range(FOCUS_RETRIES):
            if focus_window(target):
                time.sleep(FOCUS_DELAY)
                if user32.GetForegroundWindow() == target:
                    return True
            time.sleep(0.05)
        return False

    def _restore_clip(self, gen, ours):
        with self._clip_lock:
            if gen != self._clip_gen:   # มีงานใหม่ตั้ง Clipboard ต่อแล้ว -> ให้งานล่าสุดเป็นคนคืน
                return
            old, self._clip_saved = self._clip_saved, None
            try:
                if old and clip_get() == ours:   # ถ้าผู้ใช้ copy อย่างอื่นไปแล้วจะไม่ทับ
                    clip_set(old)
            except Exception:
                pass


# ============================================================================
# 8) Hotkey thread (Win32 RegisterHotKey + message loop)
# ============================================================================
class HotkeyThread(threading.Thread):
    def __init__(self, bindings, ui_queue):
        """bindings: list ของ (hotkey_text, action_id)"""
        super().__init__(daemon=True)
        self.bindings = bindings
        self.ui_queue = ui_queue
        self.thread_id = None
        self.ready = threading.Event()
        self.failed = []

    def run(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        id_map = {}
        for i, (hk, action) in enumerate(self.bindings, start=1):
            mods, vk = parse_hotkey(hk)
            if user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk):
                id_map[i] = (action, mods)
            else:
                self.failed.append(hk)
        self.ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam in id_map:
                    action, mods = id_map[msg.wParam]
                    # กด "ปุ่มว่าง" คั่น ขณะที่ผู้ใช้ยังกด modifier อยู่
                    # -> กัน Alt เปิดเมนูของ IDE และกัน Alt+Shift / Ctrl+Shift สลับภาษา
                    user32.keybd_event(VK_MASK, 0, 0, 0)
                    user32.keybd_event(VK_MASK, 0, KEYEVENTF_KEYUP, 0)
                    self.ui_queue.put(('hotkey', action))
        finally:
            for i in id_map:
                user32.UnregisterHotKey(None, i)

    def stop(self):
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


# ============================================================================
# 9) หน้าต่าง GUI (Always-on-Top)
# ============================================================================
def build_app(start_hotkeys=True):
    import tkinter as tk
    from tkinter import ttk

    class App:
        def __init__(self):
            self.ui_queue = queue.Queue()
            self.root = tk.Tk()
            self.root.title('Robot Macro')
            self.root.attributes('-topmost', ALWAYS_ON_TOP)
            try:
                self.root.attributes('-alpha', WINDOW_ALPHA)
            except tk.TclError:
                pass
            self.root.protocol('WM_DELETE_WINDOW', self.quit)
            self.cmds = {c.id: c for c in MACROS}
            self.last_cmd_id = None
            self.paused = tk.BooleanVar(value=False)
            self.typer = Typer(self.ui_queue)
            self.hotkeys = None

            # --- ตัวแปรค่าพารามิเตอร์ (StringVar เพื่อให้พิมพ์แก้ได้อิสระ) ---
            self.v_speed = tk.StringVar(value=str(DEFAULT_SPEED))
            self.v_cm = tk.StringVar(value=str(DEFAULT_CM))
            self.v_ms = tk.StringVar(value=str(DEFAULT_MS))
            self.v_dir = tk.StringVar(value=str(DEFAULT_DIR))
            self.v_angle = tk.StringVar(value=str(DEFAULT_ANGLE))
            self.v_act = tk.StringVar(value=DEFAULT_ACTION)
            self.v_n = tk.StringVar(value=str(DEFAULT_N))
            self.v_L = tk.StringVar(value=str(DEFAULT_L))
            self.v_R = tk.StringVar(value=str(DEFAULT_R))
            self.v_opt_speed = tk.BooleanVar(value=OPT_SPEED_INCLUDE)
            self.v_end = tk.BooleanVar(value=PRESS_END_BEFORE)
            self.v_enter = tk.BooleanVar(value=PRESS_ENTER_AFTER)
            self.v_alias = tk.BooleanVar(value=USE_SHORT_ALIAS)
            self.v_opt_act = tk.BooleanVar(value=GYRO_INCLUDE_ACT)
            self.v_opt_dir = tk.BooleanVar(value=GYRO_INCLUDE_DIR)
            self.v_top = tk.BooleanVar(value=ALWAYS_ON_TOP)
            self.v_compact = tk.BooleanVar(value=False)
            self.v_status = tk.StringVar(value='พร้อม — คลิกที่ IDE แล้วกดคีย์ลัดได้เลย')
            self.v_preview = tk.StringVar(value='')
            self.v_target = tk.StringVar(value='เป้าหมาย: -')
            self.v_actinfo = tk.StringVar(value='')
            self._hover_job = None   # after-id ของ hover preview ที่รออยู่ (debounce)

            self._build_ui()
            self.v_act.trace_add('write', lambda *a: self._on_act_change())
            self.v_alias.trace_add('write', lambda *a: self._refresh_button_labels())
            # Live Preview อัปเดตทันทีเมื่อเปลี่ยนค่าใดก็ได้
            for var in (self.v_speed, self.v_cm, self.v_ms, self.v_dir, self.v_angle,
                        self.v_n, self.v_L, self.v_R,
                        self.v_alias, self.v_opt_act, self.v_opt_dir, self.v_opt_speed):
                var.trace_add('write', lambda *a: self._live_preview())
            self._on_act_change()

            self.typer.start()
            if start_hotkeys:
                self._start_hotkeys()
            self.root.after(30, self._poll_queue)
            self.root.after(200, self._poll_foreground)

        # ------------------------------------------------------------ UI
        def _build_ui(self):
            root = self.root
            style = ttk.Style(root)
            style.configure('TButton', font=UI_FONT, padding=(2, 1))
            style.configure('Code.TButton', font=('Consolas', 9), padding=(2, 1))
            style.configure('Small.TButton', font=UI_FONT, padding=(0, 0), width=5)
            style.configure('Left.TButton', font=UI_FONT, padding=(4, 0), anchor='w')
            style.configure('TLabel', font=UI_FONT)
            style.configure('TCheckbutton', font=UI_FONT)
            style.configure('Status.TLabel', font=('Segoe UI', 10))
            style.configure('Preview.TLabel', font=CODE_FONT)

            outer = ttk.Frame(root, padding=6)
            outer.pack(fill='both', expand=True)

            # ---- แถวบน: สถานะ ----
            top = ttk.Frame(outer)
            top.pack(fill='x')
            self.lbl_mode = tk.Label(top, text=' ON ', bg='#1f9d55', fg='white', font=('Segoe UI', 9, 'bold'))
            self.lbl_mode.pack(side='left')
            # ปุ่มเด่น resetAngles (ใช้บ่อยตอนตั้งลำ/เช็กพอยต์)
            tk.Button(top, text='⟲ resetAngles()   C+A+O', bg='#0f766e', fg='white',
                      activebackground='#115e59', activeforeground='white', relief='flat', bd=0,
                      font=('Segoe UI', 9, 'bold'), padx=8, cursor='hand2', takefocus=0,
                      command=lambda: self.run_cmd('cmd:ctrl+alt+o', from_button=True)).pack(side='left', padx=(6, 0))
            # width=1 + expand: ชื่อหน้าต่างเป้าหมายยาว/สั้น ไม่ดันความกว้างหน้าต่าง (ปุ่มไม่ไหลตาม)
            ttk.Label(top, textvariable=self.v_target, foreground='#555', width=1).pack(
                side='left', padx=6, fill='x', expand=True)
            ttk.Checkbutton(top, text='ย่อ', variable=self.v_compact, command=self._toggle_compact,
                            takefocus=0).pack(side='right')
            ttk.Checkbutton(top, text='บนสุด', variable=self.v_top, takefocus=0,
                            command=lambda: self.root.attributes('-topmost', self.v_top.get())).pack(side='right')

            # ---- ค่าพารามิเตอร์ ----
            pf = ttk.LabelFrame(outer, text=' ค่าที่ใช้พิมพ์ (แก้สด ๆ ได้) ', padding=4)
            pf.pack(fill='x', pady=(4, 2))

            def spin_row(row, label, var, lo, hi, step, presets=()):
                ttk.Label(pf, text=label, width=7).grid(row=row, column=0, sticky='w')
                sb = ttk.Spinbox(pf, textvariable=var, from_=lo, to=hi, increment=step, width=7, font=CODE_FONT)
                sb.grid(row=row, column=1, sticky='w', padx=2)
                col = 2
                for text, value in presets:
                    ttk.Button(pf, text=text, style='Small.TButton', takefocus=0,
                               command=lambda v=value: var.set(str(v))).grid(row=row, column=col, padx=1)
                    col += 1

            spin_row(0, 'speed', self.v_speed, SPEED_MIN, SPEED_MAX, SPEED_STEP,
                     [(str(SLOW_SPEED), SLOW_SPEED), (str(DEFAULT_SPEED), DEFAULT_SPEED), (str(FAST_SPEED), FAST_SPEED), ('100', 100)])
            spin_row(1, 'cm', self.v_cm, 0, 500, CM_STEP, [('5', 5), ('10', 10), ('20', 20), ('30', 30)])
            spin_row(2, 'ms', self.v_ms, 0, 10000, MS_STEP, [('100', 100), ('300', 300), ('500', 500), ('1000', 1000)])
            spin_row(3, 'angle', self.v_angle, -360, 360, ANGLE_STEP, [('45', 45), ('90', 90), ('135', 135), ('180', 180)])

            ttk.Label(pf, text='dir', width=7).grid(row=4, column=0, sticky='w')
            ttk.Combobox(pf, textvariable=self.v_dir, values=[str(d) for d in DIR_CHOICES], width=6,
                         font=CODE_FONT).grid(row=4, column=1, sticky='w', padx=2)
            for col, (txt, d) in enumerate([('↑0', 0), ('→90', 90), ('↓180', 180), ('←270', 270)], start=2):
                ttk.Button(pf, text=txt, style='Small.TButton', takefocus=0,
                           command=lambda v=d: self.v_dir.set(str(v))).grid(row=4, column=col, padx=1)

            # ---- n / L / R อยู่คอลัมน์ขวา ไม่เพิ่มความสูงหน้าต่าง ----
            ttk.Separator(pf, orient='vertical').grid(row=0, column=6, rowspan=5, sticky='ns', padx=8)
            ttk.Label(pf, text='n').grid(row=0, column=7, sticky='w')
            ttk.Spinbox(pf, textvariable=self.v_n, from_=0, to=16000, increment=1, width=5,
                        font=CODE_FONT).grid(row=0, column=8, sticky='w', padx=2)
            for i, v in enumerate(N_PRESETS):
                r, c = 1 + i // 2, 7 + i % 2
                ttk.Button(pf, text=str(v), style='Small.TButton', takefocus=0,
                           command=lambda val=v: self.v_n.set(str(val))).grid(
                    row=r, column=c, padx=1, pady=0, sticky='ew')
            for row, (txt, var) in enumerate([('L', self.v_L), ('R', self.v_R)], start=3):
                ttk.Label(pf, text=txt).grid(row=row, column=7, sticky='w')
                ttk.Spinbox(pf, textvariable=var, from_=-100, to=100, increment=SPEED_STEP, width=5,
                            font=CODE_FONT).grid(row=row, column=8, sticky='w', padx=2)

            # ---- ตัวเลือก ----
            of = ttk.Frame(outer)
            of.pack(fill='x', pady=(2, 2))
            for text, var in [('End ก่อน', self.v_end), ('Enter หลัง', self.v_enter), ('ชื่อย่อ', self.v_alias),
                              ('ใส่ speed (opt.)', self.v_opt_speed),
                              ('Gyro ใส่ act', self.v_opt_act), ('Gyro ใส่ dir', self.v_opt_dir)]:
                ttk.Checkbutton(of, text=text, variable=var, takefocus=0).pack(side='left', padx=(0, 3))

            # ---- Action Pad (ปุ่มใหญ่ครบ 22 ตัว + None) ----
            self._build_action_pad(outer)

            # ---- พรีวิว + สถานะ ----
            # ขนาดคงที่ 100% (Zero Layout Shift): ใช้ tk.Label กำหนด height เป็นจำนวนบรรทัด + width=1
            # -> ความสูง/ความกว้างที่ขอจากหน้าต่างไม่ขึ้นกับข้อความเลย ข้อความยาวจะถูกตัดขวา/ตัดบรรทัดภายในกรอบ
            # (เดิมพรีวิวใช้ wraplength: ตอนชี้ปุ่ม 1 บรรทัด / ตอนออก 2 บรรทัด -> แท็บด้านล่างเด้งขึ้นลง
            #  หนีเมาส์ เกิด <Leave>/<Enter> วนไม่จบ ภาพซ้อน และคลิกไม่ติด)
            bg = style.lookup('TFrame', 'background') or root.cget('bg')
            self.lbl_preview = tk.Label(outer, textvariable=self.v_preview, font=CODE_FONT, fg='#6b46c1', bg=bg,
                                        anchor='w', justify='left', height=1, width=1, padx=0, pady=0)
            self.lbl_preview.pack(fill='x')
            # สถานะ 1 บรรทัดคงที่ (สูงเท่าเดิม) — ข้อความ ✓/เตือน ที่เด้งมาตอนเมาส์อยู่บนปุ่มจะไม่ดันแท็บลง
            self.lbl_status = tk.Label(outer, textvariable=self.v_status, font=('Segoe UI', 10), fg='#1f7a3a',
                                       bg=bg, anchor='w', justify='left', height=1, width=1, padx=0, pady=0)
            self.lbl_status.pack(fill='x', pady=(0, 4))

            # ---- แท็บปุ่มคำสั่ง (เป็นโพยคีย์ลัดไปในตัว) ----
            self.nb = ttk.Notebook(outer)
            self.nb.pack(fill='both', expand=True)
            self.cmd_buttons = []
            for tab_name, cats, cols in TABS:
                frame = ttk.Frame(self.nb, padding=4)
                self.nb.add(frame, text=tab_name)
                if cats is None:
                    self._build_param_tab(frame)
                else:
                    self._build_cmd_tab(frame, cats, cols)

            ttk.Label(outer, text=f'{pretty_hotkey(EXIT_HOTKEY)} = ปิดโปรแกรม   •   '
                                  'ท้ายปุ่ม = Ctrl+Alt+… (S+ = เติม Shift)   •   '
                                  'กดปุ่มบนจอ = พิมพ์ลง IDE ล่าสุด', foreground='#777').pack(fill='x', pady=(4, 0))
            self.compact_parts = [self.nb]

            self._lock_actdesc_size()
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            root.update_idletasks()
            if root.winfo_reqheight() > sh - 80:     # จอเตี้ย (1366x768 / สเกล 150%) -> เริ่มแบบย่อ
                self.v_compact.set(True)
                self._toggle_compact()
                root.update_idletasks()
            w = max(root.winfo_reqwidth(), 400)
            root.geometry(f'+{max(sw - w - 20, 0)}+10')

        def _build_cmd_tab(self, frame, cats, cols=4):
            row = 0
            for n, cat in enumerate(cats):
                if n:   # เส้นคั่นหมวด (ชื่อแท็บบอกหมวดอยู่แล้ว ประหยัดความสูงจอ)
                    ttk.Separator(frame).grid(row=row, column=0, columnspan=cols, sticky='ew', pady=3)
                    row += 1
                col = 0
                for c in [m for m in MACROS if m.cat == cat]:
                    b = ttk.Button(frame, style='Code.TButton', takefocus=0, width=-10,
                                   command=lambda cid=c.id: self.run_cmd(cid, from_button=True))
                    b.grid(row=row, column=col, padx=1, pady=1, sticky='ew')
                    # bind แบบ add='+' และไม่คืน 'break' -> ไม่แตะ class binding ของปุ่ม (คลิกทำงานปกติ 100%)
                    b.bind('<Enter>', lambda e, cid=c.id: self._schedule_preview(cid), add='+')
                    b.bind('<Leave>', lambda e: self._schedule_preview(None), add='+')
                    self.cmd_buttons.append((b, c))
                    col += 1
                    if col == cols:
                        col, row = 0, row + 1
                if col:
                    row += 1
            for i in range(cols):
                frame.columnconfigure(i, weight=1)
            self._refresh_button_labels()

        def _build_param_tab(self, frame):
            cols = 5
            ttk.Label(frame, text='คีย์ด้านล่างกดพร้อม Ctrl+Alt (S+ = เติม Shift)', foreground='#777').grid(
                row=0, column=0, columnspan=cols, sticky='w')
            for i, (aid, hk, label) in enumerate(PARAM_ACTIONS):
                r, c = divmod(i, cols)
                if hk.startswith('ctrl+alt+'):
                    key = pretty_hotkey(hk[len('ctrl+alt+'):], short=True).lstrip('+')
                else:
                    key = pretty_hotkey(hk, short=True)   # เช่น CS+Q = Ctrl+Shift+Q (ไม่ใช่ชุด Ctrl+Alt)
                ttk.Button(frame, text=f'{key}  {PARAM_SHORT.get(aid, label)}',
                           takefocus=0, style='Left.TButton',
                           command=lambda a=aid: self.run_param(a)).grid(row=r + 1, column=c, padx=1, pady=0, sticky='ew')
            for c in range(cols):
                frame.columnconfigure(c, weight=1)

        # ------------------------------------------------------ Action Pad
        def _build_action_pad(self, parent):
            box = ttk.LabelFrame(parent, text=' Action Character — คลิกเลือก (ตัวเล็ก/ใหญ่ คนละปุ่ม) ', padding=4)
            box.pack(fill='x', pady=(2, 2))
            grid = tk.Frame(box)
            grid.pack(fill='x')
            self.act_tiles = {}
            # กลุ่มเล็ก (n f) ไปอยู่ช่องว่างขวาของแถวที่มี 4 ปุ่ม (แถวแรกเว้นไว้ให้ None) ไม่เพิ่มความสูงหน้าต่าง
            free_rows = [r for r, g in enumerate(ACTION_GROUPS) if len(g[3]) == 4 and r > 0]
            r = 0
            for gname, light, strong, chars in ACTION_GROUPS:
                if len(chars) <= 2 and free_rows:
                    fr = free_rows.pop(0)
                    for c, ch in enumerate(chars):
                        self._make_tile(grid, ch).grid(row=fr, column=5 + c, padx=2, pady=1, sticky='nsew')
                    continue
                tk.Label(grid, text=gname, fg=strong, font=('Segoe UI', 8, 'bold'), anchor='w',
                         width=8).grid(row=r, column=0, sticky='w')
                for c, ch in enumerate(chars):
                    self._make_tile(grid, ch).grid(row=r, column=c + 1, padx=2, pady=1, sticky='nsew')
                r += 1
            # None อยู่แถวแรก (กลุ่มหยุด มี 4 ปุ่ม จึงเหลือที่ 2 ช่องขวา)
            self._make_tile(grid, ACT_NONE).grid(row=0, column=5, columnspan=2, padx=2, pady=1, sticky='nsew')
            for c in range(1, 7):
                grid.columnconfigure(c, weight=1, uniform='tile')

            # คำอธิบายเต็มของตัวที่เลือก (ff/bb เทียบ Gyro)
            # กล่องขนาดคงที่: วัดขนาดสูงสุดของคำอธิบายทุกตัวอักษร (รวม None) ที่ DPI ปัจจุบัน แล้วล็อกไว้
            # -> เปลี่ยน Action แล้วแท็บ/ปุ่มด้านล่างไม่ขยับ (เดิมเด้ง 40px เมื่อเลือก n / f)
            # (ขนาดจริงล็อกใน _lock_actdesc_size หลังวางทุกอย่างเสร็จ)
            self._act_grid = grid
            holder = self._actdesc_holder = tk.Frame(box, height=1)
            self.lbl_actdesc = tk.Label(holder, textvariable=self.v_actinfo, font=('Segoe UI', 9), anchor='nw',
                                        justify='left', wraplength=460, padx=6, pady=3)
            holder.pack_propagate(False)
            holder.pack(fill='x', pady=(4, 0))
            self.lbl_actdesc.pack(fill='both', expand=True)

        def _make_tile(self, parent, ch):
            light, strong = ACTION_COLOR[ch]
            tile = tk.Frame(parent, bg=light, highlightthickness=2, highlightbackground=strong,
                            highlightcolor=strong, cursor='hand2')
            big = tk.Label(tile, text=ch if ch else 'None', font=ACTION_FONT if ch else ('Segoe UI', 13, 'bold'),
                           bg=light, fg=strong)
            small = tk.Label(tile, text=ACTION_SHORT[ch], font=ACTION_SUB_FONT, bg=light, fg='#333333')
            big.pack(pady=0)
            small.pack(pady=(0, 1))
            for w in (tile, big, small):
                w.bind('<Button-1>', lambda e, v=ch: self.v_act.set(v))
            self.act_tiles[ch] = (tile, big, small, light, strong)
            return tile

        def _refresh_action_pad(self):
            cur = self.v_act.get()
            for ch, (tile, big, small, light, strong) in self.act_tiles.items():
                if ch == cur:   # ตัวที่เลือก: พื้นสีเข้ม ตัวหนังสือขาว ขอบดำ
                    tile.configure(bg=strong, highlightbackground='#111111', highlightcolor='#111111')
                    big.configure(bg=strong, fg='white')
                    small.configure(bg=strong, fg='white')
                else:
                    tile.configure(bg=light, highlightbackground=strong, highlightcolor=strong)
                    big.configure(bg=light, fg=strong)
                    small.configure(bg=light, fg='#333333')

        def _refresh_button_labels(self):
            short = self.v_alias.get()
            for b, c in self.cmd_buttons:
                label = c.alias if (short and c.alias) else (c.btn or c.label(short))
                if c.cat in SERVO_CATS and not c.raw and c.name != 'ServoWrite' and label.startswith('Servo'):
                    label = label[len('Servo'):]   # แท็บ Servo: ตัดคำว่า Servo ให้ปุ่มไม่ล้นจอ (พิมพ์จริงยังเป็นชื่อเต็ม)
                b.configure(text=f'{label} {key_on_button(c.hotkey)}' if c.hotkey else label)

        def _toggle_compact(self):
            for w in self.compact_parts:
                if self.v_compact.get():
                    w.pack_forget()
                else:
                    w.pack(fill='both', expand=True, after=self.lbl_status)

        @staticmethod
        def _actinfo_text(ch):
            if ch == ACT_NONE:
                return ('None — ไม่ใส่ select: ใช้กับคำสั่งที่ select เป็น optional เช่น FFcm / FFtimer / FFcmG / ffdircl\n'
                        'คำสั่งที่บังคับมี select (FFC, FFL, FFBG ...) จะไม่พิมพ์ และขึ้นเตือน · ชุด ffdirclg/ffdirg ใช้ \'p\' แทน')
            line, gyro = ACTION_INFO[ch]
            return (f"'{ch}'  ตามเส้น (FFC / BBC ...):  {line}\n"
                    f"'{ch}'  Gyro (FFcmG / FFBG ...):  {gyro}")

        def _update_actinfo(self):
            ch = self.v_act.get()
            light, strong = ACTION_COLOR.get(ch, ACTION_NONE_COLORS)
            text = self._actinfo_text(ch) if (ch == ACT_NONE or ch in ACTION_INFO) else ''
            if self.v_actinfo.get() != text:
                self.v_actinfo.set(text)
            self.lbl_actdesc.configure(bg=light, fg=strong)

        def _lock_actdesc_size(self):
            """ตัดบรรทัดตามความกว้างจริงของแผงปุ่ม Action แล้วล็อกความสูงกล่อง = คำอธิบายที่ยาวที่สุด (ทุกตัว + None)"""
            self.root.update_idletasks()
            box = self._act_grid.master
            outer = box.master
            # ความกว้างที่ได้แน่ทั้งโหมดเต็ม/โหมดย่อ = แผงที่กว้างสุดใน outer (ไม่นับแท็บ ซึ่งถูกซ่อนตอนย่อ)
            inner = max(w.winfo_reqwidth() for w in outer.pack_slaves() if w is not self.nb)
            insets = box.winfo_reqwidth() - self._act_grid.winfo_reqwidth()   # ขอบ + padding ของ LabelFrame
            wrap = max(inner - insets - 2 * int(self.lbl_actdesc.cget('padx')) - 4, 300)
            self.lbl_actdesc.configure(wraplength=wrap)
            max_h = 0
            for ch in [ACT_NONE] + ACTION_LIST:
                self.v_actinfo.set(self._actinfo_text(ch))
                self.lbl_actdesc.update_idletasks()
                max_h = max(max_h, self.lbl_actdesc.winfo_reqheight())
            self._actdesc_holder.configure(height=max_h)

        def _on_act_change(self):
            self._refresh_action_pad()
            self._update_actinfo()
            self._live_preview()

        def _live_preview(self):
            """บรรทัดตัวอย่างสด: FFC (เส้น) + ffdircl (ลำดับ select/dir) + คำสั่งล่าสุด"""
            p, errors = self.read_params()
            if errors:
                self._set_preview('⚠ ' + ', '.join(errors))
                return
            ids = ['cmd:ctrl+alt+1', 'cmd:ctrl+alt+;']    # FFC (เส้น) + ffdircl (ลำดับ select/dir)
            if self.last_cmd_id and self.last_cmd_id not in ids:
                ids.append(self.last_cmd_id)
            parts = []
            for cid in ids:
                try:
                    parts.append(render(self.cmds[cid], p, self.opts()))
                except ValueError:
                    parts.append(f'{self.cmds[cid].label(self.v_alias.get())}(✗ ค่าไม่ครบ/นอกช่วง)')
            self._set_preview('ตัวอย่าง →  ' + '   '.join(parts))

        def _set_preview(self, text):
            if self.v_preview.get() != text:   # ข้อความเดิมเป๊ะ -> ไม่สั่งวาดซ้ำ
                self.v_preview.set(text)

        def _schedule_preview(self, cid):
            """Hover debounce: ลากเมาส์ผ่านหลายปุ่มเร็ว ๆ จะอัปเดตครั้งเดียวตอนหยุด (cid=None = กลับเป็นตัวอย่างสด)"""
            if self._hover_job is not None:
                try:
                    self.root.after_cancel(self._hover_job)
                except Exception:
                    pass
            self._hover_job = self.root.after(HOVER_DEBOUNCE_MS, self._apply_hover, cid)

        def _apply_hover(self, cid):
            self._hover_job = None
            if cid is None:
                self._live_preview()
            else:
                self._show_preview(cid)

        # ------------------------------------------------------ ค่า/ตรวจสอบ
        def read_params(self):
            errors = []

            def num(var, name, cast=float, lo=None, hi=None):
                try:
                    v = cast(float(var.get().strip()))
                except ValueError:
                    errors.append(f'{name} ไม่ใช่ตัวเลข')
                    return 0
                if (lo is not None and v < lo) or (hi is not None and v > hi):
                    errors.append(f'{name} ต้องอยู่ช่วง {lo}..{hi}')
                return v

            p = {
                'speed': num(self.v_speed, 'speed', int, SPEED_MIN, SPEED_MAX),
                'cm': num(self.v_cm, 'cm', float, 0),
                'ms': num(self.v_ms, 'ms', int, 0),
                'dir': num(self.v_dir, 'dir', int, -360, 360),
                'angle': num(self.v_angle, 'angle', int, -360, 360),
            }
            act = self.v_act.get()
            if act != ACT_NONE and act not in ACTION_INFO:
                errors.append(f'action "{act}" ไม่อยู่ในตาราง')
            p['act'] = act or None          # None = ปุ่ม None (ไม่ใส่ตัวอักษร)
            p['n'] = num(self.v_n, 'n', int, 0)
            p['L'] = num(self.v_L, 'L', int, -100, 100)
            p['R'] = num(self.v_R, 'R', int, -100, 100)
            return p, errors

        def opts(self):
            return {'alias': self.v_alias.get(), 'opt_act': self.v_opt_act.get(), 'opt_dir': self.v_opt_dir.get(),
                    'opt_speed': self.v_opt_speed.get()}

        def _show_preview(self, cid):
            p, errors = self.read_params()
            if errors:
                self._set_preview('⚠ ' + ', '.join(errors))
                return
            try:
                self._set_preview('→ ' + render(self.cmds[cid], p, self.opts()))
            except ValueError as exc:
                self._set_preview('⚠ ' + str(exc))

        def set_status(self, msg, ok=True):
            self.v_status.set(msg)
            self.lbl_status.configure(foreground='#1f7a3a' if ok else '#c53030')
            if not ok:
                self.root.bell()

        # ------------------------------------------------------ คำสั่ง
        def run_cmd(self, cid, from_button=False):
            if self.paused.get() and not from_button:
                return
            p, errors = self.read_params()
            if errors:
                self.set_status('ไม่พิมพ์: ' + ', '.join(errors), ok=False)
                return
            try:
                text = render(self.cmds[cid], p, self.opts())
            except ValueError as exc:
                self.set_status('ไม่พิมพ์: ' + str(exc), ok=False)
                return
            self.last_cmd_id = cid
            self._live_preview()
            self.set_status(f'กำลังพิมพ์: {text}')
            self.typer.submit(text, {'end': self.v_end.get(), 'enter': self.v_enter.get(), 'method': TYPE_METHOD})

        def _adjust(self, var, delta, lo=None, hi=None):
            try:
                v = float(var.get())
            except ValueError:
                v = 0
            v += delta
            if lo is not None:
                v = max(lo, v)
            if hi is not None:
                v = min(hi, v)
            var.set(fmt_number(v))

        def run_param(self, aid):
            if aid == 'exit':
                self.quit()
                return
            if aid == 'pause':
                self.paused.set(not self.paused.get())
                on = not self.paused.get()
                self.lbl_mode.configure(text=' ON ' if on else ' PAUSE ', bg='#1f9d55' if on else '#c05621')
                self.set_status('มาโครทำงาน' if on else 'หยุดชั่วคราว (กด Ctrl+Alt+Shift+P เพื่อเปิด)', ok=on)
                return
            if aid == 'window':
                if self.root.state() == 'withdrawn':
                    self.root.deiconify()
                    self.root.attributes('-topmost', self.v_top.get())
                else:
                    self.root.withdraw()
                return
            if self.paused.get():
                return
            if aid == 'repeat':
                if self.last_cmd_id:
                    self.run_cmd(self.last_cmd_id)
                else:
                    self.set_status('ยังไม่มีคำสั่งล่าสุด', ok=False)
                return
            acts = {
                'speed+': lambda: self._adjust(self.v_speed, SPEED_STEP, SPEED_MIN, SPEED_MAX),
                'speed-': lambda: self._adjust(self.v_speed, -SPEED_STEP, SPEED_MIN, SPEED_MAX),
                'speed_slow': lambda: self.v_speed.set(str(SLOW_SPEED)),
                'speed_def': lambda: self.v_speed.set(str(DEFAULT_SPEED)),
                'speed_fast': lambda: self.v_speed.set(str(FAST_SPEED)),
                'cm+': lambda: self._adjust(self.v_cm, CM_STEP, 0),
                'cm-': lambda: self._adjust(self.v_cm, -CM_STEP, 0),
                'ms+': lambda: self._adjust(self.v_ms, MS_STEP, 0),
                'ms-': lambda: self._adjust(self.v_ms, -MS_STEP, 0),
                'dir0': lambda: self.v_dir.set('0'),
                'dir90': lambda: self.v_dir.set('90'),
                'dir180': lambda: self.v_dir.set('180'),
                'dir270': lambda: self.v_dir.set('270'),
                'act_p': lambda: self.v_act.set('p'),
                'act_c': lambda: self.v_act.set('c'),
                'act_s': lambda: self.v_act.set('s'),
                'act_l': lambda: self.v_act.set('l'),
                'act_r': lambda: self.v_act.set('r'),
                'act_next': lambda: self._cycle_act(1),
                'act_prev': lambda: self._cycle_act(-1),
                'act_case': lambda: self.v_act.set(self.v_act.get().swapcase()),
            }
            acts[aid]()
            self.set_status(f'speed={self.v_speed.get()}  cm={self.v_cm.get()}  ms={self.v_ms.get()}  '
                            f"dir={self.v_dir.get()}  angle={self.v_angle.get()}  "
                            f"act={repr(self.v_act.get()) if self.v_act.get() else 'None'}  "
                            f"n={self.v_n.get()}  L={self.v_L.get()}  R={self.v_R.get()}")

        def _cycle_act(self, step):
            cur = self.v_act.get()
            upper = cur.isupper()
            low = cur.lower()
            i = ACTION_CYCLE.index(low) if low in ACTION_CYCLE else -1
            nxt = ACTION_CYCLE[(i + step) % len(ACTION_CYCLE)]
            self.v_act.set(nxt.upper() if upper else nxt)

        # ------------------------------------------------------ วนลูป
        def _poll_queue(self):
            try:
                while True:
                    item = self.ui_queue.get_nowait()
                    if item[0] == 'hotkey':
                        action = item[1]
                        if action.startswith('cmd:'):
                            self.run_cmd(action)
                        else:
                            self.run_param(action)
                    elif item[0] == 'status':
                        self.set_status(item[1], item[2])
            except queue.Empty:
                pass
            if self.root.winfo_exists():
                self.root.after(30, self._poll_queue)

        def _poll_foreground(self):
            try:
                hwnd = user32.GetForegroundWindow()
                if is_valid_target(hwnd) and hwnd != self.typer.last_target:
                    self.typer.last_target = hwnd
                    title = window_title(hwnd) or window_class(hwnd)
                    self.v_target.set('เป้าหมาย: ' + (title[:38] + '…' if len(title) > 38 else title))
            except Exception:
                pass
            self.root.after(200, self._poll_foreground)

        def _start_hotkeys(self):
            bindings = [(c.hotkey, c.id) for c in MACROS if c.hotkey] + [(hk, aid) for aid, hk, _ in PARAM_ACTIONS]
            self.hotkeys = HotkeyThread(bindings, self.ui_queue)
            self.hotkeys.start()
            self.hotkeys.ready.wait(3)
            if self.hotkeys.failed:
                msg = 'คีย์ลัดที่ใช้ไม่ได้ (โปรแกรมอื่นจองไว้): ' + ', '.join(pretty_hotkey(h) for h in self.hotkeys.failed)
                print('[!] ' + msg)
                self.set_status(msg, ok=False)
            print(f'--- เริ่มทำงาน: คีย์ลัด {len(bindings) - len(self.hotkeys.failed)}/{len(bindings)} ใช้งานได้ ---')
            print(f'    {pretty_hotkey(EXIT_HOTKEY)} = ปิดโปรแกรม')

        def quit(self):
            if self.hotkeys:
                self.hotkeys.stop()
            self.typer.stop()
            try:
                self.root.destroy()
            except Exception:
                pass
            print('--- ปิดโปรแกรมแล้ว ---')

        def mainloop(self):
            self.root.mainloop()

    return App()


# ============================================================================
# 10) โหมดตรวจสอบ / ตาราง
# ============================================================================
SAMPLE_PARAMS = {'speed': DEFAULT_SPEED, 'cm': DEFAULT_CM, 'ms': DEFAULT_MS, 'dir': 90, 'angle': DEFAULT_ANGLE,
                 'act': DEFAULT_ACTION, 'n': DEFAULT_N, 'L': DEFAULT_L, 'R': DEFAULT_R}
DEFAULT_OPTS = {'alias': False, 'opt_act': True, 'opt_dir': False, 'opt_speed': True}
SAMPLE_N = {'FFSUM': 4000, 'BBSUM': 4000, 'BalanceF': 1, 'BalanceB': 1, 'BalanceFC': 1, 'BalanceBC': 1,
            'ServoWrite': 1}   # ค่า n ตัวอย่างที่เหมาะกับแต่ละคำสั่ง (ตาราง / EXPECTED)


def sample_for(cmd):
    return dict(SAMPLE_PARAMS, n=SAMPLE_N.get(cmd.name, SAMPLE_PARAMS['n']))

# ผลลัพธ์ที่ถูกต้องของทุกคำสั่ง (เรียงตาม MACROS) ที่ค่าตัวอย่าง speed=50 cm=30 ms=1000 dir=90 angle=90
# act='p' n=7 (FFSUM 4000, Balance 1, ServoWrite 1) L=60 R=20 — แต่ละบรรทัดเทียบกับ signature ในไฟล์ .h ของ UnknowRobot_STORMXII_V3_BNO085 แล้ว
EXPECTED = """
FFC(50, 'p');
FFC2(50, 'p');
FFL(50, 'p');
FFR(50, 'p');
BBC(50, 'p');
BBC2(50, 'p');
BBL(50, 'p');
BBR(50, 'p');
FFL0(50, 'p');
FFR15(50, 'p');
BBL0(50, 'p');
BBR15(50, 'p');
FFNUM(50, 'p', 7);
BBNUM(50, 'p', 7);
FFSUM(50, 'p', 4000);
BBSUM(50, 'p', 4000);
FFcm(50, 30, 'p');
BBcm(50, 30, 'p');
FFtimer(50, 1000, 'p');
BBtimer(50, 1000, 'p');
FFWhite(50, 'p');
BBWhite(50, 'p');
FFBlack(50, 'p');
BBBlack(50, 'p');
SpinL(50);
SpinR(50);
SpinL2(50);
SpinR2(50);
SpinLB(50);
SpinRB(50);
SpinL2B(50);
SpinR2B(50);
TurnLeft();
TurnRight();
TurnLeftB();
TurnRightB();
ToCenter();
ToCenterL();
ToCenterR();
BackCenter();
LF(1000);
LB(1000);
BalanceF(1);
BalanceB(1);
BalanceFC(1);
BalanceBC(1);
FFcmCirCleL(50, 30, 'p');
FFcmCirCleR(50, 30, 'p');
BBcmCirCleL(50, 30, 'p');
BBcmCirCleR(50, 30, 'p');
FFCirCleL(50, 'p');
FFCirCleR(50, 'p');
BBCirCleL(50, 'p');
BBCirCleR(50, 'p');
FFtimerCirCleL(50, 1000, 'p');
FFtimerCirCleR(50, 1000, 'p');
BBtimerCirCleL(50, 1000, 'p');
BBtimerCirCleR(50, 1000, 'p');
ffdircl(50, 'p', 90);
ffdircr(50, 'p', 90);
bbdircl(50, 'p', 90);
bbdircr(50, 'p', 90);
FFdir(50, 90, 'p');
BBdir(50, 90, 'p');
FFdirCirCleL(50, 90, 'p');
FFdirCirCleR(50, 90, 'p');
BBdirCirCleL(50, 90, 'p');
BBdirCirCleR(50, 90, 'p');
ffdirf(50, 90, 'p');
bbdirb(50, 90, 'p');
ffdirclg(50, 'p', 90);
ffdircrg(50, 'p', 90);
bbdirclg(50, 'p', 90);
bbdircrg(50, 'p', 90);
ffdirg(50, 'p', 90);
bbdirg(50, 'p', 90);
ffdeg(50, 'p', 90);
bbdeg(50, 'p', 90);
ffdegg(50, 'p', 90);
bbdegg(50, 'p', 90);
ffdegcl(50, 'p', 90);
ffdegcr(50, 'p', 90);
bbdegcl(50, 'p', 90);
bbdegcr(50, 'p', 90);
ffdegclg(50, 'p', 90);
ffdegcrg(50, 'p', 90);
bbdegclg(50, 'p', 90);
bbdegcrg(50, 'p', 90);
resetAngles();
SetRobotAngle();
FFcmG(50, 30, 'p');
BBcmG(50, 30, 'p');
FFcmGS(50, 30, 'p');
BBcmGS(50, 30, 'p');
FFtimerG(50, 1000, 'p');
BBtimerG(50, 1000, 'p');
FFBG(50, 'p');
BBBG(50, 'p');
ToCenterG();
spinDirection(50, 90);
turnDirection(50, 90);
turnDirectionB(50, 90);
SpinLG(50, 90);
SpinRG(50, 90);
TurnLG(50, 90);
TurnRG(50, 90);
TurnLBG(50, 90);
TurnRBG(50, 90);
spinDegree(50, 90);
turnDegree(50, 90);
turnDegreeB(50, 90);
turnDegree_none(50, 90);
turnDegreeb_none(50, 90);
turnDirection_none(50, 90);
turnDirectionb_none(50, 90);
TurnLRG(50, 90);
TurnRLG(50, 90);
TurnLRBG(50, 90);
TurnRLBG(50, 90);
rotateDegree(60, 20, 90);
rotateDegree_none(60, 20, 90);
rotateDir(60, 20, 'p', 90);
rotateDir_none(60, 20, 90);
spin_ffcmg(50, 30, 'p', 90);
spin_bbcmg(50, 30, 'p', 90);
turn_ffcmg(50, 30, 'p', 90);
turn_bbcmg(50, 30, 'p', 90);
turnb_ffcmg(50, 30, 'p', 90);
turnb_bbcmg(50, 30, 'p', 90);
resetAnglesDir(90);
setAngleOffset();
setHeading(90);
SetDirectionG(90);
SetG(1000);
SetGB(1000);
SetFG(1000);
SetBG(1000);
ServoOpen(); ServoUp();
ServoUp();
ServoUp45();
ServoDown();
ServoOpen();
ServoClose();
ServoLOpen();
ServoROpen();
ServoOpenMax();
ServoCloseSmall();
ServoGrip();
ServoOpen2();
ServoOpen(); ServoDown();
ServoDown(); ServoOpen();
ServoOpen(); ServoUp();
ServoUp(); ServoOpen();
ServoDown(); ServoClose();
ServoClose(); ServoDown();
ServoUp(); ServoClose();
ServoClose(); ServoUp();
ServoOpenMax2();
ServoLClose();
ServoRClose();
ServoLCloseSmall();
ServoRCloseSmall();
ServoLOpenMax();
ServoROpenMax();
ServoLOpenMax2();
ServoROpenMax2();
ServoWrite(1, 90);
MotorStop();
MotorStop(1000);
Move(60, 20, 1000);
Motor(60, 20);
GoStart(50);
GoEnd(50);
TestMotor();
#include <UnknowRobot_STORMXII_V3_BNO085.h>
RobotSetup();
LoadCalibrateFromEEPROM();
CalibrateSensor();
swOK();
swSTART();
SerialCalibrate_AllSensor();
SerialPositionFB();
TrackLineColor(BLACK);
RefLineValue(500);
RefCenterLineValue(500);
SetRobotPID(0.009, 0.12);
SetSensorTrackLine_CH(16);
set_sensor_track_line(0, 15);
set_line_center(1);
ModeSpdPID(1, 100, -100);
ModeSpdGyro(4, 100, -5);
SetTurnSpeed(50);
SetToCenterSpeed(30);
SetGyroRun(0.25, 2.5);
SetGyroSpin(1.3, 0.8, 65, 20, 15.0, 1.0);
SetGyroTurn(1.3, 0.8, 65, 20, 15.0, 1.0);
set_auto_align(20);
set_track_snap90(true);
FFC(80, 'p');
FFC(30, 'c');
delay(1000);
""".strip().split('\n')


def library_names(lib_dir=LIB_DIR):
    """อ่านชื่อฟังก์ชันจริงจากไลบรารี -> (ชื่อใน .h/.cpp, ชื่อที่นิยามใน examples/*.ino) หรือ None ถ้าไม่เจอโฟลเดอร์"""
    import re
    if not os.path.isdir(lib_dir):
        return None
    pat = re.compile(r'^[ \t]*(?:static[ \t]+|inline[ \t]+)*(?:void|int|bool|float|double|char|long|'
                     r'u?int\d+_t|unsigned[ \t]+\w+)[ \t]+(\w+)[ \t]*\(', re.M)
    lib, ex = set(), set()
    for root, _, files in os.walk(lib_dir):
        if '.git' in root:
            continue
        for f in files:
            if not f.endswith(('.h', '.cpp', '.ino')):
                continue
            text = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
            if f.endswith('.ino'):
                # ไฟล์คู่มือเป็นคอมเมนต์ล้วน — นับเฉพาะฟังก์ชันที่นิยามจริง (ไม่ใช่บรรทัดคอมเมนต์)
                ex.update(pat.findall(text))
            else:
                lib.update(pat.findall(text))
                for a, b in re.findall(r'^LINE_CURVE_SET\((\w+),\s*(\w+)', text, re.M):
                    lib.update((a, b))
    return lib, ex - lib


def called_names(code):
    import re
    if code.lstrip().startswith('#'):
        return []
    return [n for n in re.findall(r'\b([A-Za-z_]\w*)\s*\(', code) if n not in ('if', 'while', 'for', 'switch')]


def render_variants():
    """ทุกคำสั่ง x ตัวเลือก/ค่าหลายแบบ (ใช้ทำ --sketch และตรวจชื่อ) -> list ของบรรทัดโค้ดไม่ซ้ำ"""
    seen, out = set(), []
    params = [SAMPLE_PARAMS,
              dict(SAMPLE_PARAMS, cm=12.5, dir=270, angle=-90, act='L'),
              dict(SAMPLE_PARAMS, dir=0, angle=45, act='f', n=4000),
              dict(SAMPLE_PARAMS, n=1, act='g'),
              dict(SAMPLE_PARAMS, act=None, dir=180)]
    for p in params:
        for alias in (False, True):
            for opt_act in (True, False):
                for opt_dir in (False, True):
                    for opt_speed in (True, False):
                        o = {'alias': alias, 'opt_act': opt_act, 'opt_dir': opt_dir, 'opt_speed': opt_speed}
                        for c in MACROS:
                            try:
                                line = render(c, p, o)
                            except ValueError:
                                continue
                            if line not in seen:
                                seen.add(line)
                                out.append(line)
    return out


def test_sketch():
    """Mission.ino สำหรับทดสอบคอมไพล์: ใส่โค้ดที่ทุกคำสั่งพิมพ์ได้ลงใน Mission()
    วิธีใช้: คัดลอกโฟลเดอร์ examples/UnknowRobotStormXII_Code_V3_16CH_BNO085 ไปที่อื่น
    แล้วเขียนทับ Mission.ino ด้วยผลลัพธ์นี้ แล้วกด Verify ใน Arduino IDE"""
    body = [l for l in render_variants() if not l.lstrip().startswith('#')]
    return ('// สร้างโดย macro.py --sketch : ทดสอบคอมไพล์เท่านั้น ห้ามอัปโหลดไปวิ่งจริง\n'
            'void Mission() {\n' + ''.join(f'  {l}\n' for l in body) + '}\n')


def markdown_table():
    lines = []
    cats = []
    for c in MACROS:
        if c.cat not in cats:
            cats.append(c.cat)
    for cat in cats:
        lines += [f'#### {cat}', '', '| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |', '|---|---|---|']
        for c in [m for m in MACROS if m.cat == cat]:
            code = f"`{render(c, sample_for(c), DEFAULT_OPTS)}`"
            if c.alias:
                code += f" / `{render(c, sample_for(c), dict(DEFAULT_OPTS, alias=True))}`"
            key = f'`{pretty_hotkey(c.hotkey)}`' if c.hotkey else 'ปุ่มบนจอ'
            lines.append(f'| {key} | {code} | {c.desc} |')
        lines.append('')
    lines += ['#### ปรับค่า / ระบบ (ไม่พิมพ์ลง IDE)', '', '| คีย์ลัด | หน้าที่ |', '|---|---|']
    for _, hk, label in PARAM_ACTIONS:
        lines.append(f'| `{pretty_hotkey(hk)}` | {label} |')
    return '\n'.join(lines)


def selftest():
    ok = True

    def fail(msg):
        nonlocal ok
        print('[FAIL] ' + msg)
        ok = False

    # ---- คีย์ลัดไม่ซ้ำ ----
    seen = {}
    all_hotkeys = [(c.hotkey, c.id) for c in MACROS if c.hotkey] + [(hk, aid) for aid, hk, _ in PARAM_ACTIONS]
    for hk, ident in all_hotkeys:
        key = parse_hotkey(hk)
        if key in seen:
            fail(f'คีย์ลัดซ้ำ {hk}: {seen[key]} กับ {ident}')
        seen[key] = ident
    if len({c.id for c in MACROS}) != len(MACROS):
        fail('Cmd.id ซ้ำ')

    # ---- ทุกคำสั่งตรงกับผลลัพธ์ที่เทียบกับไฟล์ .h แล้ว ----
    got = [render(c, sample_for(c), DEFAULT_OPTS) for c in MACROS]
    if len(got) != len(EXPECTED):
        fail(f'จำนวนคำสั่ง {len(got)} ไม่เท่ากับ EXPECTED {len(EXPECTED)}')
    for c, g, e in zip(MACROS, got, EXPECTED):
        if g != e:
            fail(f'{c.name}: ได้ {g!r} ควรเป็น {e!r}')

    # ---- ตัวเลือก / None / alias / ปัดเศษ ----
    def r(name, idx=0, **kw):
        o = dict(DEFAULT_OPTS)
        for k in ('alias', 'opt_act', 'opt_dir', 'opt_speed'):
            if k in kw:
                o[k] = kw.pop(k)
        cmd = [m for m in MACROS if m.name == name][idx]
        return render(cmd, dict(sample_for(cmd), **kw), o)

    variant_checks = [
        (r('FFcmG', opt_act=False), 'FFcmG(50, 30);'),
        (r('FFcmG', act=None), 'FFcmG(50, 30);'),
        (r('FFcmG', opt_dir=True), "FFcmG(50, 30, 'p', 90);"),
        (r('FFcmG', act=None, opt_dir=True), 'FFcmG(50, 30, 90);'),          # (int, float, int direction)
        (r('BBtimerG', opt_act=False, opt_dir=True, dir=0), 'BBtimerG(50, 1000, 0);'),
        (r('FFBG', opt_dir=True, dir=270), "FFBG(50, 'p', 270);"),
        (r('FFcm', act=None, cm=12.5), 'FFcm(50, 12.5);'),
        (r('FFtimer', act=None), 'FFtimer(50, 1000);'),
        (r('FFcmCirCleL', cm=12.5), "FFcmCirCleL(50, 13, 'p');"),            # int เท่านั้น -> ปัดเศษ
        (r('FFcmCirCleL', act=None, cm=12.4), 'FFcmCirCleL(50, 12);'),
        (r('ffdircl', act=None), 'ffdircl(50, 90);'),
        (r('ffdircr', act='f', dir=180), "ffdircr(50, 'f', 180);"),
        (r('FFdir', act=None, dir=270), 'FFdir(50, 270);'),
        (r('ffdirclg', act=None), "ffdirclg(50, 'p', 90);"),                  # act! -> 'p'
        (r('ffdirf', act=None), "ffdirf(50, 90, 'p');"),
        (r('ffdeg', act=None, angle=-90), 'ffdeg(50, -90);'),
        (r('rotateDir', act=None), 'rotateDir(60, 20, 90);'),
        (r('rotateDir', act='n'), "rotateDir(60, 20, 'n', 90);"),
        (r('spin_ffcmg', act=None), 'spin_ffcmg(50, 30, 90);'),
        (r('SpinL', opt_speed=False), 'SpinL();'),
        (r('SpinLG', opt_speed=False), 'SpinLG(90);'),
        (r('spinDegree', opt_speed=False, angle=-90), 'spinDegree(-90);'),
        (r('spinDirection', opt_speed=False, dir=270), 'spinDirection(270);'),
        (r('spinDirection', alias=True), 'sdg(50, 90);'),
        (r('turnDirection', alias=True, opt_speed=False), 'tdg(90);'),
        (r('turnDirectionB', alias=True), 'tdbg(50, 90);'),
        (r('turnDirection_none', alias=True), 'turndir_none(50, 90);'),
        (r('turnDirectionb_none', alias=True), 'turndirb_none(50, 90);'),
        (r('MotorStop', 1), 'MotorStop(1000);'),
        (r('Move', L=-40, R=40, ms=300), 'Move(-40, 40, 300);'),
        (r('delay(ms)', ms=250), 'delay(250);'),
    ]
    for g, e in variant_checks:
        if g != e:
            fail(f'ได้ {g!r} ควรเป็น {e!r}')

    # ---- คำสั่งที่บังคับ select + None -> ต้องไม่พิมพ์ ----
    for name in ('FFC', 'FFNUM', 'FFWhite', 'FFCirCleL', 'FFBG', 'BBBG'):
        try:
            r(name, act=None)
            fail(f'{name} + None ควร raise ValueError')
        except ValueError:
            pass

    # ---- ค่า n / angle นอกช่วง -> ต้องไม่พิมพ์ ----
    for name, kw in [('FFNUM', {'n': 16}), ('FFNUM', {'n': 4000}), ('BBNUM', {'n': -1}), ('ServoWrite', {'n': 7}),
                     ('FFSUM', {'n': 0}), ('BalanceF', {'n': 0}), ('SpinLG', {'angle': -90}),
                     ('TurnRBG', {'angle': -45}), ('rotateDegree', {'angle': -90})]:
        try:
            r(name, **kw)
            fail(f'{name} {kw} ควร raise ValueError')
        except ValueError:
            pass
    if r('FFNUM', n=15) != "FFNUM(50, 'p', 15);" or r('ServoWrite', n=36) != 'ServoWrite(36, 90);'             or r('spinDegree', angle=-90) != 'spinDegree(50, -90);':
        fail('ค่าในช่วงที่ถูกต้องต้องพิมพ์ได้')

    # ---- Action Pad ----
    if sorted(c for _, _, _, chars in ACTION_GROUPS for c in chars) != sorted(ACTION_LIST) or len(ACTION_LIST) != 24:
        fail('Action Pad ไม่ครบ 24 ตัว')
    if set(ACTION_SHORT) != set(ACTION_LIST) | {ACT_NONE}:
        fail('ACTION_SHORT ไม่ครบ')
    if not set(ACTION_CYCLE) <= set(ACTION_LIST):
        fail('ACTION_CYCLE มีตัวที่ไม่อยู่ในตาราง')
    if fmt_number(12.5) != '12.5' or fmt_number(20.0) != '20':
        fail('fmt_number')

    # ---- ทุกชื่อฟังก์ชันที่พิมพ์ได้ต้องมีอยู่จริงในไลบรารี (ห้ามแต่งชื่อเอง) ----
    names = library_names()
    lines = render_variants()
    if names is None:
        print(f'[i] ไม่พบไลบรารีที่ {LIB_DIR} — ข้ามการตรวจชื่อฟังก์ชัน')
    else:
        lib, ex = names
        from_examples = set()
        for line in lines:
            for n in called_names(line):
                if n in lib or n in ARDUINO_BUILTINS:
                    continue
                if n in ex:
                    from_examples.add(n)
                else:
                    fail(f'"{n}" ไม่มีในไลบรารี UnknowRobot_STORMXII_V3_BNO085 ({line})')
        print(f'ตรวจชื่อกับไลบรารี: {len(lines)} บรรทัด, พบฟังก์ชันในไลบรารี {len(lib)} ชื่อ')
        if from_examples:
            print('[i] ชื่อที่นิยามใน examples/*.ino (ต้องมีไฟล์นั้นในสเก็ตช์):', ', '.join(sorted(from_examples)))

    print(f'คำสั่ง {len(MACROS)} รายการ (มีคีย์ลัด {sum(1 for c in MACROS if c.hotkey)}), '
          f'คีย์ลัดทั้งหมด {len(all_hotkeys)} ชุด')
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


# ============================================================================
# main
# ============================================================================
def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    if '--selftest' in sys.argv:
        sys.exit(0 if selftest() else 1)
    if '--table' in sys.argv:
        print(markdown_table())
        return
    if '--sketch' in sys.argv:
        print(test_sketch(), end='')
        return
    if not IS_WINDOWS:
        print('โปรแกรมนี้รองรับเฉพาะ Windows')
        sys.exit(1)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # ตัวหนังสือคมบนจอ 125-150%
    except Exception:
        pass

    if '--gui-test' in sys.argv:
        app = build_app(start_hotkeys=False)
        app.root.update()
        print('GUI OK:', app.root.winfo_width(), 'x', app.root.winfo_height())
        app.quit()
        return

    if pyperclip is None:
        print('[i] ไม่พบ pyperclip — ใช้ Clipboard ของ Windows โดยตรงแทน (ทำงานได้เหมือนกัน)')
    app = build_app()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.quit()


if __name__ == '__main__':
    main()
