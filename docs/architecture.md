# MonitorEye 架构详解

## 一句话概述

MonitorEye 是一个**纯 Python 的监护仪 GUI 自动化测试工具包**。它通过 VNC 协议连接监护仪屏幕，用图像识别找按钮/图标，用 OCR 读数字，用 pytest 写测试断言。内置一个假的监护仪模拟器，没有真机也能跑。

---

## 整体架构图

```
你写的测试脚本（pytest）
        │
        ▼
┌─ MonitorScreen ──────────────────────────────────┐
│  用户唯一需要接触的入口类                          │
│                                                   │
│  ┌─ VNCConnection ─┐  ┌─ ImageFinder ─┐         │
│  │  连接监护仪屏幕   │  │  在屏幕上找图片│         │
│  │  截图、点击、打字 │  │  模板匹配算法  │         │
│  └────────┬────────┘  └──────┬────────┘         │
│           │                   │                   │
│  ┌────────▼────────┐  ┌──────▼────────┐         │
│  │  vncdotool CLI  │  │   OpenCV      │         │
│  │  (外部工具)      │  │  matchTemplate│         │
│  └─────────────────┘  └──────────────┘          │
│                                                   │
│  ┌─ OCREngine ─────┐  ┌─ Region ──────┐         │
│  │  读屏幕上的数字   │  │  屏幕的一块区域│         │
│  │  预处理 + Tesseract│ │  限定搜索范围  │         │
│  └─────────────────┘  └──────────────┘          │
└───────────────────────────────────────────────────┘
        │
        │ 连接真机 或 连接模拟器
        ▼
┌─ MockVNCServer ──────────────────────────────────┐
│  假的 VNC 服务器（开发/演示时用）                   │
│                                                   │
│  ┌─ MonitorRenderer ─┐                           │
│  │  用 Pillow 画一个   │                           │
│  │  假的监护仪界面     │                           │
│  │  HR=75 SpO2=98 ... │                           │
│  └────────────────────┘                           │
└───────────────────────────────────────────────────┘
```

---

## 文件目录结构

```
monitor-eye/
├── monitor_eye/                 ← Python 包（核心代码都在这里）
│   ├── __init__.py              ← 包入口，对外暴露 5 个名字
│   ├── screen.py                ← ★ 最重要的文件：MonitorScreen 和 Region
│   ├── connection.py            ← VNC 连接管理
│   ├── finder.py                ← 图像匹配引擎
│   ├── ocr.py                   ← OCR 数字识别引擎
│   ├── exceptions.py            ← 自定义异常
│   ├── pytest_plugin.py         ← pytest 插件（自动注册 fixture）
│   └── mock/                    ← 内置模拟器子包
│       ├── __init__.py
│       ├── renderer.py          ← 用 Pillow 画假监护仪画面
│       └── vnc_server.py        ← 最小化 VNC 服务器
├── tests/                       ← 测试（41 个测试用例）
│   ├── test_finder.py           ← 图像匹配测试
│   ├── test_ocr.py              ← OCR 测试
│   ├── test_mock_renderer.py    ← 渲染器测试
│   ├── test_mock_vnc.py         ← VNC 服务器测试
│   ├── test_connection.py       ← 连接管理测试
│   ├── test_screen.py           ← Screen/Region API 测试
│   ├── test_plugin.py           ← pytest 插件测试
│   ├── test_integration.py      ← 端到端集成测试
│   ├── conftest.py              ← 共享 fixture
│   └── __init__.py
├── examples/
│   └── test_comen_monitor.py    ← 科曼监护仪测试示例
├── pyproject.toml               ← 项目配置（依赖、构建、pytest 设置）
├── README.md
└── .gitignore
```

---

## 每个文件详解

### `__init__.py` — 包入口（9 行）

```python
from monitor_eye.screen import MonitorScreen, Region
from monitor_eye.finder import Match
from monitor_eye.exceptions import FindFailed, ConnectionError
```

**作用：** 让用户可以直接 `from monitor_eye import MonitorScreen`，不需要知道内部文件结构。

**对外暴露 5 个名字：**
| 名字 | 类型 | 用途 |
|------|------|------|
| `MonitorScreen` | 类 | 主入口，连接监护仪 |
| `Region` | 类 | 屏幕上的一块矩形区域 |
| `Match` | 数据类 | 图像匹配结果（坐标+置信度） |
| `FindFailed` | 异常 | 找不到图片时抛出 |
| `ConnectionError` | 异常 | VNC 连接失败时抛出 |

---

### `screen.py` — 用户最常接触的文件（129 行）

包含两个类：

#### `MonitorScreen` — 主入口

**生活类比：** 就像你坐在监护仪前面，眼睛看屏幕、手指点按钮。MonitorScreen 就是你的"眼睛+手"。

**关键方法：**

| 方法 | 做什么 | 类比 |
|------|--------|------|
| `MonitorScreen("192.168.1.100")` | 通过 VNC 连接真实监护仪 | 走到监护仪前面 |
| `MonitorScreen.from_mock()` | 启动假的监护仪并连上 | 打开模拟器练习 |
| `capture("截图.png")` | 截取当前屏幕 | 拍照存档 |
| `find("alarm.png")` | 在屏幕上找某个图标 | 用眼睛找报警灯 |
| `exists("alarm.png")` | 同上但找不到不报错 | 瞄一眼有没有 |
| `click("button.png")` | 找到图标并点击 | 用手指按按钮 |
| `region(x, y, w, h)` | 框出屏幕的一块区域 | 只看心率那一块 |
| `disconnect()` | 断开连接 | 离开监护仪 |

**内部组合了 3 个引擎：**
```python
self._conn = VNCConnection(...)    # 负责网络通信
self._finder = ImageFinder()       # 负责图像匹配
self._ocr = OCREngine()            # 负责文字识别
```

#### `Region` — 屏幕上的一块区域

**生活类比：** 监护仪屏幕很大，你说"看心率那个区域"，Region 就是用一个矩形框把那块区域圈出来。

| 方法 | 做什么 |
|------|--------|
| `region.read_number()` | 对这个区域做 OCR 读数字 |
| `region.text()` | 对这个区域做 OCR 读文字 |
| `region.find("icon.png")` | 只在这个区域内找图片（更快更准） |
| `region.capture("hr.png")` | 只截取这个区域 |

---

### `connection.py` — VNC 连接管理（83 行）

**作用：** 封装 vncdotool 命令行工具，提供简单的 Python 接口。

**为什么用命令行而不是 Python API？**
vncdotool 的 Python API 基于 Twisted 异步框架。Twisted 有一个"reactor"（事件循环），在一个进程里只能启动一次。pytest 跑多个测试时会冲突。所以改用 `subprocess` 调命令行，每次调用都是独立进程，完全没有冲突。

**工作方式：**
```
connection.capture()
    ↓
subprocess.run(["vncdotool", "-s", "localhost::5900", "capture", "/tmp/xxx.png"])
    ↓
读取 /tmp/xxx.png → OpenCV 加载 → 返回 numpy 数组
    ↓
删除临时文件
```

| 方法 | 实际执行的命令 |
|------|--------------|
| `connect()` | `vncdotool capture /tmp/probe.png`（探测连通性） |
| `capture()` | `vncdotool capture /tmp/xxx.png` |
| `click(x, y)` | `vncdotool move 400 300 click 1` |
| `type_text("hello")` | `vncdotool type hello` |

---

### `finder.py` — 图像匹配引擎（107 行）

**作用：** 在一张大图（屏幕截图）里找一张小图（模板图片）的位置。

**核心算法：** OpenCV 的 `matchTemplate`（模板匹配）

**生活类比：** 就像"大家来找茬"游戏——给你一个图标模板，在整个屏幕上滑动对比，找到最像的位置。

**两个类：**

#### `Match` — 匹配结果
```python
@dataclass
class Match:
    x: int        # 左上角 X 坐标
    y: int        # 左上角 Y 坐标
    width: int    # 宽度
    height: int   # 高度
    score: float  # 相似度（0~1，越高越像）
```
- `match.center` → 中心点坐标（点击时用）
- `match.click_point` → 同上，语义更清晰

#### `ImageFinder` — 查找引擎
- `find(screen, template)` → 找最佳匹配，低于置信度返回 None
- `find_all(screen, template)` → 找所有匹配，用 NMS（非极大值抑制）去除重复

**NMS 是什么？**
模板匹配会在同一个图标周围产生很多"差不多"的匹配点。NMS 就是只保留得分最高的那个，把太近的其他点丢掉。

---

### `ocr.py` — OCR 数字识别引擎（80 行）

**作用：** 从屏幕截图中读出数字（心率 75、血氧 98 等）。

**核心问题：** SikuliX 用 Tesseract 直接识别监护仪屏幕，准确率只有约 10%。原因有三：
1. 监护仪是黑底白字 → Tesseract 默认处理白底黑字
2. 屏幕上的数字很小 → Tesseract 对小于 12px 的字体识别差
3. 数字 "13" 会被认成 "'|3" → Tesseract 默认识别所有字符

**MonitorEye 的预处理管线（5 步）：**

```
步骤 1: 彩色 → 灰度
        ↓
步骤 2: 检测背景亮度 → 如果是深色背景就自动反色（黑变白、白变黑）
        ↓  解决问题 1
步骤 3: 如果图片高度 < 50px → 放大到 60px
        ↓  解决问题 2
步骤 4: OTSU 自适应二值化 → 变成纯黑白图
        ↓
步骤 5: 形态学膨胀（2x2） → 把笔画加粗一点
        ↓
送入 Tesseract，只允许识别 0123456789./
                               解决问题 3
```

| 方法 | 做什么 | 返回 |
|------|--------|------|
| `preprocess(image)` | 执行上面 5 步 | 处理后的二值图 |
| `read_text(image)` | 预处理 + OCR | 字符串如 "120/80" |
| `read_number(image)` | 预处理 + OCR + 提取数字 | 整数如 75，或 None |

---

### `exceptions.py` — 自定义异常（30 行）

最简单的文件。定义了两个异常：

| 异常 | 什么时候抛出 | 示例 |
|------|-------------|------|
| `FindFailed` | `find("xxx.png")` 找不到图片 | `FindFailed: 'alarm.png' (waited 5s)` |
| `ConnectionError` | VNC 连不上 | `Cannot connect to 192.168.1.100:5900` |

两者都继承自 `MonitorEyeError` 基类，方便统一捕获：
```python
try:
    screen.find("alarm.png", timeout=5)
except FindFailed:
    print("没有报警，正常")
```

---

### `pytest_plugin.py` — pytest 插件（20 行）

**作用：** 注册一个 `monitor_screen` fixture，任何测试文件都能直接用。

**原理：** `pyproject.toml` 里注册了 pytest11 入口点：
```toml
[project.entry-points."pytest11"]
monitor_eye = "monitor_eye.pytest_plugin"
```
pytest 启动时会自动加载这个插件，fixture 全局可用。

**fixture 做了什么：**
1. 启动 Mock VNC Server
2. 连接上去，返回 MonitorScreen
3. 测试结束后自动断开连接、关闭服务器

```python
# 在任何测试文件里直接用，不需要 import
def test_heart_rate(monitor_screen):
    hr = monitor_screen.region(20, 40, 200, 80).read_number()
    assert hr is not None
```

---

### `mock/renderer.py` — 模拟监护仪画面渲染器（166 行）

**作用：** 用 Pillow（Python 图像库）画一个假的监护仪界面。

**输出效果：**
```
┌──────────────────────────────────────┐
│ HR        NIBP                       │  ← 标签（小字）
│ 75  bpm   120/80   mmHg             │  ← 数值（大字）
│                                      │
│ SpO2      RESP         TEMP          │
│ 98  %     16   rpm     36.8  °C     │
│                                      │
│ ～～～～～～～ ECG 波形 ～～～～～～～  │
│                                      │
│                            [SILENCE] │  ← 静音按钮
└──────────────────────────────────────┘
```

**关键方法：**

| 方法 | 做什么 |
|------|--------|
| `render()` | 画一帧画面 → 返回 800x600 的 numpy 数组（BGR 格式） |
| `set_vitals(hr=180)` | 修改生命体征数值 |
| `trigger_alarm("hr_high")` | 激活报警 → 顶部出现红色条 |
| `silence_alarm()` | 关闭报警 |
| `tick()` | 模拟时间流逝 → 数值微微波动（±1），ECG 波形移动 |

**字体回退链：**
macOS Helvetica → Linux DejaVu → Pillow 内置默认字体

---

### `mock/vnc_server.py` — 最小化 VNC 服务器（200 行）

**作用：** 实现 RFB 3.3 协议，让 vncdotool 能连上来截图和操作。

**这是整个项目技术含量最高的文件。**

**什么是 RFB 协议？**
Remote Frame Buffer，VNC 底层用的协议。简单说就是：
- 服务端告诉客户端"我的屏幕有多大、像素格式是什么"
- 客户端说"给我最新的画面"
- 服务端把像素数据发过去
- 客户端说"用户在 (x,y) 点了一下鼠标"

**通信流程：**
```
客户端 (vncdotool)              服务端 (MockVNCServer)
        │                              │
        │◄──── "RFB 003.003\n" ────────│  1. 服务端发版本号
        │───── "RFB 003.003\n" ───────►│  2. 客户端回版本号
        │◄──── 安全类型=1(无密码) ──────│  3. 服务端说不需要密码
        │───── ClientInit(共享=1) ─────►│  4. 客户端说"我要连"
        │◄──── ServerInit ─────────────│  5. 服务端发屏幕信息
        │      (800x600, 32bpp,        │     （宽高、像素格式、名字）
        │       名字="MonitorEye Mock") │
        │                              │
        │───── 请求画面更新 ──────────►│  6. 客户端要截图
        │◄──── 整屏像素数据 ───────────│  7. 服务端发 800x600x4 字节
        │      (800*600*4 = 1.92MB)    │
        │                              │
        │───── 鼠标点击(715,570) ─────►│  8. 客户端发点击事件
        │      服务端检查是否点了静音按钮 │
```

**关键方法：**

| 方法 | 做什么 |
|------|--------|
| `start()` | 开一个后台线程监听端口 |
| `stop()` | 关闭套接字和线程 |
| `_handshake()` | 版本号交换 + 安全类型协商 |
| `_server_init()` | 发送屏幕尺寸和像素格式 |
| `_message_loop()` | 循环处理客户端消息 |
| `_send_framebuffer_update()` | 调 renderer.render() 拿画面，转成原始像素发出去 |
| `_handle_pointer()` | 收到鼠标点击 → 判断是否点了 SILENCE 按钮 |
| `_recv_exact(n)` | 确保收到恰好 n 个字节（TCP 可能分片） |

---

### `examples/test_comen_monitor.py` — 科曼监护仪测试示例（41 行）

**作用：** 展示"如果你要测试真实的科曼监护仪，测试代码长什么样"。

3 个测试用例：

| 用例 | 做什么 |
|------|--------|
| TC-01 截图 | 连接 → 截图保存 → 验证截图非空 |
| TC-02 心率范围 | OCR 读心率 → 断言在 30~250 之间 |
| TC-03 静音报警 | 触发报警 → 点击静音 → 验证报警消失 |

**切换真机只需改一行：**
```python
# Mock 模式（现在用的）
screen = MonitorScreen.from_mock()

# 真机模式（以后用的）
screen = MonitorScreen("192.168.1.100", port=5900, password="xxx")
```

---

### `pyproject.toml` — 项目配置（27 行）

| 配置项 | 值 | 含义 |
|--------|-----|------|
| `name` | monitor-eye | 包名 |
| `version` | 0.1.0 | 版本号 |
| `requires-python` | >=3.9 | 最低 Python 版本 |
| `dependencies` | 5 个库 | 运行时依赖 |
| `dev` | pytest, pytest-html | 开发时额外依赖 |
| `pytest11` | monitor_eye.pytest_plugin | 自动注册 pytest 插件 |
| `testpaths` | tests | pytest 默认搜索目录 |

**5 个运行时依赖：**

| 库 | 用在哪里 | 干什么 |
|----|---------|--------|
| `vncdotool` | connection.py | VNC 协议通信 |
| `opencv-python-headless` | finder.py, ocr.py | 图像匹配、图像预处理 |
| `pytesseract` | ocr.py | 调用 Tesseract OCR 引擎 |
| `Pillow` | renderer.py | 画模拟监护仪界面 |
| `numpy` | 几乎所有文件 | 图像数据的载体（数组） |

---

## 数据流总结

一次 `screen.region(20, 40, 200, 80).read_number()` 背后发生了什么：

```
1. screen.region(20, 40, 200, 80)
   → 创建 Region 对象，记住这块区域的坐标

2. region.read_number()
   → 调用 screen._capture_raw()

3. screen._capture_raw()
   → 调用 connection.capture()

4. connection.capture()
   → subprocess 执行: vncdotool -s localhost::15999 capture /tmp/xxx.png
   → vncdotool 通过 VNC 协议连到 MockVNCServer
   → MockVNCServer 调 renderer.render() 画一帧
   → 像素数据通过 RFB 协议传回
   → vncdotool 保存为 PNG
   → OpenCV 读取 PNG → numpy 数组 (600, 800, 3)
   → 删除临时文件

5. region._crop(frame)
   → 从 800x600 的全屏截图中裁出 (20,40) 到 (220,120) 的区域

6. ocr.read_number(cropped)
   → preprocess(): 灰度 → 反色 → 放大 → 二值化 → 膨胀
   → Tesseract OCR → "75"
   → 提取数字 → int(75)
   → 返回 75
```

---

## 测试文件说明

| 测试文件 | 测什么 | 数量 | 需要 VNC？ |
|---------|--------|------|-----------|
| `test_finder.py` | 图像匹配正确性 | 6 | 不需要（纯内存图像） |
| `test_ocr.py` | OCR 预处理+识别 | 7 | 不需要（生成测试图片） |
| `test_mock_renderer.py` | 渲染器输出正确性 | 6 | 不需要（纯内存） |
| `test_mock_vnc.py` | VNC 服务器协议 | 7 | 需要（自启 Mock） |
| `test_connection.py` | VNC 连接封装 | 4 | 需要（自启 Mock） |
| `test_screen.py` | Screen/Region API | 5 | 需要（自启 Mock） |
| `test_plugin.py` | pytest 插件 | 1 | 需要（自启 Mock） |
| `test_integration.py` | 端到端流程 | 2 | 需要（自启 Mock） |
| **examples/test_comen_monitor.py** | **示例用例** | **3** | **需要（自启 Mock）** |
| **合计** | | **41** | |
