# MonitorEye

纯 Python 医疗监护仪 GUI 测试工具包 —— 轻量级 SikuliX 替代方案。

## 为什么选择 MonitorEye？

SikuliX 是主流的开源 GUI 自动化工具，但在嵌入式医疗设备测试中存在关键缺陷：

| SikuliX 的问题 | MonitorEye 的方案 |
|---|---|
| 仅支持 Jython 2.7 | Python 3.9+ |
| 依赖 Java（~80MB） | `pip install`（~5MB） |
| VNC 协议兼容性差（仅 RFB 3.x，特殊键失效） | vncdotool（RFB 3.3-3.8） |
| OCR 对小字体/反色文字识别率仅 ~10% | 预处理流水线：自动反色、放大、数字白名单 |
| 无 pytest 集成 | 原生 pytest fixture |
| 不支持无头 CI/CD | 默认无头运行 |

## 快速开始

```bash
# 系统依赖
brew install tesseract  # macOS
# apt install tesseract-ocr  # Linux

# 安装 MonitorEye
cd monitor-eye
pip install -e ".[dev]"

# 运行示例测试（使用内置 Mock，无需真实硬件）
pytest examples/test_comen_monitor.py -v
```

## 使用示例

```python
from monitor_eye import MonitorScreen

# 连接到 Mock 服务器（无需硬件）
screen = MonitorScreen.from_mock()

# 或连接真实监护仪（通过 VNC）
# screen = MonitorScreen("192.168.1.100", port=5900)

# 通过 OCR 读取心率
hr = screen.region(20, 40, 200, 80).read_number()
print(f"心率: {hr} bpm")

# 查找并点击图标
screen.click("alarm_icon.png")

# 截图保存
screen.capture("evidence/screenshot.png")

screen.disconnect()
```

## pytest Fixture

MonitorEye 自动注册 `monitor_screen` fixture：

```python
def test_heart_rate(monitor_screen):
    hr = monitor_screen.region(20, 40, 200, 80).read_number()
    assert hr is None or 30 < hr < 250

def test_alarm_silence(monitor_screen):
    monitor_screen._mock_server.renderer.trigger_alarm("hr_high")
    monitor_screen._conn.click(715, 570)
    assert not monitor_screen._mock_server.renderer.alarm_active
```

## 架构

```
MonitorScreen           ← 用户 API
├── VNCConnection       ← vncdotool 封装（CLI 子进程）
├── ImageFinder         ← OpenCV 模板匹配 + NMS
├── OCREngine           ← Tesseract + 预处理流水线
└── MockVNCServer       ← 内置 RFB 3.3 服务器（用于测试）
    └── MonitorRenderer ← Pillow 模拟监护仪显示
```

### OCR 预处理流水线

解决 SikuliX 的三个具体缺陷：

```
原始图像 → 灰度化 → 自动反色（深色背景）→ 放大（小字体）
  → 形态学膨胀 → OTSU 二值化 → Tesseract（数字白名单）
```

1. **自动反色** — 修复白字黑底识别失败（SikuliX Issue #440）
2. **放大** — 修复小字体（<12px）识别失败
3. **数字白名单** — 修复 "13" → "'|3" 误识别

## 项目结构

```
monitor-eye/
├── monitor_eye/
│   ├── __init__.py          # 公共 API 导出
│   ├── screen.py            # MonitorScreen + Region
│   ├── connection.py        # VNC 连接（vncdotool）
│   ├── finder.py            # 图像匹配（OpenCV）
│   ├── ocr.py               # OCR 引擎（Tesseract）
│   ├── exceptions.py        # FindFailed, ConnectionError
│   ├── pytest_plugin.py     # monitor_screen fixture
│   └── mock/
│       ├── vnc_server.py    # 最小化 RFB 3.3 VNC 服务器
│       └── renderer.py      # Pillow 监护仪显示渲染器
├── tests/                   # 41 个测试，全部通过
├── examples/
│   └── test_comen_monitor.py
└── pyproject.toml
```

## 环境要求

- Python 3.9+
- Tesseract OCR（`brew install tesseract` / `apt install tesseract-ocr`）

## 运行测试

```bash
pytest tests/ examples/ -v
```

## 目标设备

适用于任何可通过 VNC 访问的医疗监护仪设备。

## 许可证

MIT
