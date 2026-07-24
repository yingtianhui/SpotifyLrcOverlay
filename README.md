# Spotify LRC Overlay

Windows 透明悬浮歌词软件，使用 Python + PySide6，自动检测 Spotify 桌面版和网页版当前播放歌曲，并从 LRCLIB 获取 LRC 歌词。

## 功能

- 自动检测 Spotify 桌面版和支持 Windows 媒体会话的浏览器 Spotify Web
- 根据歌曲名和歌手从 LRCLIB 获取同步 LRC 歌词
- 自动解析 LRC 时间轴
- 透明悬浮歌词窗，始终置顶
- 鼠标拖动改变位置
- 切歌自动刷新歌词
- 当前句 + 下一句双行显示
- 界面按钮调节歌词提前量，范围 800-2000ms
- MVC 结构
- 10Hz 歌词刷新
- 网络/检测错误自动重试
- 滚动日志文件

## 安装运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spotify_lrc_overlay
```

## 打包 exe

双击运行：

```text
build_release.bat
```

或在命令行运行：

```powershell
.\.venv\Scripts\Activate.ps1
python -m PyInstaller spotify_lrc_overlay.spec
```

最终生成一个单文件 exe：

```text
dist\SpotifyLrcOverlay.exe
```

把这个 `SpotifyLrcOverlay.exe` 发给别人即可，对方双击运行，不需要打开命令行，也不需要复制整个项目文件夹。

## 歌词同步调节

悬浮窗底部有三个控制按钮：

```text
-100   提前 xxxxms   重置   +100
```

- `+100`：歌词更早出现
- `-100`：歌词更晚出现
- `重置`：恢复默认 1500ms
- 可调范围：800-2000ms

也可以用环境变量设置启动默认值：

```powershell
$env:SPOTIFY_LRC_OFFSET_MS="1200"
python -m spotify_lrc_overlay
```

## 日志

日志位于：

```text
%LOCALAPPDATA%\SpotifyLrcOverlay\logs\app.log
```

如果歌词停住，查看日志中的 `Playback:` 行。`reported` 是 Windows/Spotify 报告的进度，`resolved` 是软件最终用于匹配歌词的进度，`lyric_position` 是加上提前量后的歌词匹配位置。

## 说明

主检测方案依赖 Windows Global System Media Transport Controls。Spotify 桌面版通常可直接识别；Spotify Web 需要浏览器把网页媒体暴露给 Windows 媒体会话。若系统未提供媒体会话，本程序会退回到窗口标题检测，但只能识别歌曲信息，无法获得精确播放进度。
