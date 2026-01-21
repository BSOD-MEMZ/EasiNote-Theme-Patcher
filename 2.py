import builtins
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import py7zr
import pygame
import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QPainter,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QScroller,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    AvatarWidget,
    BodyLabel,
    CaptionLabel,
    CardWidget,
    CheckBox,
    ComboBox,
    CommandBar,
    Dialog,
    ExpandGroupSettingCard,
    FlowLayout,
    FluentFontIconBase,
    FluentWindow,
    HyperlinkButton,
    InfoBar,
    LineEdit,
    MessageBox,
    MessageBoxBase,
    PillPushButton,
    PrimaryPushButton,
    PrimaryPushSettingCard,
    PrimaryToolButton,
    PushButton,
    QConfig,
    RadioButton,
    SmoothScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    TeachingTip,
    TextEdit,
    Theme,
    ThemeColor,
    TitleLabel,
    TreeView,
    setTheme,
    setThemeColor,
)

# 全局变量
newest_path = "C:/Program Files (x86)/Seewo/EasiNote5/"
get_correct_path = False
setting_data = {}
gotoeditdirectly = True  # 记录用户tm是怎么来EditPage的，直接点进去还是打开了文件，如果打开文件大抵是要解压到临时目录然后将newestpath设置为那个临时目录，但是万一主题文件不全怎么办？
isedited = False  # edit的过去式是这个吗（？


if not hasattr(builtins, "sound"):
    builtins.sound = True


_sfx_player = None
_sfx_output = None


class SimpleAudioPlayer:
    def play(self, path: str):
        if not os.path.exists(path):
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

    def stop(self):
        pygame.mixer.music.stop()

    def pause(self):
        pygame.mixer.music.pause()

    def resume(self):
        pygame.mixer.music.unpause()

    def is_playing(self):
        return pygame.mixer.music.get_busy()


_sfx_player = SimpleAudioPlayer()


def _play_sfx(filename: str):
    if not getattr(builtins, "app_ready", False):
        return
    if not getattr(builtins, "sound", False):
        return

    path = os.path.abspath(os.path.join("Resource", "sounds", filename))
    _sfx_player.play(path)


def sfx_open():
    _play_sfx("click.wav")


def sfx_click():
    _play_sfx("click_buffered.wav")


def sfx_exit():
    _play_sfx("exit.wav")


class PhotoFontIcon(FluentFontIconBase):
    def path(self, theme=Theme.AUTO):
        global setting_data
        return setting_data["icon_font"]


class EasiNoteThemePatcherEngine(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent

    def ask_theme_file(self):
        global setting_data
        sfx_open()
        self.main_window.setWindowTitle("EasiNote Theme Patcher - 未保存")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择主题文件",
            "",
            "7z 压缩主题文件 (*.7z);;所有文件 (*)",
        )
        if file_path:
            if not setting_data["not_to_ask_patch"]:
                self.ask_patch_or_not(file_path)
            else:
                self.patch_theme(file_path)

    def ask_patch_or_not(self, file_path):
        global setting_data
        sfx_open()
        w = OpenCustomMessageBox(self.main_window)
        if w.exec():
            sfx_exit()
            if w.remember.isChecked():
                setting_data["not_to_ask_patch"] = True
            if w.patch.isChecked():
                self.patch_theme(file_path)
            else:
                self.extra_to_path(file_path)

    def extra_to_path(self, file_path):
        global setting_data
        global gotoeditdirectly
        global newest_path
        newest_path = "./Temp"
        shutil.rmtree("./Temp", ignore_errors=True)
        temp_dir = "./Temp"
        with py7zr.SevenZipFile(file_path, "r") as archive:
            archive.extractall(temp_dir)
        setting_data["edit_temp_before_close"] = True
        with open("setting.json", "w", encoding="utf-8") as f:
            json.dump(setting_data, f, ensure_ascii=False, indent=4)
        gotoeditdirectly = False
        self.main_window.setWindowTitle("EasiNote Theme Patcher - 编辑临时文件")

    def patch_theme(self):
        temp_dir = "./temp"
        global newest_path
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                src = os.path.join(root, f)

                # 计算相对路径
                rel_path = os.path.relpath(src, temp_dir)
                dst = os.path.join(newest_path, rel_path)

                # 创建必要目录
                os.makedirs(os.path.dirname(dst), exist_ok=True)

                # 覆盖
                shutil.copy2(src, dst)
                InfoBar.success("Patched", rel_path, parent=self)
        shutil.rmtree(temp_dir)
        InfoBar.success("补丁应用成功", "主题资源已成功覆盖", parent=self)


class AudioPlayerWidget(QWidget):
    """音频播放控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_player = SimpleAudioPlayer()
        self.is_playing = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 音频图标
        self.audio_icon = QLabel()
        self.audio_icon.setPixmap(QPixmap("Resource/elements/record--images.png"))
        self.audio_icon.setFixedSize(200, 200)
        pix = self.audio_icon.pixmap()
        if pix:
            self.audio_icon.setPixmap(
                pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self.audio_icon.setScaledContents(False)
        self.audio_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.audio_icon, alignment=Qt.AlignCenter)

        # 文件名显示
        self.file_name_label = CaptionLabel("未选择音频文件")
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.file_name_label.setWordWrap(True)  # 启用自动换行
        layout.addWidget(self.file_name_label)

        # 播放控制按钮
        button_layout = QHBoxLayout()
        self.play_button = PrimaryToolButton(PhotoFontIcon("\ue768"))
        self.play_button.setFixedSize(50, 50)
        self.play_button.clicked.connect(self.toggle_play)
        button_layout.addStretch()
        button_layout.addWidget(self.play_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def load_audio(self, file_path):
        """加载音频文件"""
        self.file_path = file_path
        self.file_name_label.setText(Path(file_path).name)
        self.play_button.setIcon(PhotoFontIcon("\ue768"))
        self.is_playing = False

    def toggle_play(self):
        if not hasattr(self, "file_path"):
            return

        if self.is_playing:
            self.media_player.pause()
            self.is_playing = False
            self.play_button.setIcon(PhotoFontIcon("\ue768"))
        else:
            self.media_player.play(self.file_path)
            self.is_playing = True
            self.play_button.setIcon(PhotoFontIcon("\ue769"))

    def stop(self):
        self.media_player.stop()
        self.is_playing = False
        self.play_button.setIcon(PhotoFontIcon("\ue768"))


class TextEditorWidget(QWidget):
    """文本编辑器控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.is_modified = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 文本编辑器
        self.text_edit = TextEdit()
        self.text_edit.setPlaceholderText("在此编辑文件内容...")
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)

    def load_file(self, file_path):
        """加载文件内容"""
        try:
            self.file_path = file_path
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                self.text_edit.setPlainText(content)
                self.is_modified = False
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(file_path, "r", encoding="gbk") as file:
                    content = file.read()
                    self.text_edit.setPlainText(content)
                    self.is_modified = False
            except Exception as e:
                raise Exception(f"无法读取文件: {str(e)}")
        except Exception as e:
            raise Exception(f"无法读取文件: {str(e)}")

    def save_file(self, file_path=None):
        """保存文件内容"""
        if file_path is None:
            file_path = self.file_path

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(self.text_edit.toPlainText())
            self.is_modified = False
            return True
        except Exception as e:
            return False, str(e)

    def on_text_changed(self):
        self.is_modified = True

    def get_content(self):
        """获取文本内容"""
        return self.text_edit.toPlainText()


class ThemeCard(CardWidget):
    """主题卡片控件"""

    def __init__(self, theme_name, theme_data, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.theme_data = theme_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.theme_name)
        layout.addWidget(title_label)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(200, 150)
        self.preview_label.setText("加载中...")
        layout.addWidget(self.preview_label)

        # 描述
        description_label = BodyLabel(self.theme_data.get("description", ""))
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # 标签
        tags_layout = FlowLayout()
        tags = self.theme_data.get("tags", [])
        for tag in tags:
            tag_button = PillPushButton(tag)
            tag_button.setEnabled(False)
            tags_layout.addWidget(tag_button)
        layout.addLayout(tags_layout)

        # 下载按钮和进度条
        self.download_button = PrimaryPushButton("下载主题")
        self.download_button.clicked.connect(self.download_theme)
        layout.addWidget(self.download_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 加载预览图
        self.load_preview_image()

    def load_preview_image(self):
        """加载预览图片"""
        preview_url = self.theme_data.get("preview", "")
        if preview_url:
            # 在实际应用中，这里应该异步加载图片
            # 这里简化为显示占位符
            self.preview_label.setText("预览图")

    def download_theme(self):
        """下载主题"""
        download_url = self.theme_data.get("link", "")
        if not download_url:
            InfoBar.error("下载失败", "无效的下载链接", parent=self, duration=2000)
            return

        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存主题文件", f"{self.theme_name}.7z", "压缩文件 (*.7z)"
        )

        if file_path:
            self.download_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 直接使用requests下载
            try:
                response = requests.get(download_url, stream=True)
                total_size = int(response.headers.get("content-length", 0))

                with open(file_path, "wb") as file:
                    downloaded_size = 0
                    for data in response.iter_content(chunk_size=8192):
                        file.write(data)
                        downloaded_size += len(data)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress_bar.setValue(progress)
                            # 处理事件，更新UI
                            QApplication.processEvents()

                self.download_button.setEnabled(True)
                self.progress_bar.setVisible(False)
                InfoBar.success("下载完成", "主题已保存", parent=self, duration=2000)
            except Exception as e:
                self.download_button.setEnabled(True)
                self.progress_bar.setVisible(False)
                InfoBar.error(
                    "下载失败", f"下载失败: {str(e)}", parent=self, duration=2000
                )


class StorePage(SmoothScrollArea):
    def __init__(self):
        super().__init__()
        self.loaded = False
        self.init_ui()

    def init_ui(self):
        self.setObjectName("StorePage")
        self.setStyleSheet("border: none; background-color: transparent;")

        # 创建滚动区域
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumSize(750, 480)
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.content_widget = QWidget(self)
        self.setWidget(self.content_widget)

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(40, 20, 40, 20)
        content_layout.setSpacing(32)

        # 标题区域
        title_label = TitleLabel("主题商店")
        content_layout.addWidget(title_label)

        subtitle_label = SubtitleLabel("下载其他用户制作的精美主题")
        content_layout.addWidget(subtitle_label)

        # 主题网格布局
        self.themes_container = QWidget()
        self.themes_layout = FlowLayout(self.themes_container)
        content_layout.addWidget(self.themes_container)

        content_layout.addStretch()

    def load_store_data(self):
        InfoBar.error(
            "当前功能无效",
            "我没做完，主题下不了，这些只是placeholder",
            parent=self,
            duration=5000,
        )
        """加载商店数据"""
        try:
            # 首先尝试从网络加载
            response = requests.get(
                "https://xxtsoft.top/support/ENTP/store.json", timeout=10
            )
            if response.status_code == 200:
                self.themes_data = response.json()
                InfoBar.success(
                    "加载成功", "已从服务器加载主题列表", parent=self, duration=2000
                )
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            print(f"网络加载失败: {e}，尝试本地文件")
            # 网络加载失败，使用本地文件
            try:
                local_path = Path("./store.json")
                if local_path.exists():
                    with open(local_path, "r", encoding="utf-8") as file:
                        self.themes_data = json.load(file)
                    InfoBar.warning(
                        "使用本地数据",
                        "网络不可用，使用本地主题列表",
                        parent=self,
                        duration=2000,
                    )
                else:
                    raise Exception("本地store.json文件不存在")
            except Exception as local_error:
                print(f"本地加载失败: {local_error}")
                InfoBar.error(
                    "加载失败", "无法加载主题列表", parent=self, duration=2000
                )
                return

        # 显示主题卡片
        self.display_themes()

    def display_themes(self):
        """显示主题卡片"""
        # 清空现有布局
        while self.themes_layout.count():
            child = self.themes_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 添加主题卡片
        for theme_name, theme_data in self.themes_data.items():
            theme_card = ThemeCard(theme_name, theme_data)
            theme_card.setFixedSize(300, 400)
            self.themes_layout.addWidget(theme_card)


class AboutPage(SmoothScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("AboutPage")
        self.setStyleSheet("border: none; background-color: transparent;")

        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumSize(750, 480)
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.content_widget = QWidget(self)
        self.setWidget(self.content_widget)

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(40, 20, 40, 20)
        content_layout.setSpacing(32)

        title_label = TitleLabel("关于")
        content_layout.addWidget(title_label)

        subtitle_label = SubtitleLabel(
            "EasiNote Theme Patcher - Makes EasiNote great again!"
        )
        content_layout.addWidget(subtitle_label)


class BannerWidget(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedHeight(400)

        self.banner_pix = QPixmap("./banner.png")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        title = TitleLabel("EasiNote Theme Patcher", self)
        layout.addWidget(title)
        subtitle = SubtitleLabel("为更离谱的互动教学而生！", self)
        layout.addWidget(subtitle)
        cardArea = QWidget(self)
        cardLayout = QHBoxLayout(cardArea)
        cardLayout.setContentsMargins(0, 40, 0, 0)
        cardLayout.setSpacing(12)
        cardLayout.setAlignment(Qt.AlignLeft)
        layout.addWidget(cardArea)
        self.addCard(
            cardLayout,
            "Resource/Stickers/start.png",
            "打开预设",
            "修改当前主题",
            onClick=EasiNoteThemePatcherEngine(self.main_window).ask_theme_file,
        )
        self.addCard(
            cardLayout,
            "Resource/Stickers/hijack.png",
            "劫持模式",
            "暴力劫持老师的课件并强制修改",
            onClick=lambda: (
                sfx_open(),
                InfoBar.info(
                    "TODO",
                    "此功能非常复杂，涉及Python watchdog监测文件，XML读取和临时文件夹替换，所以暂时未完成",
                    parent=self,
                ),
            ),
        )
        self.addCard(
            cardLayout,
            "Resource/Stickers/store.png",
            "主题商店",
            "免费下载适合当前场景的教学主题",
            onClick=self.go_store,
        )
        self.addCard(
            cardLayout,
            "Resource/Stickers/help.png",
            "帮助文档",
            "不会用就先看看",
            onClick=lambda: (
                sfx_open(),
                os.startfile("https://xxtsoft.top/articles/entp.html"),
            ),
        )

    def addCard(self, layout, icon, title, text, onClick=None):
        card = QWidget()
        card.setFixedSize(198, 210)
        card.setStyleSheet("""
            .QWidget {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 12px;
            }
            .QWidget:hover {
                background: rgba(255, 255, 255, 0.9);
            }
            QLabel {
                color: #333;
            }
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(20, 20, 20, 16)
        v.setSpacing(8)

        iconLabel = QLabel()
        pix = QPixmap(icon)
        iconLabel.setPixmap(
            pix.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        v.addWidget(iconLabel)

        titleLabel = QLabel(title)
        titleLabel.setStyleSheet("font-size: 16px; font-weight: 600;")
        v.addWidget(titleLabel)

        textLabel = QLabel(text)
        textLabel.setWordWrap(True)
        textLabel.setStyleSheet("font-size: 12px; color: #666;")
        v.addWidget(textLabel)

        layout.addWidget(card)
        if onClick:
            card.mouseReleaseEvent = lambda e: onClick()

    def go_store(self):
        self.main_window.switchTo(self.main_window.store_page)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        if not self.banner_pix.isNull():
            pix = self.banner_pix.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, pix)


class ProfilePage(SmoothScrollArea):
    # TODO: 做出真正的登录功能，我会尽力学SQL的，应该吧
    def __init__(self, main_window):
        super().__init__()
        global setting_data
        self.main_window = main_window
        self.init_ui()
        self.mainlayout.addStretch(1)
        self.mainlayout.setContentsMargins(40, 20, 40, 20)
        self.mainlayout.setSpacing(8)

    def init_ui(self):
        global setting_data
        self.setObjectName("ProfilePage")
        self.setStyleSheet("border: none; background-color: transparent;")

        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumSize(750, 480)
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.content_widget = QWidget(self)
        self.setWidget(self.content_widget)

        self.add_profile_card()
        if not setting_data["profile_banner"]:
            title_label = TitleLabel("设置")
            self.mainlayout.addWidget(title_label)
        self.avatar.clicked.connect(lambda: self.showdialog())
        self.add_path_buttons(self.mainlayout)
        self.add_editor_buttons(self.mainlayout)
        self.set_global_color(self.mainlayout)
        """self.pandora_boxxx(self.mainlayout)"""

    def add_profile_card(self):
        self.avatar = AvatarWidget("Resource/avatar.png", self)
        self.nameLabel = SubtitleLabel("未登录", self)
        self.profilelayout = QHBoxLayout()
        self.profileWidget = QWidget()
        self.profilelayout = QHBoxLayout(self.profileWidget)

        self.profilelayout.setContentsMargins(20, 20, 20, 20)
        self.profilelayout.setSpacing(12)  # 头像与标题之间的垂直间距
        self.profilelayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.profilelayout.addWidget(self.avatar)
        self.profilelayout.addWidget(self.nameLabel)
        self.mainlayout = QVBoxLayout(self.content_widget)
        self.mainlayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.content_widget.setLayout(self.mainlayout)
        self.mainlayout.addWidget(self.profileWidget)
        self.userlayout = QHBoxLayout()
        self.userlayout.setSpacing(12)
        self.userlayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.spacer = QSpacerItem(100, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.profilelayout.addItem(self.spacer)
        self.addCard(
            self.userlayout,
            "Resource/elements/money.png",
            "0",
            "萌力值",
            onClick=lambda: InfoBar.info(
                "TODO", "此功能尚未实现", parent=self, duration=2000
            ),
        )
        self.addCard(
            self.userlayout,
            "Resource/Stickers/status/none.png",
            "未设置",
            "状态",
            onClick=lambda: self.set_status(),
        )
        self.addCard(
            self.userlayout,
            "Resource/elements/Settings.png",
            "编辑",
            "配置文件",
            onClick=lambda: os.startfile("setting.json"),
        )
        self.profilelayout.addLayout(self.userlayout)
        if not setting_data.get("profile_banner", True):
            self.profileWidget.setVisible(False)

    def showdialog(self):
        sfx_open()
        w = LoginCustomMessageBox(self)
        if w.exec():
            sfx_exit()
            self.avatar.setPixmap(QPixmap("Resource/avatar.png"))
            self.nameLabel.setText(w.account_edit.text())
        else:
            sfx_exit()
            InfoBar.info(
                "不登录也没关系哦",
                "就算不登录，也可以使用程序的大部分功能",
                parent=self,
                duration=2000,
            )

    def add_some_setting(self):
        pass

    def set_status(self):
        # TODO: 设置用户状态
        pass

    def addCard(self, layout, icon, title, text, onClick=None):
        card = QWidget()
        card.setFixedSize(72, 72)
        card.setStyleSheet("""
            .QWidget {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(234, 234, 234, 1);
                border-radius: 8px;
            }
            .QWidget:hover {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(178, 178, 178, 1);
            }
            QLabel {
                color: #333;
            }
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(0)

        iconLabel = QLabel()
        pix = QPixmap(icon)
        iconLabel.setPixmap(
            pix.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        v.addWidget(iconLabel)

        titleLabel = QLabel(title)
        titleLabel.setStyleSheet("font-size: 14px; font-weight: 600;")
        v.addWidget(titleLabel)

        textLabel = QLabel(text)
        textLabel.setWordWrap(True)
        textLabel.setStyleSheet("font-size: 11px; color: #666;")
        v.addWidget(textLabel)

        layout.addWidget(card)
        if onClick:
            card.mouseReleaseEvent = lambda e: onClick()

    def add_path_buttons(self, layout):
        global setting_data
        card = ExpandGroupSettingCard(
            icon=PhotoFontIcon("\uec50"),
            title="希沃白板安装路径",
            content=r"希沃白板通常存在于 C:\Program Files (x86)\Seewo\EasiNote5 目录下，但这个文件夹下有多个子文件夹，希沃白板安装完新版后旧版不会删除，因此请选择数字大的那个文件夹",
        )
        find_btn = PrimaryPushButton("开始自动查找")
        find_btn.setFixedWidth(135)
        input_btn = PushButton("手动查找")
        input_btn.setFixedWidth(135)
        find_btn.clicked.connect(self.on_find_clicked)
        input_btn.clicked.connect(self.on_input_clicked)
        card.addGroup(
            icon=PhotoFontIcon("\ue721"),
            title="自动查找",
            content="智能比较和查找希沃白板的安装路径",
            widget=find_btn,
        )
        card.addGroup(
            icon=PhotoFontIcon("\ue70f"),
            title="手动查找",
            content="当前路径：" + setting_data["newest_path"],
            widget=input_btn,
        )
        layout.addWidget(card)
        # 卧槽我是真会写屎山，反正root_layout就是最底层的布局，然后里面套了两个布局，一个是path_layout放文字，一个是action_layout放按钮
        # 我的 GitHub Copilot 限额快用完了，你们有什么头绪吗？
        # 然后我就用QFW自带的SettingCard，我还真tm是个天才，我造你妈的轮子
        # 写个蛋的layout

    def add_editor_buttons(self, layout):
        global setting_data
        card = PrimaryPushSettingCard(
            icon=PhotoFontIcon("\ue91b"),
            title="图片编辑器路径",
            content="你喜欢使用什么图片编辑器呀？在这里输入编辑器路径",
            text="浏览",
        )
        card.clicked.connect(self.on_editor_clicked)
        layout.addWidget(card)

    def set_global_color(self, layout):
        global setting_data
        card = ExpandGroupSettingCard(
            icon=PhotoFontIcon("\ue771"), title="个性化", content="设置程序的外观和行为"
        )
        color_choicer = ComboBox()
        color_choicer.addItems(["浅色", "深色", "跟随系统"])
        if setting_data.get("global_theme") == "light":
            color_choicer.setCurrentIndex(0)
        elif setting_data.get("global_theme") == "dark":
            color_choicer.setCurrentIndex(1)
        else:
            color_choicer.setCurrentIndex(2)
        color_choicer.currentIndexChanged.connect(
            lambda index: self.on_color_changed(index)
        )
        color_picker = PrimaryPushButton("自定义主题色")
        font_choicer = ComboBox()
        font_choicer.addItems(["Segoe Fluent Icons", "Segoe MDL2 Assets"])
        if setting_data.get("icon_font") == "Resource/fonts/SEGMDL2.TTF":
            font_choicer.setCurrentIndex(1)
        font_choicer.currentIndexChanged.connect(
            lambda index: self.on_font_changed(index)
        )
        color_choicer.setFixedWidth(135)
        color_picker.setFixedWidth(135)
        font_choicer.setFixedWidth(135)
        if setting_data.get("allow_about"):
            aboutpage_switch = SwitchButton()
            aboutpage_switch.setChecked(bool(setting_data.get("allow_about", True)))
        else:
            aboutpage_switch = SwitchButton()
            aboutpage_switch.setChecked(bool(setting_data.get("allow_about", False)))
        if setting_data.get("enable_pjsk"):
            pjsk_switch = SwitchButton()
            pjsk_switch.setChecked(bool(setting_data.get("enable_pjsk", True)))
        else:
            pjsk_switch = SwitchButton()
            pjsk_switch.setChecked(bool(setting_data.get("enable_pjsk", False)))
        if setting_data.get("sfx_sound"):
            sfx_switch = SwitchButton()
            sfx_switch.setChecked(bool(setting_data.get("sfx_sound", True)))
        else:
            sfx_switch = SwitchButton()
            sfx_switch.setChecked(bool(setting_data.get("sfx_sound", False)))
        aboutpage_switch.checkedChanged.connect(
            lambda: self.on_about_changed(aboutpage_switch.isChecked)
        )
        pjsk_switch.checkedChanged.connect(
            lambda: self.on_pjsk_changed(pjsk_switch.isChecked)
        )
        sfx_switch.checkedChanged.connect(
            lambda: self.on_sfx_changed(sfx_switch.isChecked)
        )
        card.addGroup(
            icon=PhotoFontIcon("\ue706"),
            title="全局主题模式",
            content="在夜间使用深色模式可以防止被亮瞎哦~",
            widget=color_choicer,
        )
        card.addGroup(
            icon=PhotoFontIcon("\ue790"),
            title="主题色",
            content="你觉得什么颜色好看呢？",
            widget=color_picker,
        )
        card.addGroup(
            icon=PhotoFontIcon("\uf158"),
            title="图标字体",
            content="Segoe Fluent Icons 偏向 Win11 风格，Segoe MDL2 Assets 偏向 Win10 风格",
            widget=font_choicer,
        )
        card.addGroup(
            icon=PhotoFontIcon("\ue946"),
            title="在侧栏显示“关于”",
            content="若关闭此选项，不会在侧边栏上显示关于页面",
            widget=aboutpage_switch,
        )
        card.addGroup(
            icon=PhotoFontIcon("\uf4aa"),
            title="Project Sekai 贴纸",
            content="在班级等公共场合可关闭此选项以免社死",
            widget=pjsk_switch,
        )
        card.addGroup(
            icon=PhotoFontIcon("\ue767"),
            title="音效反馈",
            content="程序会在部分事件发生时播放音效",
            widget=sfx_switch,
        )
        layout.addWidget(card)

    def pandora_boxxx(self, layout):
        global setting_data
        card = ExpandGroupSettingCard(
            icon=PhotoFontIcon("\uf1333"),
            title="PANDORA BOXXX",
            content="一旦打开这个盒子，就再也没有回头路了！",
        )
        test_mail_input = LineEdit()
        test_mail_input.setPlaceholderText("e.g. example@outlook.com")
        test_mail_input.setFixedWidth(300)
        test_mail_input.textChanged.connect(
            lambda: self.verify_debug_account(test_mail_input.text())
        )
        card.addGroup(
            icon=PhotoFontIcon("\ue716"),
            title="输入测试邮箱",
            content="请输入测试邮箱账号。开发者不对使用调试选项造成的任何后果负责。",
            widget=test_mail_input,
        )

        layout.addWidget(card)

    def on_sfx_changed(self, checked):
        global setting_data
        if checked:
            setting_data["sfx_sound"] = True
            sfx_open()
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))
        else:
            setting_data["sfx_sound"] = False
            sfx_exit()
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))

    def on_pjsk_changed(self, checked):
        global setting_data
        if checked:
            setting_data["enable_pjsk"] = True
            sfx_open()
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))
        else:
            setting_data["enable_pjsk"] = False
            sfx_exit()
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))

    def on_about_changed(self, checked):
        global setting_data
        if checked:
            setting_data["allow_about"] = True
            sfx_open()
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))
        else:
            setting_data["allow_about"] = False
            sfx_exit()
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))

    def verify_debug_account(self, mail):
        global setting_data
        if mail == "sorutokawaii@xxtsoft.top" or mail == "iwanttofxxk@0xabcd.dev":
            InfoBar.success("ReMaster Lv.15 Unlocked!", "下次启动应用生效")
            setting_data["debug"] = True
            json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))

    def on_color_changed(self, index):
        sfx_open()
        global setting_data
        if index == 0:
            setTheme(Theme.LIGHT)
            setting_data["global_theme"] = "light"
        elif index == 1:
            setTheme(Theme.DARK)
            setting_data["global_theme"] = "dark"
        else:
            setTheme(Theme.AUTO)
            setting_data["global_theme"] = "system"
        json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))

    def on_font_changed(self, index):
        sfx_open()
        global setting_data
        if index == 0:
            setting_data["icon_font"] = "Resource/fonts/SEGOEICONS.TTF"
        else:
            setting_data["icon_font"] = "Resource/fonts/SEGMDL2.TTF"
        json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))

    def on_input_clicked(self):
        global newest_path
        global setting_data
        w = PathCustomMessageBox(self)
        if w.exec():
            newest_path = w.path_edit.text()
            setting_data["newest_path"] = newest_path
            json.dump(
                setting_data,
                open("setting.json", "w", encoding="utf-8"),
            )

    def on_editor_clicked(self):
        global setting_data
        sfx_open()
        temp = QFileDialog.getOpenFileName(
            self,
            "选择图片编辑器(っ´Ι`)っ",
            "",
            "可执行文件 (*.exe);;所有文件 (*)",
        )[0]
        setting_data["editor_path"] = temp
        json.dump(
            setting_data,
            open("setting.json", "w", encoding="utf-8"),
        )

    def on_find_clicked(self):
        sfx_open()
        global newest_path, get_correct_path, setting_data
        print("Log: Trying to find EasiNote path automatically...")
        if os.path.exists("C:/Program Files (x86)/Seewo/EasiNote5/"):
            path = Path("C:/Program Files (x86)/Seewo/EasiNote5/")
            folders = [
                item.name
                for item in path.iterdir()
                if item.is_dir() and item.name.startswith("EasiNote5_")
            ]
            try:
                newest_folder = sorted(folders)[-1]
                newest_path = str(path / newest_folder)
                if self is not None:
                    InfoBar.success(
                        "查找成功",
                        "成功找到希沃白板安装路径，如果我没猜错的话应该是"
                        + newest_path
                        + "，如果不是的话就只能手动输入了",
                        parent=self,
                        duration=2000,
                    )
                print("Log: Found EasiNote path automatically:", newest_path)
                setting_data["newest_path"] = newest_path
                json.dump(setting_data, open("setting.json", "w", encoding="utf-8"))
                get_correct_path = True
            except Exception as e:
                print("Log: Failed to find EasiNote path automatically:", e)
                if self is not None:
                    InfoBar.error(
                        "查找失败",
                        "我怀疑你装过希沃白板，但没卸干净",
                        parent=self,
                        duration=2000,
                    )
        else:
            if self is not None:
                InfoBar.error(
                    "查找失败",
                    "未能找到希沃白板安装路径，请手动输入",
                    parent=self,
                    duration=2000,
                )


"""
class PandoraPage(SmoothScrollArea):
    def __init__(self, main_window):
        super().__init__()
        global setting_data
        self.main_window = main_window
        self.init_ui()
        self.content_widget.addStretch(1)
        self.content_widget.setContentsMargins(40, 20, 40, 20)
        self.content_widget.setSpacing(8)

    def init_ui(self):
        global setting_data
        self.setObjectName("PandoraPage")
        self.setStyleSheet("border: none; background-color: transparent;")

        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumSize(750, 480)
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.content_widget = QWidget(self)
        self.setWidget(self.content_widget)

        title_label = TitleLabel("PANDORA BOXXX")
        self.titlelayout = QVBoxLayout()
        self.titlelayout.addWidget(title_label)
        subtitle = SubtitleLabel(
            "警告：这些内容仅供测试，开发者不对使用此页面能造成的任何后果负责"
        )
        self.titlelayout.addWidget(subtitle)
        # self.content_widget.addLayout(self.titlelayout)
"""


class LoginEngine(QWidget):
    """Fuck you SQLite3"""

    def __init__(self, parent=None):
        super().__init__(parent)
        """
        conn = sqlite3.connect("test.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, penis_length REAL, pussy_depth REAL)"  # What fxxk?
        )
        conn.commit()
        conn.close()
        """


class LoginCustomMessageBox(MessageBoxBase):
    """Custom message box"""

    def __init__(self, parent=None):
        sfx_open()
        super().__init__(parent)

        self.login_title = SubtitleLabel("登录到 xxtsoft 网络", self)
        self.login_subtitle = CaptionLabel(
            "你之所以觉得我可爱，是因为你已经喜欢上我了，笨蛋~"
        )
        self.account_edit = LineEdit(self)
        self.account_edit.setPlaceholderText("xxtsoft Passport 或 用户名")
        self.password_edit = LineEdit(self)
        self.password_edit.setPlaceholderText("请输入密码")
        self.get_passport_hyperlink = HyperlinkButton(
            "https://xxtsoft.top",
            "获取 xxtsoft Passport",
            self,
            PhotoFontIcon("\ue8a7"),
        )
        self.viewLayout.addWidget(self.login_title)
        self.viewLayout.addWidget(self.login_subtitle)
        self.viewLayout.addWidget(self.account_edit)
        self.viewLayout.addWidget(self.password_edit)
        self.viewLayout.addWidget(self.get_passport_hyperlink)
        self.yesButton.setText("登录")
        self.cancelButton.setText("取消")


class OpenCustomMessageBox(MessageBoxBase):
    """Custom message box"""

    def __init__(self, parent=None):
        sfx_open()
        super().__init__(parent)
        self.open_title = SubtitleLabel("已打开文件", self)
        self.open_subtitle = CaptionLabel(
            "下一步该做什么呢？若选择“仅解压”，程序将解压主题包到临时目录，可以在编辑页面编辑主题后重新保存；若选择“立即应用”，希沃白板将立即应用当前主题。"
        )
        self.extra_to_temp_only = RadioButton("仅解压")
        self.patch = RadioButton("立即应用")
        self.remember = CheckBox("记住我的选择，以后不再询问")
        self.viewLayout.addWidget(self.open_title)
        self.viewLayout.addWidget(self.open_subtitle)
        self.viewLayout.addWidget(self.extra_to_temp_only)
        self.viewLayout.addWidget(self.patch)
        self.viewLayout.addWidget(self.remember)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")


class PathCustomMessageBox(MessageBoxBase):
    """Custom message box"""

    def __init__(self, parent=None):
        sfx_open()
        super().__init__(parent)
        self.hint_title = SubtitleLabel("输入路径", self)
        self.hint_subtitle = CaptionLabel(
            r"我们需要包括版本号的完整路径，例如C:\Program Files (x86)\Seewo\EasiNote5\EasiNote5_5.2.4.9440"
        )

        self.path_edit = LineEdit(self)
        self.openpath_button = HyperlinkButton("", "选择文件夹")
        self.openpath_button.clicked.connect(
            lambda: (
                sfx_open(),
                self.path_edit.setText(
                    QFileDialog.getExistingDirectory(
                        self,
                        "选择文件夹",
                        "",
                        QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
                    )
                ),
            )
        )
        self.viewLayout.addWidget(self.hint_title)
        self.viewLayout.addWidget(self.hint_subtitle)
        self.viewLayout.addWidget(self.path_edit)
        self.viewLayout.addWidget(self.openpath_button)


class HomePage(SmoothScrollArea):
    global default_editor
    global modified
    modified = set()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        self.setObjectName("HomePage")
        self.setStyleSheet("border: none; background-color: transparent;")

        # 创建滚动区域
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumSize(750, 480)
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.content_widget = QWidget(self)
        self.setWidget(self.content_widget)

        # 外层布局（Banner 贴边）
        outer_layout = QVBoxLayout(self.content_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Banner 顶部占满
        banner = BannerWidget(self.main_window, self)
        outer_layout.addWidget(banner)

        # 内容区仍有原来的边距
        contentArea = QWidget(self)
        content_layout = QVBoxLayout(contentArea)
        content_layout.setContentsMargins(40, 20, 40, 20)
        content_layout.setSpacing(32)

        outer_layout.addWidget(contentArea)
        body_label = BodyLabel(
            "众所周知希沃白板的资源文件全部不加密存储，而是直接放在本地目录中，内置的课堂互动模板非常有限。通过本程序您可以下载xxtsoft.top提供的其他人制作的模板或编辑属于您的主题以修改大部分希沃白板内置组件的图片声音资源和行为，从而充分调动课堂积极性，让学生更乐于参加课堂活动。"
        )
        body_label.setWordWrap(True)  # 启用自动换行
        content_layout.addWidget(body_label)
        content_layout.addStretch()


class EditPage(SmoothScrollArea):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_file_path = None
        self.current_file_type = None
        self.audio_player = None
        self.text_editor = None
        self.icons = {}
        self.command_actions = {}
        self.load_icons()
        self.init_ui()

    def load_icons(self):
        global setting_data
        if setting_data["enable_pjsk"]:
            self.icons["error"] = QPixmap("./Resource/Stickers/error_icon.png")
            self.icons["info"] = QPixmap("./Resource/Stickers/info_icon.png")
            self.icons["folder"] = QPixmap("./Resource/Stickers/folder_icon.png")
        else:
            self.icons["error"] = PhotoFontIcon("\ue783")
            self.icons["info"] = PhotoFontIcon("\ue946")
            self.icons["folder"] = PhotoFontIcon("\ue838")

    def init_ui(self):
        self.setObjectName("EditPage")
        self.setStyleSheet("border: none; background-color: transparent;")
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumSize(750, 480)
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        # 创建内容容器
        self.content_widget = QWidget(self)
        self.setWidget(self.content_widget)
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 主布局
        main_layout = QVBoxLayout(self.content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 文件浏览器和预览区域
        self.add_file_browser_section(main_layout)
        global get_correct_path, newest_path, gotoeditdirectly
        if gotoeditdirectly:
            self.main_window.setWindowTitle("EasiNote Theme Patcher - 实时编辑模式")
            InfoBar.warning(
                "实时编辑模式",
                "正在直接修改希沃白板文件，修改后不能撤销，安全起见请先备份整个文件夹",
                parent=self,
                duration=2000,
            )
        if not get_correct_path:
            InfoBar.error(
                "路径未找到",
                "请先在主页配置希沃白板安装路径",
                parent=self,
                duration=2000,
            )

    def add_file_browser_section(self, layout):
        """添加文件浏览器和预览区域"""
        # 创建分割器，可以调整左右大小
        global setting_data
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 左侧文件树
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 文件树标题
        tree_title = SubtitleLabel("文件资源")
        left_layout.addWidget(tree_title)

        # 创建文件系统模型和树视图
        self.tree_view = TreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["名称", "描述", "路径"])
        self.tree_view.setModel(self.model)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.tree_view.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.tree_view.header().setSectionResizeMode(2, QHeaderView.Interactive)
        self.tree_view.setColumnWidth(0, 250)
        self.tree_view.setColumnWidth(1, 250)
        left_layout.addWidget(self.tree_view)
        self.load_file_data()
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        preview_title = SubtitleLabel("文件预览")
        right_layout.addWidget(preview_title)
        self.preview_card = CardWidget()
        preview_card_layout = QVBoxLayout(self.preview_card)
        preview_card_layout.setContentsMargins(20, 20, 20, 20)
        preview_card_layout.setSpacing(15)
        self.command_bar = CommandBar(parent=self)
        self.command_actions["save"] = Action(
            PhotoFontIcon("\ue74e"), "导出主题包（Ctrl+S）", shortcut="Ctrl+S"
        )
        # 保存各个动作的引用
        self.command_actions["export"] = Action(
            PhotoFontIcon("\ue78c"),
            "导出选中的文件（Ctrl+Shift+S）",
            shortcut="Ctrl+Shift+S",
        )
        self.command_actions["replace"] = Action(
            PhotoFontIcon("\ue8eb"), "替换文件（Ctrl+R）", shortcut="Ctrl+R"
        )
        self.command_actions["restore"] = Action(
            PhotoFontIcon("\ue7a7"), "恢复原始文件"
        )
        self.command_actions["edit"] = Action(PhotoFontIcon("\ue70f"), "编辑文件")
        self.command_actions["copy"] = Action(
            PhotoFontIcon("\ue8c8"), "复制文件 (Ctrl+C)", shortcut="Ctrl+C"
        )
        self.command_actions["open_folder"] = Action(
            PhotoFontIcon("\ue8da"), "打开文件所在目录"
        )
        self.command_actions["play"] = Action(PhotoFontIcon("\ue768"), "播放文件")
        self.command_actions["json"] = Action(PhotoFontIcon("\ue943"), "JSON模式")
        self.command_actions["info"] = Action(PhotoFontIcon("\ue946"), "文件信息")
        self.command_actions["run"] = Action(
            PhotoFontIcon("\ue709"), "调试 - 启动希沃白板（F5）", shortcut="F5"
        )
        self.command_actions["delete"] = Action(PhotoFontIcon("\ue74d"), "抛弃临时文件")

        self.command_bar.addAction(self.command_actions["save"])
        self.command_bar.addAction(self.command_actions["export"])
        self.command_bar.addAction(self.command_actions["replace"])
        self.command_bar.addAction(self.command_actions["restore"])
        self.command_bar.addAction(self.command_actions["edit"])
        self.command_bar.addSeparator()
        self.command_bar.addAction(self.command_actions["copy"])
        self.command_bar.addAction(self.command_actions["open_folder"])
        self.command_bar.addAction(self.command_actions["play"])
        self.command_bar.addAction(self.command_actions["json"])
        self.command_bar.addAction(self.command_actions["info"])
        self.command_bar.addSeparator()
        self.command_bar.addAction(self.command_actions["run"])
        self.command_bar.addAction(self.command_actions["delete"])

        self.disable_all_actions()
        if setting_data["edit_temp_before_close"]:
            self.command_actions["delete"].setEnabled(True)
        self.command_actions["run"].setEnabled(True)

        self.command_actions["save"].triggered.connect(self.on_save_project)
        self.command_actions["export"].triggered.connect(self.on_export_file)
        self.command_actions["replace"].triggered.connect(self.on_replace_file)
        self.command_actions["restore"].triggered.connect(self.on_restore_file)
        self.command_actions["edit"].triggered.connect(self.on_edit_file)
        self.command_actions["copy"].triggered.connect(self.on_copy_file)
        self.command_actions["open_folder"].triggered.connect(self.on_open_file_folder)
        self.command_actions["play"].triggered.connect(self.on_play_file)
        self.command_actions["json"].triggered.connect(self.on_json_mode)
        self.command_actions["info"].triggered.connect(self.on_file_info)
        self.command_actions["run"].triggered.connect(self.on_run_seewo)
        self.command_actions["delete"].triggered.connect(self.on_rm_temp)
        preview_card_layout.addWidget(self.command_bar)

        self.image_preview_frame = QWidget()
        self.image_preview_frame.setMinimumSize(400, 300)
        self.image_preview_frame.setStyleSheet("""
            QWidget#image_preview_frame {
                background-color: rgba(0, 0, 0, 0.03);
                border: 2px dashed rgba(0, 0, 0, 0.1);
                border-radius: 8px;
            }
        """)
        self.image_preview_frame.setObjectName("image_preview_frame")
        image_preview_layout = QVBoxLayout(self.image_preview_frame)
        image_preview_layout.setContentsMargins(20, 20, 20, 20)
        image_preview_layout.setSpacing(15)

        self.status_container = QWidget()
        status_container_layout = QVBoxLayout(self.status_container)
        status_container_layout.setContentsMargins(0, 0, 0, 0)
        status_container_layout.setSpacing(10)
        status_container_layout.setAlignment(Qt.AlignCenter)

        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignCenter)
        status_container_layout.addWidget(self.status_icon)

        self.status_text = QLabel("请选择文件进行预览")
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setStyleSheet("""
            QLabel {
                font-size: 14px;
            }
        """)
        status_container_layout.addWidget(self.status_text)

        image_preview_layout.addWidget(self.status_container)

        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setVisible(False)
        image_preview_layout.addWidget(self.image_preview)

        image_preview_layout.addStretch()
        preview_card_layout.addWidget(self.image_preview_frame)

        # 音频播放器区域（初始隐藏）
        self.audio_player_widget = AudioPlayerWidget()
        self.audio_player_widget.setVisible(False)
        preview_card_layout.addWidget(self.audio_player_widget)

        self.text_editor_widget = TextEditorWidget()
        self.text_editor_widget.setVisible(False)
        preview_card_layout.addWidget(self.text_editor_widget)

        right_layout.addWidget(self.preview_card)
        self.tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])

        layout.addWidget(splitter)

        self.show_info_message("请选择文件进行预览")
        self.tree_view.selectionModel().selectionChanged.connect(
            self.on_tree_selection_changed
        )

    def on_tree_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            return

        index = indexes[0].sibling(indexes[0].row(), 0)

        self.on_file_clicked(index)

    def load_file_data(self):
        """加载文件数据到TreeView"""
        try:
            with open("target_file.json", "r", encoding="utf-8") as file:
                data = json.load(file)
                for category, content in data.items():
                    category_item = QStandardItem(category)
                    category_item.setEditable(False)
                    description = content.get("description", "")
                    desc_item = QStandardItem(description)
                    desc_item.setEditable(False)
                    empty_item = QStandardItem("")
                    empty_item.setEditable(False)
                    files = content.get("files", [])
                    for file_info in files:
                        file_name = QStandardItem(file_info.get("name", ""))
                        file_name.setEditable(False)
                        file_desc = QStandardItem(file_info.get("description", ""))
                        file_desc.setEditable(False)
                        file_path = QStandardItem(file_info.get("path", ""))
                        file_path.setEditable(False)
                        category_item.appendRow([file_name, file_desc, file_path])
                    self.model.appendRow([category_item, desc_item, empty_item])
            self.tree_view.doubleClicked.connect(self.on_file_double_clicked)

        except Exception as e:
            print(f"读取文件时出错: {e}")
            error_item = QStandardItem("打开失败Σ(っ °Д °;)っ")
            error_item.setEditable(False)
            desc_item = QStandardItem("请检查target_file.json文件")
            desc_item.setEditable(False)
            self.model.appendRow([error_item, desc_item, QStandardItem()])

    def on_file_clicked(self, index):
        """当文件被点击时预览文件"""
        sfx_click()
        # 检查是否选择了文件夹（有子项的节点）
        item = self.model.itemFromIndex(index.sibling(index.row(), 0))
        if item and item.hasChildren():
            self.show_folder_message("请展开文件夹以查看文件")
            self.disable_all_actions()
            return

        # 从模型的第3列获取路径（列索引2）
        path_index = index.sibling(index.row(), 2)
        path_item = self.model.itemFromIndex(path_index)
        file_path = path_item.text() if path_item is not None else ""

        if not file_path:
            self.show_info_message("请选择具体文件以预览")
            self.disable_all_actions()
            return

        global newest_path
        full_path = Path(file_path)
        if not full_path.exists():
            full_path = Path(newest_path) / file_path

        if not full_path.exists():
            self.show_error_message(f"文件不存在: {str(full_path)}")
            self.disable_all_actions()
            self.command_actions["delete"].setEnabled(True)
            self.command_actions["run"].setEnabled(True)
            self.command_actions["replace"].setEnabled(True)
            self.command_actions["save"].setEnabled(True)
            return

        # 更新当前文件路径和类型
        self.current_file_path = str(full_path)

        # 根据文件类型进行预览
        file_extension = full_path.suffix.lower()

        # 图片文件
        image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".ico", ".svg"]
        # 音频文件
        audio_extensions = [".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma"]
        # 文本文件
        text_extensions = [
            ".txt",
            ".ini",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".html",
            ".css",
            ".js",
            ".py",
            ".md",
        ]
        self.command_actions["open_folder"].setEnabled(True)
        if file_extension in image_extensions:
            temp = QPixmap(full_path)

            self.main_window.setWindowTitle(
                str(file_path) + " - " + str(temp.width()) + "x" + str(temp.height())
            )
            self.current_file_type = "image"
            self.preview_image(str(full_path))
            self.enable_file_actions()
            self.command_actions["play"].setEnabled(False)
            self.command_actions["edit"].setEnabled(True)
        elif file_extension in audio_extensions:
            self.main_window.setWindowTitle(str(file_path))
            self.current_file_type = "audio"
            self.preview_audio(str(full_path))
            self.enable_file_actions()
            self.command_actions["play"].setEnabled(True)
            self.command_actions["edit"].setEnabled(False)
        elif file_extension in text_extensions:
            self.main_window.setWindowTitle(str(file_path))
            self.current_file_type = "text"
            self.preview_text(str(full_path))
            self.enable_file_actions()
            self.command_actions["play"].setEnabled(False)
            self.command_actions["edit"].setEnabled(False)
        else:
            self.current_file_type = "other"
            self.main_window.setWindowTitle(str(file_path))
            self.show_info_message(f"不支持预览的文件类型: {file_extension}")
            self.enable_file_actions()
            self.command_actions["play"].setEnabled(False)
            self.command_actions["edit"].setEnabled(False)

    def show_error_message(self, message):
        """显示错误消息和图标"""
        self.show_status_message(message, "error")

    def show_info_message(self, message):
        """显示信息消息和图标"""
        self.show_status_message(message, "info")

    def show_folder_message(self, message):
        """显示文件夹消息和图标"""
        self.show_status_message(message, "folder")

    def show_status_message(self, message, icon_type):
        """显示状态消息和图标"""
        # 显示图片预览框，隐藏其他预览组件
        self.image_preview_frame.setVisible(True)
        self.audio_player_widget.setVisible(False)
        self.text_editor_widget.setVisible(False)

        # 隐藏图片预览，显示状态容器
        self.image_preview.setVisible(False)
        self.status_container.setVisible(True)

        icon = self.icons[icon_type]

        if isinstance(icon, QPixmap):
            pix = icon.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # PhotoFontIcon → QIcon → QPixmap
            pix = icon.icon().pixmap(96, 96)

        self.status_icon.setPixmap(pix)
        self.status_icon.setVisible(True)
        self.status_text.setText(message)
        self.status_text.setVisible(True)

    def disable_all_actions(self):
        """禁用所有命令按钮"""
        for action in self.command_actions.values():
            action.setEnabled(False)

    def enable_file_actions(self):
        """启用文件相关命令按钮"""
        for key, action in self.command_actions.items():
            action.setEnabled(True)

    def on_file_double_clicked(self, index):
        """当文件被双击时"""
        # 以第0列项判断是否为目录（有子项）
        item = self.model.itemFromIndex(index.sibling(index.row(), 0))
        if item is not None and item.hasChildren():
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)
            return
        self.on_file_info()

    def create_theme_7z(self):
        # TODO: 弹出对话框让用户输入Name，Author，Description，Tags等元数据

        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存主题包", "", "7z 压缩包 (*.7z)"
        )
        with py7zr.SevenZipFile(output_path, "w") as archive:
            for temp in modified:
                archive.write(temp, os.path.relpath(temp, newest_path))

    def preview_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.status_container.setVisible(False)
                self.image_preview.setVisible(True)
                scaled_pixmap = pixmap.scaled(
                    self.image_preview_frame.width() - 40,
                    self.image_preview_frame.height() - 40,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.image_preview.setPixmap(scaled_pixmap)
                self.image_preview_frame.setVisible(True)
                self.audio_player_widget.setVisible(False)
                self.text_editor_widget.setVisible(False)
            else:
                self.show_error_message("无法加载图片")
        except Exception as e:
            self.show_error_message(f"预览错误: {str(e)}")

    def preview_audio(self, audio_path):
        try:
            self.audio_player_widget.load_audio(audio_path)
            self.image_preview_frame.setVisible(False)
            self.text_editor_widget.setVisible(False)
            self.audio_player_widget.setVisible(True)
        except Exception as e:
            self.show_error_message(f"加载音频错误: {str(e)}")

    def preview_text(self, text_path):
        """预览文本文件"""
        try:
            self.text_editor_widget.load_file(text_path)
            self.image_preview_frame.setVisible(False)
            self.audio_player_widget.setVisible(False)
            self.text_editor_widget.setVisible(True)
        except Exception as e:
            self.show_error_message(f"加载文本文件错误: {str(e)}")

    def on_save_project(self):
        sfx_open()
        if setting_data["first_run"]:
            InfoBar.warning(
                "生成主题包",
                "跟其它软件不同，无论是实时编辑还是编辑主题包，所有更改立即生效，无需保存。此选项用于需要打包主题包以共享",
                parent=self,
                duration=2000,
            )
        self.create_theme_7z()
        InfoBar.success(
            "保存成功",
            "当前项目已保存",
            parent=self,
            duration=2000,
        )

    def on_export_file(self, checked=False):
        sfx_open()
        if not self.current_file_path:
            return

        global setting_data

        default_name = Path(self.current_file_path).name
        last_dir = setting_data.get("last_export_dir")
        if not last_dir:
            last_dir = str(Path(self.current_file_path).parent)

        initial = str(Path(last_dir) / default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文件",
            initial,  # 目录 + 默认文件名
            "所有文件 (*)",
        )
        if not file_path:
            return

        try:
            shutil.copy2(self.current_file_path, file_path)

            setting_data["last_export_dir"] = str(Path(file_path).parent)
            with open("setting.json", "w", encoding="utf-8") as f:
                json.dump(setting_data, f, ensure_ascii=False, indent=4)

            InfoBar.success(
                "导出成功", f"文件已导出到: {file_path}", parent=self, duration=2000
            )
        except Exception as e:
            InfoBar.error(
                "导出失败", f"导出文件时出错: {e}", parent=self, duration=2000
            )

    def on_replace_file(self):
        """替换文件操作"""
        if not self.current_file_path:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择替换文件", "", "所有文件 (*)"
        )

        if file_path:
            try:
                shutil.copy2(file_path, self.current_file_path)
                modified.add(self.current_file_path)
                self.command_actions["save"].setEnabled(True)
                InfoBar.success(
                    "替换成功",
                    f"文件已替换: {Path(self.current_file_path).name}",
                    parent=self,
                    duration=2000,
                )
                # 重新加载预览
                self.on_file_clicked(self.tree_view.currentIndex())
            except Exception as e:
                InfoBar.error(
                    "替换失败",
                    f"替换文件时出错: {str(e)}",
                    parent=self,
                    duration=2000,
                )

    def on_restore_file(self):
        sfx_open()
        # TODO: 实现恢复原始文件功能
        InfoBar.warning(
            "没有备份文件",
            "请手动备份文件",
            parent=self,
            duration=2000,
        )

    def on_open_file_folder(self):
        sfx_open()
        """打开文件所在目录操作"""
        if self.current_file_path:
            folder_path = os.path.dirname(self.current_file_path)
            os.startfile(folder_path)

    def on_edit_file(self):
        sfx_open()
        global default_editor, setting_data
        default_editor = setting_data["editor_path"]
        subprocess.Popen([default_editor, self.current_file_path])

    def on_copy_file(self):
        sfx_open()
        """复制文件操作"""
        if not self.current_file_path:
            return

        try:
            clipboard = QGuiApplication.clipboard()

            if self.current_file_type == "text":
                # 对于文本文件，复制文本内容
                content = self.text_editor_widget.get_content()
                clipboard.setText(content)
                InfoBar.success(
                    "复制成功",
                    "文本内容已复制到剪贴板",
                    parent=self,
                    duration=1500,
                )
            elif self.current_file_type == "image":
                # 对于图片文件，将图片复制到剪贴板
                image = QPixmap(self.current_file_path)
                if not image.isNull():
                    clipboard.setPixmap(image)
                    InfoBar.success(
                        "复制成功",
                        "图片已复制到剪贴板",
                        parent=self,
                        duration=1500,
                    )
                else:
                    InfoBar.error(
                        "复制失败",
                        "无法加载图片",
                        parent=self,
                        duration=2000,
                    )
            else:
                # 对于其他文件，复制文件路径
                clipboard.setText(self.current_file_path)
                InfoBar.success(
                    "复制成功",
                    "文件路径已复制到剪贴板",
                    parent=self,
                    duration=1500,
                )
        except Exception as e:
            InfoBar.error(
                "复制失败",
                f"复制时出错: {str(e)}",
                parent=self,
                duration=2000,
            )

    def on_play_file(self):
        """播放文件操作"""
        if self.current_file_type == "audio" and self.current_file_path:
            self.audio_player_widget.toggle_play()

    def on_json_mode(self):
        sfx_open()
        """JSON模式操作"""
        if (
            self.current_file_type == "text"
            and isinstance(self.current_file_path, str)
            and self.current_file_path.lower().endswith(".json")
        ):
            try:
                # 尝试格式化JSON
                content = self.text_editor_widget.get_content()
                parsed = json.loads(content)
                formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
                self.text_editor_widget.text_edit.setPlainText(formatted)
                InfoBar.success(
                    "JSON格式化",
                    "JSON已格式化",
                    parent=self,
                    duration=1500,
                )
            except Exception as e:
                InfoBar.error(
                    "JSON格式化失败",
                    f"不是有效的JSON格式: {str(e)}",
                    parent=self,
                    duration=2000,
                )
        else:
            InfoBar.warning(
                "JSON模式",
                "此功能仅适用于JSON文件",
                parent=self,
                duration=1500,
            )

    def on_file_info(self):
        sfx_open()
        """文件信息操作"""
        if not self.current_file_path:
            return

        self.show_file_details(self.current_file_path)

    def on_run_seewo(self):
        global setting_data
        sfx_exit()
        """启动希沃白板操作"""
        global newest_path
        if newest_path and Path(newest_path).exists():
            seewo_exe = Path(newest_path) / "../swenlauncher/swenlauncher.exe"
            if seewo_exe.exists():
                try:
                    os.startfile(str(seewo_exe))
                    if setting_data["first_run"]:
                        TeachingTip.create(
                            target=self.command_actions["run"],
                            title="启动成功",
                            content="希沃白板已启动，此外希沃白板自带热重载，因此不必关闭白板即可看到修改效果",
                            parent=self,
                            duration=2000,
                            isClosable=True,
                        )

                        setting_data["first_run"] = False
                        with open(
                            "setting.json", "w", encoding="utf-8"
                        ) as setting_file:
                            json.dump(setting_data, setting_file, indent=4)
                except Exception as e:
                    InfoBar.error(
                        "启动失败",
                        f"启动希沃白板时出错: {str(e)}",
                        parent=self,
                        duration=2000,
                    )
            else:
                InfoBar.error(
                    "启动失败",
                    "找不到swenlauncher文件",
                    parent=self,
                    duration=2000,
                )
        else:
            InfoBar.error(
                "启动失败",
                "希沃白板路径未配置或不存在",
                parent=self,
                duration=2000,
            )

    def on_rm_temp(self):
        sfx_open()
        global setting_data
        global newest_path
        global gotoeditdirectly
        w = Dialog(
            "丢弃临时文件", "临时目录将被永久删除，问一下你项目导出了吗？", window
        )
        w.yesButton.setText("我存了，你删吧")
        w.cancelButton.setText("卧槽等我一下")
        if w.exec():
            setting_data["edit_temp_before_close"] = False
            newest_path = setting_data["newest_path"]
            shutil.rmtree("./Temp", ignore_errors=True)
            with open("setting.json", "w", encoding="utf-8") as f:
                json.dump(setting_data, f, ensure_ascii=False, indent=4)
            gotoeditdirectly = True
            self.main_window.setWindowTitle("EasiNote Theme Patcher - 实时编辑模式")
        else:
            sfx_exit()
            InfoBar.info(
                title="取消",
                content="快点存一下呐，别让我催你",
                duration=1000,
                parent=self,
            )

    def show_file_details(self, file_path):
        """显示文件详细信息"""
        file_info = Path(file_path)
        if file_info.exists():
            size = file_info.stat().st_size
            size_kb = size / 1024
            size_mb = size_kb / 1024
            modified = file_info.stat().st_mtime

            # 格式化文件大小
            if size_mb >= 1:
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = f"{size_kb:.2f} KB"

            MessageBox(
                "文件信息",
                f"文件名: {file_info.name}\n"
                f"大小: {size} 字节 ({size_str})\n"
                f"路径: {file_path}\n"
                f"类型: {self.current_file_type}",
                self,
            ).exec()


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        global setting_data
        self.config = QConfig
        self.home_page = HomePage(self)
        self.edit_page = EditPage(self)
        self.store_page = StorePage()
        self.profile_page = ProfilePage(self)
        if setting_data["allow_about"]:
            self.about_page = AboutPage(self)
        """
        if setting_data["debug"]:
            self.pandora_page = PandoraPage(self)
        """
        self.initNavigation()
        self.initWindow()

    def switchTo(self, interface):
        sfx_click()  # ← 切换页面音效
        if isinstance(interface, StorePage) and not interface.loaded:
            interface.load_store_data()
            interface.loaded = True
        super().switchTo(interface)

    def initNavigation(self):
        global setting_data
        self.addSubInterface(self.home_page, PhotoFontIcon("\ue80f"), "主页")
        self.addSubInterface(self.edit_page, PhotoFontIcon("\ue70f"), "创作")
        self.addSubInterface(self.store_page, PhotoFontIcon("\ue719"), "商店")
        self.addSubInterface(self.profile_page, PhotoFontIcon("\ue713"), "设置")
        """
        if setting_data["debug"]:
            self.addSubInterface(
                self.pandora_page, PhotoFontIcon("\uf158"), "PANDORA BOXXX"
            )
        """
        if setting_data["allow_about"]:
            self.addSubInterface(self.about_page, PhotoFontIcon("\ue946"), "关于")
        self.navigationInterface.setExpandWidth(180)

    def initWindow(self):
        self.resize(1200, 700)  # 增加窗口大小以适应新布局
        # 仅在主窗口尚未设置标题时才设置默认标题，以免覆盖来自子页面（如实时编辑模式）的自定义标题
        if not self.windowTitle():
            self.setWindowTitle("EasiNote Theme Patcher")
        self.setWindowIcon(QIcon("Resource/icon.ico"))


if __name__ == "__main__":
    builtins.DEBUG = {"sound": True, "app_ready": False}

    pygame.mixer.init()
    """
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    """
    try:
        setting_data = json.load(open("setting.json", "r", encoding="utf-8"))
    except Exception as e:
        print("setting.json not found!" + str(e))
        sys.exit(0)

    if not setting_data.get("newest_path"):
        ProfilePage.on_find_clicked(None)

    else:
        newest_path = setting_data.get("newest_path")
        get_correct_path = True
    app = QApplication(sys.argv)
    if setting_data["edit_temp_before_close"]:
        gotoeditdirectly = False
        newest_path = "./Temp"
    window = MainWindow()

    setThemeColor(ThemeColor.PRIMARY.color())
    setTheme(Theme.AUTO)
    window.show()
    if setting_data["edit_temp_before_close"]:
        window.switchTo(window.edit_page)
        window.setWindowTitle("欢迎回来 - 从上次离开的地方继续编辑")
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    builtins.app_ready = True
    if setting_data["sfx_sound"]:
        builtins.sound = True

    app.exec()
