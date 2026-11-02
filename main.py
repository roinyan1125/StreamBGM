# -*- coding: utf-8 -*-
import json, os, random, sys
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QLineEdit,
    QSlider, QComboBox, QMessageBox, QInputDialog, QFrame, QAbstractItemView)

DATA = Path(os.environ.get('APPDATA') or Path.home()) / 'StreamBGM' / 'library.json'
EXT = {'.mp3', '.mp4', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'}

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('StreamBGM | 配信BGMマネージャー')
        self.resize(1050, 700)
        self.playlists = {'メイン': []}
        self.active = 'メイン'
        self.current_path = None
        self.shuffle = False
        self._seeking = False
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(.6)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(self.playback_error)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.setup_ui()
        self.load_library()
        self.refresh_lists()
        self.refresh_tracks()

    def button(self, text, fn, primary=False):
        b = QPushButton(text)
        b.clicked.connect(fn)
        if primary: b.setObjectName('primary')
        return b

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(14)
        header = QHBoxLayout()
        heading = QLabel('♫  StreamBGM')
        heading.setObjectName('heading')
        header.addWidget(heading)
        header.addStretch()
        header.addWidget(QLabel('配信向け BGM・動画ファイル管理'))
        outer.addLayout(header)
        tools = QHBoxLayout()
        for label, fn in [('＋ ファイル追加', self.add_files), ('＋ フォルダ追加', self.add_folder), ('削除', self.remove_tracks), ('＋ プレイリスト', self.add_playlist), ('リスト削除', self.remove_playlist)]:
            tools.addWidget(self.button(label, fn, label.startswith('＋ ファイル')))
        outer.addLayout(tools)
        body = QHBoxLayout()
        self.listbox = QListWidget()
        self.listbox.setMaximumWidth(210)
        self.listbox.currentTextChanged.connect(self.change_playlist)
        body.addWidget(self.listbox, 1)
        right = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('曲名やファイル名で検索...')
        self.search.textChanged.connect(self.refresh_tracks)
        right.addWidget(self.search)
        self.tracks = QListWidget()
        self.tracks.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tracks.itemDoubleClicked.connect(self.play_selected)
        right.addWidget(self.tracks)
        body.addLayout(right, 4)
        outer.addLayout(body, 1)
        self.now = QLabel('再生する曲を選択してください')
        self.now.setObjectName('now')
        outer.addWidget(self.now)
        seek_row = QHBoxLayout()
        self.elapsed = QLabel('00:00')
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self.seek.sliderReleased.connect(self.finish_seek)
        self.total = QLabel('00:00')
        seek_row.addWidget(self.elapsed)
        seek_row.addWidget(self.seek, 1)
        seek_row.addWidget(self.total)
        outer.addLayout(seek_row)
        controls = QHBoxLayout()
        controls.addWidget(self.button('⏮ 前へ', self.previous))
        self.play_btn = self.button('▶ 再生', self.toggle, True)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.button('⏭ 次へ', self.next_track))
        controls.addWidget(QLabel('ループ'))
        self.repeat = QComboBox()
        self.repeat.addItems(['全曲', '1曲', 'なし'])
        self.repeat.currentTextChanged.connect(lambda _: self.save_library())
        controls.addWidget(self.repeat)
        self.shuffle_btn = self.button('シャッフル OFF', self.toggle_shuffle)
        controls.addWidget(self.shuffle_btn)
        controls.addStretch()
        controls.addWidget(QLabel('音量'))
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setFixedWidth(125)
        self.volume.setRange(0, 100)
        self.volume.setValue(60)
        self.volume.valueChanged.connect(self.set_volume)
        controls.addWidget(self.volume)
        self.vol_label = QLabel('60%')
        controls.addWidget(self.vol_label)
        outer.addLayout(controls)
        self.statusBar().showMessage('MP3 / MP4 / WAV / M4A などに対応（形式はWindowsのコーデックに依存）')
        self.setStyleSheet('''
            QWidget { background: #101a2a; color: #e9f4ff; font-family: "Yu Gothic UI", "Meiryo", sans-serif; font-size: 13px; }
            QLabel#heading { font-size: 27px; font-weight: bold; color: #a8d5ff; }
            QLabel#now { font-size: 16px; font-weight: bold; color: #a8d5ff; padding: 8px 0; }
            QPushButton { background: #243c57; border: 1px solid #3a5675; border-radius: 9px; padding: 10px 13px; }
            QPushButton:hover { background: #365879; }
            QPushButton#primary { background: #80c1ff; color: #102035; font-weight: bold; }
            QPushButton#primary:hover { background: #a8d5ff; }
            QListWidget, QLineEdit, QComboBox { background: #18283d; border: 1px solid #39516c; border-radius: 9px; padding: 8px; }
            QListWidget::item { padding: 9px; border-radius: 5px; }
            QListWidget::item:selected { background: #3675a6; }
            QSlider::groove:horizontal { height: 6px; background: #3b526e; border-radius: 3px; }
            QSlider::handle:horizontal { background: #9ad8fe; width: 15px; margin: -5px 0; border-radius: 7px; }
            QStatusBar { color: #a8bed2; }
        ''')

    def load_library(self):
        try:
            if DATA.exists():
                data = json.loads(DATA.read_text(encoding='utf-8'))
                raw = data.get('playlists', {})
                if isinstance(raw, dict):
                    self.playlists = {str(k): [p for p in v if isinstance(p, str)] for k,v in raw.items() if isinstance(v,list)} or {'メイン': []}
                self.active = data.get('active', next(iter(self.playlists)))
                if self.active not in self.playlists: self.active = next(iter(self.playlists))
                self.repeat.setCurrentText(data.get('repeat', '全曲'))
                self.shuffle = bool(data.get('shuffle', False))
                self.volume.setValue(max(0, min(100, int(data.get('volume', 60)))))
                self.shuffle_btn.setText('シャッフル ON' if self.shuffle else 'シャッフル OFF')
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.warning(self, '読み込みエラー', f'設定を読み込めませんでした。\n{e}')

    def save_library(self):
        try:
            DATA.parent.mkdir(parents=True, exist_ok=True)
            payload = {'playlists': self.playlists, 'active': self.active, 'repeat': self.repeat.currentText(), 'shuffle': self.shuffle, 'volume': self.volume.value()}
            tmp = DATA.with_suffix('.tmp')
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(DATA)
        except OSError as e:
            self.statusBar().showMessage(f'設定の保存に失敗しました: {e}', 8000)

    def refresh_lists(self):
        self.listbox.blockSignals(True)
        self.listbox.clear()
        self.listbox.addItems(self.playlists.keys())
        matches = self.listbox.findItems(self.active, Qt.MatchExactly)
        if matches: self.listbox.setCurrentItem(matches[0])
        self.listbox.blockSignals(False)

    def refresh_tracks(self):
        self.tracks.clear()
        term = self.search.text().casefold()
        for path in self.playlists.get(self.active, []):
            if term not in Path(path).name.casefold(): continue
            item = QListWidgetItem(('♫  ' if Path(path).exists() else '⚠  ') + Path(path).name)
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            self.tracks.addItem(item)

    def change_playlist(self, name):
        if name and name in self.playlists:
            self.active = name
            self.refresh_tracks()
            self.save_library()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, '音楽・動画ファイルを追加', '', 'メディア (*.mp3 *.mp4 *.wav *.m4a *.aac *.flac *.ogg *.wma);;すべてのファイル (*)')
        self.insert_paths(paths)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'フォルダを選択')
        if folder:
            paths = [str(p) for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower() in EXT]
            self.insert_paths(sorted(paths))

    def insert_paths(self, paths):
        dest = self.playlists[self.active]
        added = 0
        for path in paths:
            p = str(Path(path).resolve())
            if Path(p).suffix.lower() in EXT and p not in dest:
                dest.append(p)
                added += 1
        self.refresh_tracks()
        self.save_library()
        self.statusBar().showMessage(f'{added} 件のファイルを追加しました', 4000)

    def remove_tracks(self):
        selected = {i.data(Qt.UserRole) for i in self.tracks.selectedItems()}
        if selected:
            self.playlists[self.active] = [p for p in self.playlists[self.active] if p not in selected]
            self.refresh_tracks()
            self.save_library()

    def add_playlist(self):
        name, ok = QInputDialog.getText(self, 'プレイリストを追加', '名前')
        name = name.strip()
        if ok and name:
            if name in self.playlists:
                QMessageBox.information(self, '確認', '同じ名前のプレイリストがあります。')
                return
            self.playlists[name] = []
            self.active = name
            self.refresh_lists()
            self.refresh_tracks()
            self.save_library()

    def remove_playlist(self):
        if len(self.playlists) <= 1:
            QMessageBox.information(self, '確認', '最後のプレイリストは削除できません。')
            return
        if QMessageBox.question(self, '削除確認', f'「{self.active}」を削除しますか？\n元の音声ファイルは削除されません。') == QMessageBox.Yes:
            del self.playlists[self.active]
            self.active = next(iter(self.playlists))
            self.refresh_lists()
            self.refresh_tracks()
            self.save_library()

    def play_selected(self, item):
        self.play_path(item.data(Qt.UserRole))

    def play_path(self, path):
        if not Path(path).is_file():
            QMessageBox.warning(self, 'ファイルがありません', f'ファイルが見つかりません。\n{path}')
            return
        self.current_path = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.now.setText('再生中: ' + Path(path).name)
        self.play_btn.setText('⏸ 一時停止')

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_btn.setText('▶ 再生')
        elif self.current_path and self.player.source().isValid():
            self.player.play()
            self.play_btn.setText('⏸ 一時停止')
        elif self.tracks.count():
            self.play_selected(self.tracks.currentItem() or self.tracks.item(0))

    def step(self, direction, automatic=False):
        paths = self.playlists.get(self.active, [])
        valid = [p for p in paths if Path(p).is_file()]
        if not valid: return
        if self.shuffle:
            candidates = [p for p in valid if p != self.current_path] or valid
            self.play_path(random.choice(candidates))
            return
        if self.current_path not in valid:
            self.play_path(valid[0])
            return
        idx = valid.index(self.current_path) + direction
        if idx >= len(valid) or idx < 0:
            if automatic and self.repeat.currentText() == 'なし':
                self.player.stop()
                self.play_btn.setText('▶ 再生')
                self.now.setText('再生が終了しました')
                return
            idx %= len(valid)
        self.play_path(valid[idx])

    def next_track(self): self.step(1)
    def previous(self): self.step(-1)

    def media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.repeat.currentText() == '1曲':
                self.player.setPosition(0)
                self.player.play()
            else:
                self.step(1, automatic=True)

    def playback_error(self, error, message):
        if error != QMediaPlayer.NoError:
            self.play_btn.setText('▶ 再生')
            QMessageBox.warning(self, '再生エラー', f'この形式を再生できませんでした。\n{message}\n\nMP4はWindowsのコーデックによって対応が異なります。')

    def position_changed(self, ms):
        if not self._seeking: self.seek.setValue(ms)
        self.elapsed.setText(self.time_text(ms))

    def duration_changed(self, ms):
        self.seek.setRange(0, max(0, ms))
        self.total.setText(self.time_text(ms))

    @staticmethod
    def time_text(ms):
        s = max(0, ms // 1000)
        return f'{s // 60:02d}:{s % 60:02d}'

    def finish_seek(self):
        self.player.setPosition(self.seek.value())
        self._seeking = False

    def set_volume(self, value):
        self.audio.setVolume(value / 100)
        self.vol_label.setText(f'{value}%')
        self.save_library()

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.shuffle_btn.setText('シャッフル ON' if self.shuffle else 'シャッフル OFF')
        self.save_library()

    def closeEvent(self, event):
        self.save_library()
        self.player.stop()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont('Yu Gothic UI', 10))
    window = Window()
    window.show()
    sys.exit(app.exec())
