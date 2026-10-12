import os
import sys
import time
import subprocess
from datetime import datetime
from PySide6 import QtCore, QtGui, QtWidgets
import keyboard

try:
    from src.recorder import StarRecorder, QUALITY_PROFILES, FORMAT_SPECS
except ImportError:
    from recorder import StarRecorder, QUALITY_PROFILES, FORMAT_SPECS

class AudioMeter(QtWidgets.QProgressBar):
    def __init__(self, parent=None, color="#ff0055"):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setTextVisible(False)
        self.setFixedHeight(10)
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: #0d1017;
                border: 1px solid #1a2333;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f2fe, stop:0.55 #4facfe, stop:0.82 #f093fb, stop:1.0 {color});
                border-radius: 4px;
            }}
        """)

class StarScreamWindow(QtWidgets.QMainWindow):
    hotkey_signal = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.recorder = StarRecorder()
        self.output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "recordings"))
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.init_ui()
        self.setup_hotkeys()
        
        # Audio level & time update timer (every 40ms = 25Hz smooth VU meter)
        self.meter_timer = QtCore.QTimer(self)
        self.meter_timer.timeout.connect(self.update_live_meters)
        self.meter_timer.start(40)
        
    def init_ui(self):
        self.setWindowTitle("STAR SCREAM // PROFESSIONAL HIGH-PERFORMANCE RECORDER")
        self.resize(1140, 760)
        self.setMinimumSize(980, 680)
        
        # Load Branded Icon
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
        if not os.path.exists(icon_path):
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png"))
        if os.path.exists(icon_path):
            app_icon = QtGui.QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QtWidgets.QApplication.setWindowIcon(app_icon)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #07090e;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                background-color: #0e121a;
                border: 1px solid #1e2638;
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 16px;
                font-weight: 700;
                color: #94a3b8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #ff2a5f;
                font-size: 11px;
                letter-spacing: 1.5px;
            }
            QComboBox {
                background-color: #141924;
                border: 1px solid #28334a;
                border-radius: 6px;
                padding: 7px 12px;
                color: #f8fafc;
                font-weight: 600;
            }
            QComboBox:hover {
                border: 1px solid #ff2a5f;
            }
            QComboBox::drop-down {
                border: none;
                width: 26px;
            }
            QComboBox QAbstractItemView {
                background-color: #141924;
                selection-background-color: #ff2a5f;
                selection-color: #ffffff;
                color: #e2e8f0;
                border: 1px solid #28334a;
                outline: none;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1a2233;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2a5f, stop:1 #ff6584);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff2a5f;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #334155;
                background-color: #141924;
            }
            QCheckBox::indicator:checked {
                background-color: #ff2a5f;
                border: 1px solid #ff6584;
            }
            QListWidget {
                background-color: #0b0e15;
                border: 1px solid #1c2333;
                border-radius: 8px;
                padding: 6px;
                color: #cbd5e1;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #141a26;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background-color: #161d2b;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #ff2a5f;
                color: #ffffff;
                font-weight: bold;
            }
            QStatusBar {
                background-color: #07090e;
                color: #64748b;
                border-top: 1px solid #141924;
                font-size: 12px;
            }
        """)
        
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(16)
        
        # --- HEADER / BRANDING ---
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(14)
        
        # Logo Icon Graphic
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png"))
        if os.path.exists(icon_path):
            logo_lbl = QtWidgets.QLabel()
            pix = QtGui.QPixmap(icon_path).scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            header_layout.addWidget(logo_lbl)
        
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QtWidgets.QLabel("STAR SCREAM")
        app_title.setStyleSheet("font-size: 26px; font-weight: 900; letter-spacing: 2.5px; color: #ff2a5f;")
        subtitle = QtWidgets.QLabel("ULTRA FAST PC RECORDER // EASIER THAN OBS // HARDWARE ACCELERATED")
        subtitle.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1.2px; color: #64748b;")
        title_box.addWidget(app_title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        
        header_layout.addStretch()
        
        # Hardware Status Badges
        badge_box = QtWidgets.QHBoxLayout()
        badge_box.setSpacing(8)
        
        hotkey_tag = QtWidgets.QLabel("⌨ F9: REC | F10: PAUSE")
        hotkey_tag.setStyleSheet("""
            background-color: #161b26;
            border: 1px solid #28334a;
            color: #94a3b8;
            border-radius: 12px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 700;
        """)
        badge_box.addWidget(hotkey_tag)
        
        nvenc_badge = QtWidgets.QLabel("⚡ RTX 3050 NVENC ON")
        nvenc_badge.setStyleSheet("""
            background-color: #0d2b1d;
            border: 1px solid #059669;
            color: #10b981;
            border-radius: 12px;
            padding: 5px 14px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.8px;
        """)
        badge_box.addWidget(nvenc_badge)
        header_layout.addLayout(badge_box)
        
        main_layout.addLayout(header_layout)
        
        # --- CENTER SPLIT: CONFIGURATION PANELS & RECORDINGS VAULT ---
        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(18)
        
        # LEFT COLUMN: VIDEO, FORMAT, RESOLUTION, & AUDIO MIXER
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(14)
        
        # 1. VIDEO SOURCE, RESOLUTION & FORMAT GROUP
        video_group = QtWidgets.QGroupBox("1. VIDEO CANVAS, RESOLUTION & CONTAINER FORMAT")
        vg_layout = QtWidgets.QGridLayout(video_group)
        vg_layout.setContentsMargins(16, 18, 16, 16)
        vg_layout.setHorizontalSpacing(16)
        vg_layout.setVerticalSpacing(12)
        
        # Row 0: Display & Resolution
        vg_layout.addWidget(QtWidgets.QLabel("Display Source:"), 0, 0)
        self.combo_display = QtWidgets.QComboBox()
        monitors = self.recorder.get_monitors()
        if len(monitors) > 1:
            for idx in range(1, len(monitors)):
                m = monitors[idx]
                self.combo_display.addItem(f"🖥️ Monitor {idx} ({m['width']}x{m['height']})", idx)
        else:
            self.combo_display.addItem("🖥️ Primary Display (1920x1080)", 1)
        vg_layout.addWidget(self.combo_display, 0, 1)
        
        vg_layout.addWidget(QtWidgets.QLabel("Target Resolution:"), 0, 2)
        self.combo_res = QtWidgets.QComboBox()
        self.combo_res.addItems([
            "Native (Original)",
            "4K UHD (3840x2160)",
            "2K QHD (2560x1440)",
            "1080p FHD (1920x1080)",
            "720p HD (1280x720)",
            "480p SD (854x480)"
        ])
        vg_layout.addWidget(self.combo_res, 0, 3)
        
        # Row 1: Format & Quality Bitrate Profile
        vg_layout.addWidget(QtWidgets.QLabel("Output Format:"), 1, 0)
        self.combo_format = QtWidgets.QComboBox()
        for fmt in FORMAT_SPECS.keys():
            self.combo_format.addItem(fmt)
        vg_layout.addWidget(self.combo_format, 1, 1)
        
        vg_layout.addWidget(QtWidgets.QLabel("Video Quality:"), 1, 2)
        self.combo_quality = QtWidgets.QComboBox()
        for q in QUALITY_PROFILES.keys():
            self.combo_quality.addItem(q)
        self.combo_quality.setCurrentText("High (Crystal Clear / 12 Mbps)")
        vg_layout.addWidget(self.combo_quality, 1, 3)
        
        # Row 2: Frame Rate & Encoder Engine
        vg_layout.addWidget(QtWidgets.QLabel("Framerate (FPS):"), 2, 0)
        self.combo_fps = QtWidgets.QComboBox()
        self.combo_fps.addItems(["60 FPS (Ultra Smooth)", "30 FPS (Standard)", "120 FPS (High Refresh)", "24 FPS (Cinematic)"])
        vg_layout.addWidget(self.combo_fps, 2, 1)
        
        vg_layout.addWidget(QtWidgets.QLabel("Encoder Acceleration:"), 2, 2)
        self.combo_encoder = QtWidgets.QComboBox()
        self.combo_encoder.addItems(["⚡ NVIDIA NVENC (GPU Boost)", "🖥️ Software x264 (CPU)"])
        vg_layout.addWidget(self.combo_encoder, 2, 3)
        
        left_panel.addWidget(video_group)
        
        # 2. AUDIO MIXER & CHANNELS
        audio_group = QtWidgets.QGroupBox("2. DUAL-CHANNEL AUDIO MIXER (OBS-STYLE VU METERS)")
        ag_layout = QtWidgets.QVBoxLayout(audio_group)
        ag_layout.setContentsMargins(16, 18, 16, 16)
        ag_layout.setSpacing(14)
        
        # Channel 1: Desktop / System Audio
        sys_box = QtWidgets.QVBoxLayout()
        sys_top = QtWidgets.QHBoxLayout()
        self.chk_sys_audio = QtWidgets.QCheckBox("🔊 SYSTEM AUDIO (Desktop / Games / Music / Discord)")
        self.chk_sys_audio.setChecked(True)
        sys_top.addWidget(self.chk_sys_audio)
        sys_top.addStretch()
        self.lbl_sys_vol = QtWidgets.QLabel("100%")
        self.lbl_sys_vol.setStyleSheet("font-weight: 700; color: #38bdf8;")
        sys_top.addWidget(self.lbl_sys_vol)
        sys_box.addLayout(sys_top)
        
        sys_slider_box = QtWidgets.QHBoxLayout()
        self.slider_sys = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_sys.setRange(0, 100)
        self.slider_sys.setValue(100)
        self.slider_sys.valueChanged.connect(self.on_sys_slider_change)
        sys_slider_box.addWidget(self.slider_sys)
        sys_box.addLayout(sys_slider_box)
        
        self.meter_sys = AudioMeter(self, color="#00f2fe")
        sys_box.addWidget(self.meter_sys)
        ag_layout.addLayout(sys_box)
        
        ag_layout.addSpacing(4)
        
        # Channel 2: Microphone
        mic_box = QtWidgets.QVBoxLayout()
        mic_top = QtWidgets.QHBoxLayout()
        self.chk_mic_audio = QtWidgets.QCheckBox("🎙️ MICROPHONE (Voice Input)")
        self.chk_mic_audio.setChecked(True)
        mic_top.addWidget(self.chk_mic_audio)
        mic_top.addStretch()
        self.lbl_mic_vol = QtWidgets.QLabel("100%")
        self.lbl_mic_vol.setStyleSheet("font-weight: 700; color: #ff2a5f;")
        mic_top.addWidget(self.lbl_mic_vol)
        mic_box.addLayout(mic_top)
        
        mic_slider_box = QtWidgets.QHBoxLayout()
        self.slider_mic = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_mic.setRange(0, 100)
        self.slider_mic.setValue(100)
        self.slider_mic.valueChanged.connect(self.on_mic_slider_change)
        mic_slider_box.addWidget(self.slider_mic)
        mic_box.addLayout(mic_slider_box)
        
        self.meter_mic = AudioMeter(self, color="#ff0055")
        mic_box.addWidget(self.meter_mic)
        ag_layout.addLayout(mic_box)
        
        left_panel.addWidget(audio_group)
        body_layout.addLayout(left_panel, stretch=6)
        
        # RIGHT COLUMN: RECORDINGS VAULT
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(10)
        
        rec_group = QtWidgets.QGroupBox("RECORDINGS VAULT")
        rg_layout = QtWidgets.QVBoxLayout(rec_group)
        rg_layout.setContentsMargins(14, 18, 14, 14)
        rg_layout.setSpacing(10)
        
        self.list_recordings = QtWidgets.QListWidget()
        self.list_recordings.itemDoubleClicked.connect(self.play_selected_video)
        rg_layout.addWidget(self.list_recordings)
        
        vault_btns = QtWidgets.QHBoxLayout()
        vault_btns.setSpacing(8)
        
        btn_open_folder = QtWidgets.QPushButton("📂 Open Folder")
        btn_open_folder.setStyleSheet("""
            QPushButton {
                background-color: #141924;
                border: 1px solid #28334a;
                padding: 7px 12px;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #21293b; border-color: #ff2a5f; }
        """)
        btn_open_folder.clicked.connect(self.open_recordings_folder)
        vault_btns.addWidget(btn_open_folder)
        
        btn_play = QtWidgets.QPushButton("▶ Play")
        btn_play.setStyleSheet("""
            QPushButton {
                background-color: #141924;
                border: 1px solid #28334a;
                padding: 7px 12px;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #21293b; border-color: #ff2a5f; }
        """)
        btn_play.clicked.connect(self.play_selected_video)
        vault_btns.addWidget(btn_play)
        
        btn_delete = QtWidgets.QPushButton("🗑 Delete")
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #1c1418;
                border: 1px solid #4a1f28;
                padding: 7px 12px;
                border-radius: 6px;
                font-weight: 700;
                color: #f87171;
            }
            QPushButton:hover { background-color: #38151f; }
        """)
        btn_delete.clicked.connect(self.delete_selected_video)
        vault_btns.addWidget(btn_delete)
        
        rg_layout.addLayout(vault_btns)
        right_panel.addWidget(rec_group)
        
        body_layout.addLayout(right_panel, stretch=4)
        main_layout.addLayout(body_layout)
        
        # --- BOTTOM ACTION BAR: DURATION & GIANT RECORD CONTROLS ---
        footer = QtWidgets.QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #0c1018;
                border: 1px solid #1c2436;
                border-radius: 16px;
                padding: 8px 18px;
            }
        """)
        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.setSpacing(20)
        
        # Live Recording Indicator & Digital Timer
        timer_box = QtWidgets.QHBoxLayout()
        timer_box.setSpacing(10)
        self.status_dot = QtWidgets.QLabel("●")
        self.status_dot.setStyleSheet("color: #475569; font-size: 24px;")
        timer_box.addWidget(self.status_dot)
        
        self.lbl_timer = QtWidgets.QLabel("00:00:00")
        self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: 900; font-family: monospace; color: #f8fafc;")
        timer_box.addWidget(self.lbl_timer)
        
        self.lbl_status_text = QtWidgets.QLabel("READY")
        self.lbl_status_text.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        timer_box.addWidget(self.lbl_status_text)
        footer_layout.addLayout(timer_box)
        
        footer_layout.addStretch()
        
        # PAUSE / RESUME BUTTON
        self.btn_pause = QtWidgets.QPushButton("⏸ PAUSE (F10)")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setFixedSize(140, 50)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #171d2b;
                border: 1px solid #2d3952;
                color: #e2e8f0;
                font-weight: 800;
                font-size: 13px;
                border-radius: 25px;
            }
            QPushButton:hover { background-color: #242e44; border-color: #38bdf8; }
            QPushButton:disabled { color: #334155; border-color: #141924; background-color: #0d111a; }
        """)
        self.btn_pause.clicked.connect(self.toggle_pause)
        footer_layout.addWidget(self.btn_pause)
        
        # GIANT RECORD / STOP BUTTON
        self.btn_record = QtWidgets.QPushButton("● START RECORDING (F9)")
        self.btn_record.setFixedSize(250, 50)
        self.btn_record.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0844, stop:1 #ff4e50);
                border: none;
                color: #ffffff;
                font-weight: 900;
                font-size: 14px;
                letter-spacing: 1.2px;
                border-radius: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e0073c, stop:1 #e04446);
            }
        """)
        self.btn_record.clicked.connect(self.toggle_recording)
        footer_layout.addWidget(self.btn_record)
        
        main_layout.addWidget(footer)
        
        # Status Bar
        self.statusBar().showMessage("Ready to record with RTX NVENC acceleration.")
        self.refresh_recordings_list()

    def setup_hotkeys(self):
        self.hotkey_signal.connect(self.handle_hotkey)
        try:
            keyboard.add_hotkey("f9", lambda: self.hotkey_signal.emit("f9"))
            keyboard.add_hotkey("f10", lambda: self.hotkey_signal.emit("f10"))
        except Exception as e:
            print("Hotkey setup note:", e)

    def handle_hotkey(self, key):
        if key == "f9":
            self.toggle_recording()
        elif key == "f10":
            self.toggle_pause()

    def on_sys_slider_change(self, val):
        self.lbl_sys_vol.setText(f"{val}%")
        self.recorder.sys_volume = val / 100.0

    def on_mic_slider_change(self, val):
        self.lbl_mic_vol.setText(f"{val}%")
        self.recorder.mic_volume = val / 100.0

    def toggle_recording(self):
        if not self.recorder.is_recording:
            # Gather user choices
            format_name = self.combo_format.currentText()
            fmt_spec = FORMAT_SPECS.get(format_name, FORMAT_SPECS["MP4 (Universal)"])
            ext = fmt_spec["ext"]
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"STARSCREAM_{timestamp}.{ext}"
            filepath = os.path.join(self.output_dir, filename)
            
            mon_idx = self.combo_display.currentData() or 1
            fps_str = self.combo_fps.currentText()
            fps = 60
            if "120" in fps_str: fps = 120
            elif "60" in fps_str: fps = 60
            elif "30" in fps_str: fps = 30
            elif "24" in fps_str: fps = 24
            
            resolution = self.combo_res.currentText()
            quality = self.combo_quality.currentText()
            rec_sys = self.chk_sys_audio.isChecked()
            rec_mic = self.chk_mic_audio.isChecked()
            
            use_nvenc = "NVENC" in self.combo_encoder.currentText()
            self.recorder.use_nvenc = use_nvenc
            
            ok = self.recorder.start(
                filepath,
                monitor_idx=mon_idx,
                record_sys=rec_sys,
                record_mic=rec_mic,
                fps=fps,
                resolution=resolution,
                quality=quality,
                container_format=format_name
            )
            
            if ok:
                self.btn_record.setText("■ STOP RECORDING (F9)")
                self.btn_record.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7f1d1d, stop:1 #991b1b);
                        border: 1px solid #ef4444;
                        color: #ffffff;
                        font-weight: 900;
                        font-size: 14px;
                        letter-spacing: 1.2px;
                        border-radius: 25px;
                    }
                    QPushButton:hover {
                        background: #b91c1c;
                    }
                """)
                self.status_dot.setStyleSheet("color: #ef4444; font-size: 24px;")
                self.lbl_status_text.setText("RECORDING LIVE")
                self.lbl_status_text.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 700;")
                self.btn_pause.setEnabled(True)
                self.btn_pause.setText("⏸ PAUSE (F10)")
                self.statusBar().showMessage(f"Recording active: {resolution} @ {fps}fps [{format_name}]")
        else:
            # Stop recording
            self.btn_record.setText("FINALIZING VIDEO...")
            self.btn_record.setEnabled(False)
            self.lbl_status_text.setText("MUXING & SAVING...")
            self.lbl_status_text.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 700;")
            QtWidgets.QApplication.processEvents()
            
            saved = self.recorder.stop()
            self.btn_record.setEnabled(True)
            self.btn_record.setText("● START RECORDING (F9)")
            self.btn_record.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0844, stop:1 #ff4e50);
                    border: none;
                    color: #ffffff;
                    font-weight: 900;
                    font-size: 14px;
                    letter-spacing: 1.2px;
                    border-radius: 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e0073c, stop:1 #e04446);
                }
            """)
            self.status_dot.setStyleSheet("color: #475569; font-size: 24px;")
            self.lbl_status_text.setText("SAVED")
            self.lbl_status_text.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 700;")
            self.lbl_timer.setText("00:00:00")
            self.btn_pause.setEnabled(False)
            self.btn_pause.setText("⏸ PAUSE (F10)")
            self.meter_sys.setValue(0)
            self.meter_mic.setValue(0)
            
            self.refresh_recordings_list()
            if saved and os.path.exists(saved):
                sz_mb = os.path.getsize(saved) / (1024 * 1024)
                self.statusBar().showMessage(f"Saved: {os.path.basename(saved)} ({sz_mb:.1f} MB)", 5000)

    def toggle_pause(self):
        if self.recorder.is_recording:
            paused = self.recorder.toggle_pause()
            if paused:
                self.btn_pause.setText("▶ RESUME (F10)")
                self.btn_pause.setStyleSheet("""
                    QPushButton {
                        background-color: #b45309;
                        border: 1px solid #f59e0b;
                        color: #ffffff;
                        font-weight: 800;
                        font-size: 13px;
                        border-radius: 25px;
                    }
                    QPushButton:hover { background-color: #d97706; }
                """)
                self.status_dot.setStyleSheet("color: #f59e0b; font-size: 24px;")
                self.lbl_status_text.setText("PAUSED")
                self.lbl_status_text.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 700;")
            else:
                self.btn_pause.setText("⏸ PAUSE (F10)")
                self.btn_pause.setStyleSheet("""
                    QPushButton {
                        background-color: #171d2b;
                        border: 1px solid #2d3952;
                        color: #e2e8f0;
                        font-weight: 800;
                        font-size: 13px;
                        border-radius: 25px;
                    }
                    QPushButton:hover { background-color: #242e44; border-color: #38bdf8; }
                """)
                self.status_dot.setStyleSheet("color: #ef4444; font-size: 24px;")
                self.lbl_status_text.setText("RECORDING LIVE")
                self.lbl_status_text.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 700;")

    def update_live_meters(self):
        if self.recorder.is_recording:
            dur = int(self.recorder.get_duration())
            h = dur // 3600
            m = (dur % 3600) // 60
            s = dur % 60
            self.lbl_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")
            
            if not self.recorder.is_paused and (dur % 2 == 0):
                self.status_dot.setStyleSheet("color: #ff0055; font-size: 26px;")
            elif not self.recorder.is_paused:
                self.status_dot.setStyleSheet("color: #991b1b; font-size: 24px;")
                
            sys_val = min(100, int((self.recorder.current_sys_level ** 0.5) * 100))
            mic_val = min(100, int((self.recorder.current_mic_level ** 0.5) * 100))
            self.meter_sys.setValue(sys_val)
            self.meter_mic.setValue(mic_val)
        else:
            self.meter_sys.setValue(0)
            self.meter_mic.setValue(0)

    def refresh_recordings_list(self):
        self.list_recordings.clear()
        if not os.path.exists(self.output_dir):
            return
            
        supported_exts = (".mp4", ".mkv", ".mov", ".webm")
        files = [f for f in os.listdir(self.output_dir) if f.lower().endswith(supported_exts)]
        files.sort(reverse=True)
        
        for f in files:
            path = os.path.join(self.output_dir, f)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            item = QtWidgets.QListWidgetItem(f"📹 {f}  [{size_mb:.1f} MB]")
            item.setData(QtCore.Qt.UserRole, path)
            self.list_recordings.addItem(item)

    def play_selected_video(self):
        item = self.list_recordings.currentItem()
        if item:
            path = item.data(QtCore.Qt.UserRole)
            if path and os.path.exists(path):
                os.startfile(path)

    def delete_selected_video(self):
        item = self.list_recordings.currentItem()
        if item:
            path = item.data(QtCore.Qt.UserRole)
            if path and os.path.exists(path):
                confirm = QtWidgets.QMessageBox.question(
                    self, "Delete Recording", 
                    f"Are you sure you want to delete {os.path.basename(path)}?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if confirm == QtWidgets.QMessageBox.Yes:
                    try:
                        os.remove(path)
                        self.refresh_recordings_list()
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "Error", f"Failed to delete: {e}")

    def open_recordings_folder(self):
        if os.path.exists(self.output_dir):
            os.startfile(self.output_dir)

    def closeEvent(self, event):
        if self.recorder.is_recording:
            reply = QtWidgets.QMessageBox.question(
                self, "Recording in Progress",
                "A recording is currently running. Stop and save before exiting?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.recorder.stop()
                event.accept()
            elif reply == QtWidgets.QMessageBox.No:
                self.recorder.stop()
                event.accept()
            else:
                event.ignore()
                return
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = StarScreamWindow()
    window.show()
    sys.exit(app.exec())
