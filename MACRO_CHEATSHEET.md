# MACRO CHEATSHEET — STORM-XII V3 (16CH + BNO085)

โพยคีย์ลัดของ `macro.py` ที่พิมพ์โค้ดจากไลบรารี **UnknowRobot_STORMXII_V3_BNO085** ลง Arduino IDE
ทุกชื่อฟังก์ชันและลำดับพารามิเตอร์ตรวจกับไฟล์ `.h` ของไลบรารีแล้ว (`python macro.py --selftest`) และคอมไพล์ผ่านจริงบนบอร์ด RP2350B

## วิธีอ่านโพย

- คีย์ลัดทุกตัวกด **Ctrl+Alt** ยกเว้นปิดโปรแกรม (`Ctrl+Shift+Q`) · บนปุ่มในหน้าต่างจะเขียนย่อ เช่น `T` = Ctrl+Alt+T, `S+T` = Ctrl+Alt+Shift+T
- "ปุ่มบนจอ" = ไม่มีคีย์ลัด ให้คลิกปุ่มในแท็บของหน้าต่างโพย
- ค่าในวงเล็บดึงจากช่องในหน้าต่างโพยตอนกด ตัวอย่างในตารางใช้ `speed=50 cm=30 ms=1000 dir=90 angle=90 select='p' n=7 L=60 R=20` (n ของ FFSUM = 4000, Balance/ServoWrite = 1)

## ความหมายพารามิเตอร์

| ช่อง | ความหมาย | ใช้กับ |
|---|---|---|
| `speed` | ความเร็ว 0-100 | แทบทุกคำสั่ง · ติ๊ก **ใส่ speed (opt.)** ออก = ไม่ใส่ speed ใช้ค่าจาก `SetTurnSpeed` / `SetGyroSpin` / `SetGyroTurn` (เช่น `SpinL();` `SpinLG(90);`) |
| `cm` | ระยะทาง (เซนติเมตร โดยประมาณ) | `FFcm` `FFcmG` `FFcmGS` `spin_ffcmg` … · ชุด `FFcmCirCle*` รับเลขจำนวนเต็ม โปรแกรมปัดเศษให้ |
| `ms` | เวลา (มิลลิวินาที) | `FFtimer` `FFtimerG` `LF` `SetG` `Move` `delay` |
| `dir` | ทิศสัมบูรณ์ 0 / 90 / 180 / 270 นับจาก `resetAngles()` ครั้งล่าสุด | `spinDirection` `ffdircl` `FFdir` `FFcmG(...dir)` `resetAnglesDir` |
| `angle` | องศาสัมพัทธ์ · `SpinLG/SpinRG/TurnLG...` ใส่บวก (ทิศอยู่ในชื่อแล้ว) · `spinDegree/turnDegree/ffdeg` บวก = ขวา ลบ = ซ้าย | ชุดหมุน/เลี้ยว Gyro, `ffdeg*`, `rotateDegree` |
| select | ตัวอักษรเมื่อเจอแยก (Action Pad) · **None** = ไม่ใส่ | ดูตารางด้านล่าง |
| `n` | `FFNUM` = ตำแหน่งเซนเซอร์ 0-15 · `FFSUM` = ผลรวมเซนเซอร์หน้า (เช่น 4000 ≈ ดำ 4 ตัว) · `Balance*` = จำนวนครั้ง · `ServoWrite` = เลขเซอร์โว 0 ยก / 1 ซ้าย / 2 ขวา | |
| `L` `R` | ความเร็วล้อซ้าย / ขวา (-100..100) | `Move` `Motor` `rotateDegree` `rotateDir` |

ตัวเลือก **Gyro ใส่ act / Gyro ใส่ dir** ใช้กับ `FFcmG BBcmG FFcmGS BBcmGS FFtimerG BBtimerG` (และ dir กับ `FFBG BBBG`)
ใส่หรือไม่ใส่แต่ละตัวได้อิสระ เพราะไลบรารีแยก overload ด้วยชนิด เช่น `FFcmG(50, 30);` `FFcmG(50, 30, 'p');` `FFcmG(50, 30, 90);` `FFcmG(50, 30, 'p', 90);`

## ตัวอักษร select (อ่านจาก TrackSelectF/B ใน Unknow_PID.h และ TrackSelectG/GB ใน Unknow_IMU.h)

| ตัว | ตามเส้น `FFC FFL FFcm FFtimer …` (ff / bb) | Gyro `FFcmG FFBG FFtimerG …` (ff / bb) |
|---|---|---|
| `s` | เบรกหยุด | เบรกหยุด |
| `S` | ToFront (bb: ToBack) แล้วเบรก | ToFront แล้วเบรก (bb: ถอยให้หลังเจอเส้นก่อน) |
| `p` | วิ่งผ่านแยกต่อ | วิ่งผ่านแยกต่อ |
| `P` | ToFront แล้วผ่าน (bb = `p`) | ToFront แล้วผ่าน (bb = `p`) |
| `c` | เข้ากลางหุ่นแล้วหยุด | เข้ากลางหุ่นแล้วหยุด |
| `C` | ToFront/ToBack + เข้ากลาง | ff: เข้ากลาง · bb: ToFront + ถอยเข้ากลาง |
| `l` / `r` | เข้ากลาง + `SpinL()` / `SpinR()` | เข้ากลาง + หมุน -90° / +90° |
| `L` / `R` | ToFront/ToBack + เข้ากลาง + Spin | หมุน -90° / +90° ทันที |
| `q` / `e` | เลี้ยวล้อเดียว `TurnLeft()` / `TurnRight()` (bb: `TurnRightB` / `TurnLeftB`) | ToFront + เลี้ยว -90° / +90° (bb: เลี้ยวถอย +90° / -90°) |
| `Q` / `E` | ToFront/ToBack ก่อน แล้วเหมือนตัวเล็ก | เลี้ยวทันที |
| `a` / `d` | เข้ากลาง + `SpinLB()` / `SpinRB()` (เซนเซอร์หลัง) | ไม่มี → หยุด |
| `A` / `D` | ToFront/ToBack + เหมือนตัวเล็ก | ไม่มี → หยุด |
| `b` / `B` | ไม่มี → หยุด | วิ่งต่อจนเซนเซอร์หลังเจอเส้น |
| `g` / `G` | ค้างมุม `SetFG` / `SetBG` นาน = speed ms (`G` = ToFront ก่อน) | ค้างมุม `SetG` นาน = speed ms |
| `n` | เฉพาะชุด `ffdircl…` `ffdeg…` `rotateDir`: ไหลต่อ ไม่เบรก (คำสั่งอื่น = หยุด) | เหมือนกัน |
| `f` | เฉพาะชุด `ffdircl…` `ffdeg…` `rotateDir`: เบรกไจโร + ล็อกมุม (คำสั่งอื่น = หยุด) | เหมือนกัน |

- คำสั่งที่ **บังคับ** มี select (`FFC FFL FFR FFWhite FFCirCleL FFBG …`): ถ้าเลือก None โปรแกรมจะไม่พิมพ์และขึ้นเตือนสีแดง
- ค่า `n` นอกช่วงจะไม่พิมพ์ (ไลบรารีไม่เช็กให้ เช่น `FFNUM` อ่าน `F[n]` ตรง ๆ): `FFNUM/BBNUM` 0-15 · `FFSUM/BBSUM` 1-16000 · `Balance*` 1-20 · `ServoWrite` 0/1/2 หรือ 34-39
- `SpinLG SpinRG TurnLG TurnRG TurnLBG TurnRBG TurnLRG… rotateDegree` ต้องใช้ angle เป็นบวก (ทิศอยู่ในชื่อแล้ว) ถ้าติดลบจะไม่พิมพ์ — อยากใส่ +/- ให้ใช้ `spinDegree` / `turnDegree`
- ชุด `ffdirclg ffdircrg bbdirclg bbdircrg ffdirg bbdirg ffdirf bbdirb ffdegg ffdeg*g`: ถ้าเลือก None จะใส่ `'p'` ให้เอง

## เทียบชุดเดิม → ชุด STORM-XII V3 BNO085 (คีย์ลัดเดิมยังกดตำแหน่งเดิม)

| คีย์ | เดิม (ไลบรารีเก่า) | ใหม่ |
|---|---|---|
| `1..4` / `S+1..4` | `ff ffc ffl ffr` / `bb…` | `FFC FFC2 FFL FFR` / `BBC BBC2 BBL BBR` |
| `5` / `6` | `ffcm` / `fft` | `FFcm` / `FFtimer` (select ใส่เมื่อเลือกตัวอักษร) |
| `7` | `fft(…, act)` | `FFWhite` (S+7 = `BBWhite`) |
| `S+A S+D S+J S+L` | `spinl spinr spinl2 spinr2` | `SpinL SpinR SpinL2 SpinR2` |
| `T Y` / `S+T S+Y` | `ffcmcl ffcmcr` / `bbcm…` | `FFcmCirCleL FFcmCirCleR` / `BBcmCirCle…` |
| `;` `'` / `Z` `X` (+Shift) | `ffdircl…` / `ffdirclg…` | ชื่อเดิม (มีในไลบรารีใหม่) — **ตัด tol ออก** เพราะไลบรารีใหม่ไม่มี |
| `O` | `resetAngles` | `resetAngles` (S+O = `SetRobotAngle`) |
| `G` `H` `B` (+Shift) | `ffcmg ffcmgs ffbg` | `FFcmG FFcmGS FFBG` / `BBcmG BBcmGS BBBG` · ใหม่ `V` = `FFtimerG` |
| `N` `M` `S+M` | `spindir turndir turndirb` | `spinDirection turnDirection turnDirectionB` (ชื่อย่อ `sdg tdg tdbg`) |
| `A D Q E` (+Shift) | `spinlg spinrg turnlg turnrg turnlbg turnrbg` | `SpinLG SpinRG TurnLG TurnRG TurnLBG TurnRBG` |
| `F` / `S+F` | — | ใหม่: `spinDegree` / `turnDegree` (องศามีเครื่องหมาย) |
| `F1..F12` | `arm_*` | `ServoUp ServoDown ServoOpen ServoClose …` (ดูตาราง) |
| `S+F1..F8` | `arm_open_down …` | ท่าผสม 2 คำสั่งในบรรทัดเดียว เช่น `ServoOpen(); ServoDown();` |
| `S+C` `S+S` `S+N` | — | ใหม่: `ToCenter` / `MotorStop` / `resetAnglesDir` |

คำสั่งใหม่ของรุ่นนี้ที่เพิ่มเป็นปุ่มบนจอ: `FFL0 FFR15 FFNUM FFSUM FFBlack`, ชุดกินโค้ง `FFCirCle* FFtimerCirCle*`,
`FFdir FFdirCirCle* ffdirf ffdirg`, ชุดองศา `ffdeg ffdegg ffdegcl…`, Gyro ขั้นสูง `TurnLRG rotateDegree rotateDir spin_ffcmg turn_ffcmg …`,
ค้างมุม `SetG SetFG …`, มอเตอร์ `Move Motor GoStart GoEnd`, และบรรทัดตั้งค่าจากสเก็ตช์ตัวอย่าง

## ข้อควรรู้

- **Servo** (`ServoOpen ServoClose ServoUp …`) ไม่ได้อยู่ในไฟล์ `.h` แต่อยู่ใน `Servo.ino` ของสเก็ตช์ตัวอย่าง `UnknowRobotStormXII_Code_V3_16CH_BNO085` ต้องมีแท็บนั้นในโปรเจกต์
- `ToCenterLG()` / `ToCenterRG()` มีเขียนใน Manual.ino แต่ **ไม่มีในโค้ดไลบรารีจริง** จึงไม่ได้ใส่ (ใช้ `ToCenterG()` แทน)
- ไม่มีปุ่มแบบใส่ kp/kd เอง (เช่น `FFC(50, 0.02, 'p')`) เพราะถ้าจำนวนอาร์กิวเมนต์ไปตรง overload ของ kp ตัวอักษรจะถูกแปลงเป็นตัวเลขเงียบ ๆ — ให้พิมพ์ kp/kd เองใน IDE
- `ffdircl(speed, dir, 'p')` (สลับลำดับ) ไลบรารีตั้งใจให้คอมไพล์ไม่ผ่าน ลำดับที่ถูกคือ `ffdircl(speed, 'p', dir)` · แต่ `FFdir` / `ffdirf` ใส่ select **ไว้ท้าย**
- ค่าเริ่มต้นในโปรแกรม (speed 50 / fast 80 / slow 30, cm 30, ms 1000) และบรรทัดในแท็บ "ตั้งค่า" (`SetRobotPID(0.009, 0.12)`, `ModeSpdGyro(4, 100, -5)` …) ใช้ตัวเลขจากสเก็ตช์ตัวอย่างของไลบรารี

## ตารางคีย์ลัดทั้งหมด (สร้างจาก `python macro.py --table`)

#### ตามเส้นจนเจอแยก

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+1` | `FFC(50, 'p');` | ตามเส้น จับแยกด้วยเซนเซอร์คู่กลาง |
| `Ctrl+Alt+2` | `FFC2(50, 'p');` | ตามเส้น จับแยกด้วยริมซ้าย+ขวา (0,15) |
| `Ctrl+Alt+3` | `FFL(50, 'p');` | ตามเส้น จับแยกด้วยเซนเซอร์คู่ซ้าย |
| `Ctrl+Alt+4` | `FFR(50, 'p');` | ตามเส้น จับแยกด้วยเซนเซอร์คู่ขวา |
| `Ctrl+Alt+Shift+1` | `BBC(50, 'p');` | ถอยตามเส้น จับแยกคู่กลาง |
| `Ctrl+Alt+Shift+2` | `BBC2(50, 'p');` | ถอยตามเส้น จับแยกริมซ้าย+ขวา |
| `Ctrl+Alt+Shift+3` | `BBL(50, 'p');` | ถอยตามเส้น จับแยกคู่ซ้าย |
| `Ctrl+Alt+Shift+4` | `BBR(50, 'p');` | ถอยตามเส้น จับแยกคู่ขวา |
| ปุ่มบนจอ | `FFL0(50, 'p');` | เหมือน FFL + ริมซ้ายสุด (แยกกว้าง) |
| ปุ่มบนจอ | `FFR15(50, 'p');` | เหมือน FFR + ริมขวาสุด (แยกกว้าง) |
| ปุ่มบนจอ | `BBL0(50, 'p');` | ถอย BBL + ริมซ้ายสุด |
| ปุ่มบนจอ | `BBR15(50, 'p');` | ถอย BBR + ริมขวาสุด |
| ปุ่มบนจอ | `FFNUM(50, 'p', 7);` | ตามเส้น จับแยกที่เซนเซอร์ตัวที่ n (0-15) |
| ปุ่มบนจอ | `BBNUM(50, 'p', 7);` | ถอยตามเส้น จับแยกที่เซนเซอร์ตัวที่ n |
| ปุ่มบนจอ | `FFSUM(50, 'p', 4000);` | ตามเส้นจนผลรวมเซนเซอร์หน้า >= n (เช่น 4000) |
| ปุ่มบนจอ | `BBSUM(50, 'p', 4000);` | ถอยตามเส้นจนผลรวม >= n |

#### ตามเวลา / ระยะ / ขาว-ดำ

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+5` | `FFcm(50, 30, 'p');` | ตามเส้นตามระยะ cm (+select ถ้าเลือก) |
| `Ctrl+Alt+Shift+5` | `BBcm(50, 30, 'p');` | ถอยตามเส้นตามระยะ cm |
| `Ctrl+Alt+6` | `FFtimer(50, 1000, 'p');` | ตามเส้นตามเวลา ms (+select ถ้าเลือก) |
| `Ctrl+Alt+Shift+6` | `BBtimer(50, 1000, 'p');` | ถอยตามเส้นตามเวลา ms |
| `Ctrl+Alt+7` | `FFWhite(50, 'p');` | ตามเส้นจนเซนเซอร์หน้าขาวหมด |
| `Ctrl+Alt+Shift+7` | `BBWhite(50, 'p');` | ถอยตามเส้นจนเซนเซอร์หลังขาวหมด |
| ปุ่มบนจอ | `FFBlack(50, 'p');` | เดินหน้า (ไม่ PID) จนเซนเซอร์หน้าเจอดำ |
| ปุ่มบนจอ | `BBBlack(50, 'p');` | ถอยหลัง (ไม่ PID) จนเซนเซอร์หลังเจอดำ |

#### หมุน/เลี้ยวหาเส้น

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Shift+A` | `SpinL(50);` | หมุนซ้ายหาเส้น (เซนเซอร์หน้า) |
| `Ctrl+Alt+Shift+D` | `SpinR(50);` | หมุนขวาหาเส้น (เซนเซอร์หน้า) |
| `Ctrl+Alt+Shift+J` | `SpinL2(50);` | หมุนซ้ายข้ามไปเส้นที่ 2 |
| `Ctrl+Alt+Shift+L` | `SpinR2(50);` | หมุนขวาข้ามไปเส้นที่ 2 |
| ปุ่มบนจอ | `SpinLB(50);` | หมุนซ้ายหาเส้น (เซนเซอร์หลัง) |
| ปุ่มบนจอ | `SpinRB(50);` | หมุนขวาหาเส้น (เซนเซอร์หลัง) |
| ปุ่มบนจอ | `SpinL2B(50);` | หมุนซ้ายเส้นที่ 2 (เซนเซอร์หลัง) |
| ปุ่มบนจอ | `SpinR2B(50);` | หมุนขวาเส้นที่ 2 (เซนเซอร์หลัง) |
| ปุ่มบนจอ | `TurnLeft();` | เลี้ยวซ้ายล้อเดียว (เซนเซอร์หน้า) |
| ปุ่มบนจอ | `TurnRight();` | เลี้ยวขวาล้อเดียว (เซนเซอร์หน้า) |
| ปุ่มบนจอ | `TurnLeftB();` | เลี้ยวถอยหลังซ้ายล้อเดียว |
| ปุ่มบนจอ | `TurnRightB();` | เลี้ยวถอยหลังขวาล้อเดียว |

#### เข้ากลาง / จัดตรงเส้น

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Shift+C` | `ToCenter();` | เดินหน้าเข้ากลางหุ่น (กลางซ้ายหรือขวา) |
| ปุ่มบนจอ | `ToCenterL();` | เดินหน้าจนกลางซ้ายเจอเส้น |
| ปุ่มบนจอ | `ToCenterR();` | เดินหน้าจนกลางขวาเจอเส้น |
| ปุ่มบนจอ | `BackCenter();` | ถอยหลังเข้ากลางหุ่น |
| ปุ่มบนจอ | `LF(1000);` | จัดตรงเส้นอยู่กับที่ (เซนเซอร์หน้า) ms |
| ปุ่มบนจอ | `LB(1000);` | จัดตรงเส้นอยู่กับที่ (เซนเซอร์หลัง) ms |
| ปุ่มบนจอ | `BalanceF(1);` | จัดหุ่นตรงเส้น เซนเซอร์หน้า n ครั้ง |
| ปุ่มบนจอ | `BalanceB(1);` | จัดหุ่นตรงเส้น เซนเซอร์หลัง n ครั้ง |
| ปุ่มบนจอ | `BalanceFC(1);` | จัดตรง คู่กลาง (ขยับหน้า) n ครั้ง |
| ปุ่มบนจอ | `BalanceBC(1);` | จัดตรง คู่กลาง (ขยับถอย) n ครั้ง |

#### กินโค้ง CirCle

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+T` | `FFcmCirCleL(50, 30, 'p');` | กินโค้งซ้ายตามระยะ (cm จำนวนเต็ม) |
| `Ctrl+Alt+Y` | `FFcmCirCleR(50, 30, 'p');` | กินโค้งขวาตามระยะ (cm จำนวนเต็ม) |
| `Ctrl+Alt+Shift+T` | `BBcmCirCleL(50, 30, 'p');` | ถอยกินโค้งซ้ายตามระยะ |
| `Ctrl+Alt+Shift+Y` | `BBcmCirCleR(50, 30, 'p');` | ถอยกินโค้งขวาตามระยะ |
| ปุ่มบนจอ | `FFCirCleL(50, 'p');` | กินโค้งซ้ายจนเจอแยก |
| ปุ่มบนจอ | `FFCirCleR(50, 'p');` | กินโค้งขวาจนเจอแยก |
| ปุ่มบนจอ | `BBCirCleL(50, 'p');` | ถอยกินโค้งซ้ายจนเจอแยก |
| ปุ่มบนจอ | `BBCirCleR(50, 'p');` | ถอยกินโค้งขวาจนเจอแยก |
| ปุ่มบนจอ | `FFtimerCirCleL(50, 1000, 'p');` | กินโค้งซ้ายตามเวลา |
| ปุ่มบนจอ | `FFtimerCirCleR(50, 1000, 'p');` | กินโค้งขวาตามเวลา |
| ปุ่มบนจอ | `BBtimerCirCleL(50, 1000, 'p');` | ถอยกินโค้งซ้ายตามเวลา |
| ปุ่มบนจอ | `BBtimerCirCleR(50, 1000, 'p');` | ถอยกินโค้งขวาตามเวลา |

#### ตามเส้นจนถึงทิศ (จบโหมดเส้น)

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+;` | `ffdircl(50, 'p', 90);` | เกาะโค้งซ้ายจนหันถึงทิศ dir |
| `Ctrl+Alt+'` | `ffdircr(50, 'p', 90);` | เกาะโค้งขวาจนหันถึงทิศ dir |
| `Ctrl+Alt+Shift+;` | `bbdircl(50, 'p', 90);` | ถอยเกาะโค้งซ้ายจนถึงทิศ dir |
| `Ctrl+Alt+Shift+'` | `bbdircr(50, 'p', 90);` | ถอยเกาะโค้งขวาจนถึงทิศ dir |
| ปุ่มบนจอ | `FFdir(50, 90, 'p');` | ตามเส้นจนหันถึงทิศ dir (select ไว้ท้าย) |
| ปุ่มบนจอ | `BBdir(50, 90, 'p');` | ถอยตามเส้นจนถึงทิศ dir (select ไว้ท้าย) |
| ปุ่มบนจอ | `FFdirCirCleL(50, 90, 'p');` | กินโค้งซ้ายจนถึงทิศ dir |
| ปุ่มบนจอ | `FFdirCirCleR(50, 90, 'p');` | กินโค้งขวาจนถึงทิศ dir |
| ปุ่มบนจอ | `BBdirCirCleL(50, 90, 'p');` | ถอยกินโค้งซ้ายจนถึงทิศ dir |
| ปุ่มบนจอ | `BBdirCirCleR(50, 90, 'p');` | ถอยกินโค้งขวาจนถึงทิศ dir |
| ปุ่มบนจอ | `ffdirf(50, 90, 'p');` | ตามเส้นถึงทิศ → TrackSelectF (None→'p') |
| ปุ่มบนจอ | `bbdirb(50, 90, 'p');` | ถอยตามเส้นถึงทิศ → TrackSelectB (None→'p') |

#### ตามเส้นจนถึงทิศ (จบ TrackSelectG)

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Z` | `ffdirclg(50, 'p', 90);` | เกาะโค้งซ้ายถึง dir → TrackSelectG (None→'p') |
| `Ctrl+Alt+X` | `ffdircrg(50, 'p', 90);` | เกาะโค้งขวาถึง dir → TrackSelectG (None→'p') |
| `Ctrl+Alt+Shift+Z` | `bbdirclg(50, 'p', 90);` | ถอยเกาะโค้งซ้ายถึง dir → GB (None→'p') |
| `Ctrl+Alt+Shift+X` | `bbdircrg(50, 'p', 90);` | ถอยเกาะโค้งขวาถึง dir → GB (None→'p') |
| ปุ่มบนจอ | `ffdirg(50, 'p', 90);` | ตามเส้นถึงทิศ dir → TrackSelectG (None→'p') |
| ปุ่มบนจอ | `bbdirg(50, 'p', 90);` | ถอยตามเส้นถึงทิศ dir → TrackSelectGB (None→'p') |

#### ตามเส้นจนหมุนครบองศา

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| ปุ่มบนจอ | `ffdeg(50, 'p', 90);` | ตามเส้นจนหมุนครบ angle → TrackSelectF |
| ปุ่มบนจอ | `bbdeg(50, 'p', 90);` | ถอยตามเส้นจนหมุนครบ angle → TrackSelectB |
| ปุ่มบนจอ | `ffdegg(50, 'p', 90);` | เหมือน ffdeg จบ TrackSelectG (None→'p') |
| ปุ่มบนจอ | `bbdegg(50, 'p', 90);` | เหมือน bbdeg จบ TrackSelectGB (None→'p') |
| ปุ่มบนจอ | `ffdegcl(50, 'p', 90);` | เกาะโค้งซ้ายจนหมุนครบ angle |
| ปุ่มบนจอ | `ffdegcr(50, 'p', 90);` | เกาะโค้งขวาจนหมุนครบ angle |
| ปุ่มบนจอ | `bbdegcl(50, 'p', 90);` | ถอยเกาะโค้งซ้ายจนหมุนครบ angle |
| ปุ่มบนจอ | `bbdegcr(50, 'p', 90);` | ถอยเกาะโค้งขวาจนหมุนครบ angle |
| ปุ่มบนจอ | `ffdegclg(50, 'p', 90);` | เกาะโค้งซ้ายครบ angle → G (None→'p') |
| ปุ่มบนจอ | `ffdegcrg(50, 'p', 90);` | เกาะโค้งขวาครบ angle → G (None→'p') |
| ปุ่มบนจอ | `bbdegclg(50, 'p', 90);` | ถอยเกาะโค้งซ้ายครบ angle → GB (None→'p') |
| ปุ่มบนจอ | `bbdegcrg(50, 'p', 90);` | ถอยเกาะโค้งขวาครบ angle → GB (None→'p') |

#### Gyro วิ่งตรง

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+O` | `resetAngles();` | รีเซ็ตมุมไจโร = ทิศ 0 (ตั้งลำ/เช็กพอยต์) |
| `Ctrl+Alt+G` | `FFcmG(50, 30, 'p');` | Gyro ตรงตามระยะ เร่ง/ผ่อน |
| `Ctrl+Alt+Shift+G` | `BBcmG(50, 30, 'p');` | Gyro ถอยตรงตามระยะ เร่ง/ผ่อน |
| `Ctrl+Alt+H` | `FFcmGS(50, 30, 'p');` | Gyro ตรงตามระยะ ความเร็วคงที่ |
| `Ctrl+Alt+Shift+H` | `BBcmGS(50, 30, 'p');` | Gyro ถอยตรงตามระยะ ความเร็วคงที่ |
| `Ctrl+Alt+V` | `FFtimerG(50, 1000, 'p');` | Gyro ตรงตามเวลา ms |
| `Ctrl+Alt+Shift+V` | `BBtimerG(50, 1000, 'p');` | Gyro ถอยตรงตามเวลา ms |
| `Ctrl+Alt+B` | `FFBG(50, 'p');` | Gyro ตรงจนเซนเซอร์หน้าเจอเส้น |
| `Ctrl+Alt+Shift+B` | `BBBG(50, 'p');` | Gyro ถอยตรงจนเซนเซอร์หลังเจอเส้น |

#### ตั้งทิศ / ค้างมุม

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Shift+O` | `SetRobotAngle();` | จำมุมตอนนี้เป็นมุมอ้างอิง (ไม่ reset) |
| ปุ่มบนจอ | `ToCenterG();` | Gyro เดินตรงเข้ากลางหุ่น |
| `Ctrl+Alt+Shift+N` | `resetAnglesDir(90);` | วางหุ่นหันทิศ dir แล้วรีเซ็ตมุม |
| ปุ่มบนจอ | `setAngleOffset();` | ตั้งมุมตอนนี้เป็น 0 (เหมือน resetAngles) |
| ปุ่มบนจอ | `setHeading(90);` | ตั้งทิศที่ RunG จะล็อก (ไม่หมุนตัว) |
| ปุ่มบนจอ | `SetDirectionG(90);` | ตั้งทิศที่จะวิ่งตรงเข้าหา |
| ปุ่มบนจอ | `SetG(1000);` | ค้างที่มุมอ้างอิง ms |
| ปุ่มบนจอ | `SetGB(1000);` | ค้างที่มุมอ้างอิง (แบบถอย) ms |
| ปุ่มบนจอ | `SetFG(1000);` | จำมุมตอนนี้แล้วค้าง ms |
| ปุ่มบนจอ | `SetBG(1000);` | จำมุมตอนนี้แล้วค้าง (แบบถอย) ms |

#### Gyro หมุน/เลี้ยว

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+N` | `spinDirection(50, 90);` / `sdg(50, 90);` | หมุนอยู่กับที่ไปทิศ dir |
| `Ctrl+Alt+M` | `turnDirection(50, 90);` / `tdg(50, 90);` | เลี้ยว(เดินหน้า)ล้อเดียวไปทิศ dir |
| `Ctrl+Alt+Shift+M` | `turnDirectionB(50, 90);` / `tdbg(50, 90);` | เลี้ยว(ถอยหลัง)ล้อเดียวไปทิศ dir |
| `Ctrl+Alt+A` | `SpinLG(50, 90);` | หมุนซ้ายอยู่กับที่ angle° |
| `Ctrl+Alt+D` | `SpinRG(50, 90);` | หมุนขวาอยู่กับที่ angle° |
| `Ctrl+Alt+Q` | `TurnLG(50, 90);` | เลี้ยวซ้ายล้อเดียว (เดินหน้า) |
| `Ctrl+Alt+E` | `TurnRG(50, 90);` | เลี้ยวขวาล้อเดียว (เดินหน้า) |
| `Ctrl+Alt+Shift+Q` | `TurnLBG(50, 90);` | เลี้ยวซ้ายล้อเดียว (ถอยหลัง) |
| `Ctrl+Alt+Shift+E` | `TurnRBG(50, 90);` | เลี้ยวขวาล้อเดียว (ถอยหลัง) |
| `Ctrl+Alt+F` | `spinDegree(50, 90);` | หมุนอยู่กับที่ angle° (+ขวา / -ซ้าย) |
| `Ctrl+Alt+Shift+F` | `turnDegree(50, 90);` | เลี้ยวหน้าล้อเดียว angle° (+ขวา / -ซ้าย) |
| ปุ่มบนจอ | `turnDegreeB(50, 90);` | เลี้ยวถอยล้อเดียว angle° (+/-) |

#### Gyro ขั้นสูง (โค้ง S / arc / คอมโบ)

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| ปุ่มบนจอ | `turnDegree_none(50, 90);` | เลี้ยวหน้า angle° ไม่เบรก (ต่อโค้ง) |
| ปุ่มบนจอ | `turnDegreeb_none(50, 90);` | เลี้ยวถอย angle° ไม่เบรก |
| ปุ่มบนจอ | `turnDirection_none(50, 90);` / `turndir_none(50, 90);` | เลี้ยวหน้าไปทิศ dir ไม่เบรก |
| ปุ่มบนจอ | `turnDirectionb_none(50, 90);` / `turndirb_none(50, 90);` | เลี้ยวถอยไปทิศ dir ไม่เบรก |
| ปุ่มบนจอ | `TurnLRG(50, 90);` | ตีโค้ง S เดินหน้า ซ้ายก่อนแล้วสวนขวา |
| ปุ่มบนจอ | `TurnRLG(50, 90);` | ตีโค้ง S เดินหน้า ขวาก่อนแล้วสวนซ้าย |
| ปุ่มบนจอ | `TurnLRBG(50, 90);` | ตีโค้ง S ถอยหลัง ซ้ายก่อนแล้วสวนขวา |
| ปุ่มบนจอ | `TurnRLBG(50, 90);` | ตีโค้ง S ถอยหลัง ขวาก่อนแล้วสวนซ้าย |
| ปุ่มบนจอ | `rotateDegree(60, 20, 90);` | โค้งกำหนดล้อ L,R จนหมุนครบ angle แล้วเบรก |
| ปุ่มบนจอ | `rotateDegree_none(60, 20, 90);` | โค้งกำหนดล้อ ครบ angle แล้วไหลต่อ |
| ปุ่มบนจอ | `rotateDir(60, 20, 'p', 90);` | โค้งกำหนดล้อจนหันทิศ dir (+select / 'n' / 'f') |
| ปุ่มบนจอ | `rotateDir_none(60, 20, 90);` | โค้งกำหนดล้อจนหันทิศ dir แล้วไหลต่อ |
| ปุ่มบนจอ | `spin_ffcmg(50, 30, 'p', 90);` | หมุนเข้าทิศ dir แล้ว Gyro วิ่งหน้า cm |
| ปุ่มบนจอ | `spin_bbcmg(50, 30, 'p', 90);` | หมุนเข้าทิศ dir แล้ว Gyro ถอย cm |
| ปุ่มบนจอ | `turn_ffcmg(50, 30, 'p', 90);` | เลี้ยวหน้าเข้าทิศ dir แล้ววิ่งหน้า cm |
| ปุ่มบนจอ | `turn_bbcmg(50, 30, 'p', 90);` | เลี้ยวหน้าเข้าทิศ dir แล้วถอย cm |
| ปุ่มบนจอ | `turnb_ffcmg(50, 30, 'p', 90);` | เลี้ยวถอยเข้าทิศ dir แล้ววิ่งหน้า cm |
| ปุ่มบนจอ | `turnb_bbcmg(50, 30, 'p', 90);` | เลี้ยวถอยเข้าทิศ dir แล้วถอย cm |

#### Servo (ฟังก์ชันใน Servo.ino)

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+F1` | `ServoOpen(); ServoUp();` | ท่าเตรียม: อ้า + ยก (ตามตัวอย่าง setup) |
| `Ctrl+Alt+F2` | `ServoUp();` | ยกขึ้น |
| `Ctrl+Alt+F3` | `ServoUp45();` | ยกครึ่งทาง |
| `Ctrl+Alt+F4` | `ServoDown();` | วางลง |
| `Ctrl+Alt+F5` | `ServoOpen();` | อ้า |
| `Ctrl+Alt+F6` | `ServoClose();` | หนีบ |
| `Ctrl+Alt+F7` | `ServoLOpen();` | อ้าเฉพาะซ้าย |
| `Ctrl+Alt+F8` | `ServoROpen();` | อ้าเฉพาะขวา |
| `Ctrl+Alt+F9` | `ServoOpenMax();` | อ้าสุด |
| `Ctrl+Alt+F10` | `ServoCloseSmall();` | หนีบชิ้นเล็ก |
| `Ctrl+Alt+F11` | `ServoGrip();` | หนีบแน่น (Close +15°) |
| `Ctrl+Alt+F12` | `ServoOpen2();` | อ้าแบบที่ 2 |

#### Servo ท่าผสม

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Shift+F1` | `ServoOpen(); ServoDown();` | อ้า → วาง |
| `Ctrl+Alt+Shift+F2` | `ServoDown(); ServoOpen();` | วาง → อ้า |
| `Ctrl+Alt+Shift+F3` | `ServoOpen(); ServoUp();` | อ้า → ยก |
| `Ctrl+Alt+Shift+F4` | `ServoUp(); ServoOpen();` | ยก → อ้า |
| `Ctrl+Alt+Shift+F5` | `ServoDown(); ServoClose();` | วาง → หนีบ |
| `Ctrl+Alt+Shift+F6` | `ServoClose(); ServoDown();` | หนีบ → วาง |
| `Ctrl+Alt+Shift+F7` | `ServoUp(); ServoClose();` | ยก → หนีบ |
| `Ctrl+Alt+Shift+F8` | `ServoClose(); ServoUp();` | หนีบ → ยก |

#### Servo ทีละข้าง

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| ปุ่มบนจอ | `ServoOpenMax2();` | อ้าสุดแบบที่ 2 |
| ปุ่มบนจอ | `ServoLClose();` | หนีบเฉพาะซ้าย |
| ปุ่มบนจอ | `ServoRClose();` | หนีบเฉพาะขวา |
| ปุ่มบนจอ | `ServoLCloseSmall();` | หนีบเล็กเฉพาะซ้าย |
| ปุ่มบนจอ | `ServoRCloseSmall();` | หนีบเล็กเฉพาะขวา |
| ปุ่มบนจอ | `ServoLOpenMax();` | อ้าสุดเฉพาะซ้าย |
| ปุ่มบนจอ | `ServoROpenMax();` | อ้าสุดเฉพาะขวา |
| ปุ่มบนจอ | `ServoLOpenMax2();` | อ้าสุดแบบ 2 เฉพาะซ้าย |
| ปุ่มบนจอ | `ServoROpenMax2();` | อ้าสุดแบบ 2 เฉพาะขวา |
| ปุ่มบนจอ | `ServoWrite(1, 90);` | เซอร์โวเลข n (0 ยก/1 ซ้าย/2 ขวา หรือ 34-39) ไปมุม angle |

#### มอเตอร์ / ออกตัว

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Shift+S` | `MotorStop();` | หยุดมอเตอร์ทันที |
| ปุ่มบนจอ | `MotorStop(1000);` | หยุดมอเตอร์แล้วหน่วง ms |
| ปุ่มบนจอ | `Move(60, 20, 1000);` | สั่งล้อซ้าย L ขวา R นาน ms |
| ปุ่มบนจอ | `Motor(60, 20);` | สั่งล้อซ้าย L ขวา R (ไม่หน่วง) |
| ปุ่มบนจอ | `GoStart(50);` | วิ่งจนพ้นจุด Start |
| ปุ่มบนจอ | `GoEnd(50);` | วิ่งจนถึงจุด Finish |
| ปุ่มบนจอ | `TestMotor();` | ทดสอบมอเตอร์ ซ้ายแล้วขวา |

#### ตั้งค่า / เซนเซอร์ (ค่าจากตัวอย่าง)

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| ปุ่มบนจอ | `#include <UnknowRobot_STORMXII_V3_BNO085.h>` | include ไลบรารี (บนสุดของไฟล์) |
| ปุ่มบนจอ | `RobotSetup();` | เริ่มระบบทั้งหมด (บรรทัดแรกของ setup) |
| ปุ่มบนจอ | `LoadCalibrateFromEEPROM();` | โหลดค่าคาลิเบรตจาก EEPROM |
| ปุ่มบนจอ | `CalibrateSensor();` | คาลิเบรตเซนเซอร์ แล้วเซฟ EEPROM |
| ปุ่มบนจอ | `swOK();` | รอกด OK (กด START = คาลิเบรต) |
| ปุ่มบนจอ | `swSTART();` | รอกด START |
| ปุ่มบนจอ | `SerialCalibrate_AllSensor();` | Serial: ค่าคาลิเบรตทุกเซนเซอร์ |
| ปุ่มบนจอ | `SerialPositionFB();` | Serial: ตำแหน่งเส้น หน้า/หลัง |
| ปุ่มบนจอ | `TrackLineColor(BLACK);` | สีเส้น BLACK / WHITE |
| ปุ่มบนจอ | `RefLineValue(500);` | ค่าแบ่งขาว/ดำ หน้า-หลัง |
| ปุ่มบนจอ | `RefCenterLineValue(500);` | ค่าแบ่งขาว/ดำ คู่กลาง |
| ปุ่มบนจอ | `SetRobotPID(0.009, 0.12);` | KP, KD หลักของการวิ่งตามเส้น |
| ปุ่มบนจอ | `SetSensorTrackLine_CH(16);` | จำนวนเซนเซอร์จับแยก 6-16 |
| ปุ่มบนจอ | `set_sensor_track_line(0, 15);` | ช่วงเซนเซอร์ที่ใช้วิ่ง |
| ปุ่มบนจอ | `set_line_center(1);` | เข้ากลาง 0 = เดินตรง, 1 = ตามเส้น |
| ปุ่มบนจอ | `ModeSpdPID(1, 100, -100);` | โหมดจำกัดกำลังล้อ (ตามเส้น) |
| ปุ่มบนจอ | `ModeSpdGyro(4, 100, -5);` | โหมดจำกัดกำลังล้อ (Gyro) |
| ปุ่มบนจอ | `SetTurnSpeed(50);` | ความเร็ว SpinL/SpinR ที่ไม่ใส่ speed |
| ปุ่มบนจอ | `SetToCenterSpeed(30);` | ความเร็วเดินเข้ากลางหุ่น |
| ปุ่มบนจอ | `SetGyroRun(0.25, 2.5);` | kp, kd วิ่งตรงด้วย Gyro |
| ปุ่มบนจอ | `SetGyroSpin(1.3, 0.8, 65, 20, 15.0, 1.0);` | ค่าหมุนอยู่กับที่ด้วย Gyro |
| ปุ่มบนจอ | `SetGyroTurn(1.3, 0.8, 65, 20, 15.0, 1.0);` | ค่าเลี้ยวล้อเดียวด้วย Gyro |
| ปุ่มบนจอ | `set_auto_align(20);` | คลาดเกิน 20° หมุนตั้งลำก่อน (0 = ปิด) |
| ปุ่มบนจอ | `set_track_snap90(true);` | ปัดมุมเข้าแกน 90° ที่ทางแยก |

#### กำหนดเอง

| คีย์ลัด | ผลลัพธ์ (ค่าตัวอย่าง) | ความหมาย |
|---|---|---|
| `Ctrl+Alt+Shift+0` | `FFC(80, 'p');` | FFC ความเร็ว FAST_SPEED |
| `Ctrl+Alt+Shift+9` | `FFC(30, 'c');` | FFC ความเร็ว SLOW_SPEED |
| `Ctrl+Alt+Shift+8` | `delay(1000);` | หน่วงเวลา (Arduino) |

#### ปรับค่า / ระบบ (ไม่พิมพ์ลง IDE)

| คีย์ลัด | หน้าที่ |
|---|---|
| `Ctrl+Alt+=` | speed +5 |
| `Ctrl+Alt+-` | speed -5 |
| `Ctrl+Alt+8` | speed = SLOW (30) |
| `Ctrl+Alt+9` | speed = DEFAULT (50) |
| `Ctrl+Alt+0` | speed = FAST (80) |
| `Ctrl+Alt+]` | cm +5 |
| `Ctrl+Alt+[` | cm -5 |
| `Ctrl+Alt+Shift+]` | ms +100 |
| `Ctrl+Alt+Shift+[` | ms -100 |
| `Ctrl+Alt+I` | dir = 0   (I = บน) |
| `Ctrl+Alt+L` | dir = 90  (L = ขวา) |
| `Ctrl+Alt+K` | dir = 180 (K = ล่าง) |
| `Ctrl+Alt+J` | dir = 270 (J = ซ้าย) |
| `Ctrl+Alt+P` | act = 'p' ผ่านแยก |
| `Ctrl+Alt+C` | act = 'c' เข้ากลาง |
| `Ctrl+Alt+S` | act = 's' หยุด |
| `Ctrl+Alt+,` | act = 'l' (, = <) |
| `Ctrl+Alt+.` | act = 'r' (. = >) |
| `Ctrl+Alt+/` | act ตัวถัดไป |
| `Ctrl+Alt+Shift+/` | act ตัวก่อนหน้า |
| `Ctrl+Alt+U` | act สลับเล็ก/ใหญ่ (p↔P) |
| `Ctrl+Alt+R` | พิมพ์คำสั่งล่าสุดซ้ำ (ค่าปัจจุบัน) |
| `Ctrl+Alt+Shift+P` | หยุด/เปิด มาโครชั่วคราว |
| `Ctrl+Alt+Shift+W` | ซ่อน/แสดงหน้าต่าง |
| `Ctrl+Shift+Q` | ปิดโปรแกรม |
