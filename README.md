# EasiNote Theme Patcher

一个用于编辑与打包希沃白板主题资源的桌面工具（PySide2 + Fluent Widgets）。

## 环境

- Python 3.8（面向 Win7 兼容）
- 依赖见 `pyproject.toml`

## 快速开始

1. 创建并激活虚拟环境

```powershell
uv venv .venv --python 3.8
. .venv\Scripts\Activate.ps1
```

2. 安装依赖

```powershell
uv pip install --python .venv PySide2 PySide2-Fluent-Widgets pygame py7zr==0.9.0 requests
```

3. 运行

```powershell
python 2.py
```

## 说明

- `setting.json` 为运行时配置文件
- 主题包格式为 `.7z`
