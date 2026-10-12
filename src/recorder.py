import os
import sys
import time
import queue
import threading
import subprocess
import ctypes
import warnings
import numpy as np
import mss
import soundcard as sc

warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

def get_ffmpeg_path():
    # If running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        bundle_ffmpeg = os.path.join(base_dir, 'assets', 'ffmpeg.exe')
        if os.path.exists(bundle_ffmpeg):
            return bundle_ffmpeg
        alt_ffmpeg = os.path.join(os.path.dirname(sys.executable), 'assets', 'ffmpeg.exe')
        if os.path.exists(alt_ffmpeg):
            return alt_ffmpeg
            
    # Check local workspace assets
    local_ffmpeg = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "ffmpeg.exe"))
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    return "ffmpeg"

# Preset Bitrate / Quality mapping
QUALITY_PROFILES = {
    "Ultra (Lossless / 25 Mbps)": {"bitrate": "25M", "maxrate": "35M", "bufsize": "50M", "nvenc_preset": "p7", "x264_crf": "16"},
    "High (Crystal Clear / 12 Mbps)": {"bitrate": "12M", "maxrate": "16M", "bufsize": "24M", "nvenc_preset": "p5", "x264_crf": "18"},
    "Balanced (Recommended / 6 Mbps)": {"bitrate": "6M", "maxrate": "8M", "bufsize": "12M", "nvenc_preset": "p4", "x264_crf": "21"},
    "Economy (Compact / 3 Mbps)": {"bitrate": "3M", "maxrate": "4M", "bufsize": "6M", "nvenc_preset": "p3", "x264_crf": "24"},
}

# Container & Codec specifications
FORMAT_SPECS = {
    "MP4 (Universal)": {
        "ext": "mp4",
        "video_codec_nvenc": "h264_nvenc",
        "video_codec_cpu": "libx264",
        "audio_codec": "aac",
        "audio_bitrate": "256k"
    },
    "MKV (Stream Safe / Crash Proof)": {
        "ext": "mkv",
        "video_codec_nvenc": "h264_nvenc",
        "video_codec_cpu": "libx264",
        "audio_codec": "aac",
        "audio_bitrate": "256k"
    },
    "MOV (QuickTime / Pro Quality)": {
        "ext": "mov",
        "video_codec_nvenc": "h264_nvenc",
        "video_codec_cpu": "libx264",
        "audio_codec": "aac",
        "audio_bitrate": "256k"
    },
    "WEBM (Web Optimized)": {
        "ext": "webm",
        "video_codec_nvenc": "libvpx-vp9",
        "video_codec_cpu": "libvpx-vp9",
        "audio_codec": "libopus",
        "audio_bitrate": "160k"
    }
}

class StarRecorder:
    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self.output_path = None
        self.start_time = 0
        self.pause_start = 0
        self.total_paused_time = 0
        
        self.video_thread = None
        self.audio_thread = None
        self.ffmpeg_proc = None
        
        # Audio configuration
        self.record_mic = True
        self.record_sys = True
        self.mic_volume = 1.0
        self.sys_volume = 1.0
        
        # Live audio meter levels (0.0 to 1.0)
        self.current_mic_level = 0.0
        self.current_sys_level = 0.0
        
        # Capture settings
        self.fps = 60
        self.monitor_idx = 1
        self.use_nvenc = True
        self.resolution = "Native (Original)"
        self.quality = "Balanced (Recommended / 6 Mbps)"
        self.container_format = "MP4 (Universal)"
        
        self._stop_event = threading.Event()

    def _setup_desktop_session(self):
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    def get_monitors(self):
        self._setup_desktop_session()
        try:
            with mss.MSS() as sct:
                return sct.monitors
        except Exception:
            return [{'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]

    def get_audio_devices(self):
        try:
            speakers = [s.name for s in sc.all_speakers()]
            mics = [m.name for m in sc.all_microphones()]
            return speakers, mics
        except Exception:
            return [], []

    def start(self, output_filepath, monitor_idx=1, record_sys=True, record_mic=True, 
              fps=60, resolution="Native (Original)", quality="Balanced (Recommended / 6 Mbps)", 
              container_format="MP4 (Universal)"):
        if self.is_recording:
            return False
            
        self.output_path = output_filepath
        self.monitor_idx = monitor_idx
        self.record_sys = record_sys
        self.record_mic = record_mic
        self.fps = fps
        self.resolution = resolution
        self.quality = quality
        self.container_format = container_format
        
        self.is_paused = False
        self.total_paused_time = 0
        self._stop_event.clear()
        
        # Determine source screen resolution
        self._setup_desktop_session()
        with mss.MSS() as sct:
            if monitor_idx < len(sct.monitors):
                mon = sct.monitors[monitor_idx]
            else:
                mon = sct.monitors[1]
            src_w = mon['width']
            src_h = mon['height']
            
        if src_w % 2 != 0: src_w -= 1
        if src_h % 2 != 0: src_h -= 1

        # Target resolution calculation
        scale_filter = []
        if resolution == "4K UHD (3840x2160)":
            scale_filter = ['-vf', 'scale=3840:2160']
        elif resolution == "2K QHD (2560x1440)":
            scale_filter = ['-vf', 'scale=2560:1440']
        elif resolution == "1080p FHD (1920x1080)":
            scale_filter = ['-vf', 'scale=1920:1080']
        elif resolution == "720p HD (1280x720)":
            scale_filter = ['-vf', 'scale=1280:720']
        elif resolution == "480p SD (854x480)":
            scale_filter = ['-vf', 'scale=854:480']

        # Get quality profile settings
        q_prof = QUALITY_PROFILES.get(quality, QUALITY_PROFILES["Balanced (Recommended / 6 Mbps)"])
        fmt_spec = FORMAT_SPECS.get(container_format, FORMAT_SPECS["MP4 (Universal)"])
        
        # Determine video encoder
        if self.use_nvenc and fmt_spec["ext"] != "webm":
            v_encoder = fmt_spec["video_codec_nvenc"]
            encoder_args = [
                '-c:v', v_encoder,
                '-preset', q_prof["nvenc_preset"],
                '-b:v', q_prof["bitrate"],
                '-maxrate', q_prof["maxrate"],
                '-bufsize', q_prof["bufsize"],
            ]
        else:
            v_encoder = fmt_spec["video_codec_cpu"]
            if v_encoder == "libx264":
                encoder_args = [
                    '-c:v', v_encoder,
                    '-crf', q_prof["x264_crf"],
                    '-preset', 'veryfast',
                ]
            else:
                encoder_args = [
                    '-c:v', v_encoder,
                    '-b:v', q_prof["bitrate"],
                ]

        base_without_ext = os.path.splitext(output_filepath)[0]
        self.temp_audio_file = f"{base_without_ext}_temp_audio.wav"
        self.temp_video_file = f"{base_without_ext}_temp_video.{fmt_spec['ext']}"
        
        ffmpeg_bin = get_ffmpeg_path()
        v_cmd = [
            ffmpeg_bin, '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{src_w}x{src_h}',
            '-pix_fmt', 'bgra',
            '-r', str(self.fps),
            '-i', '-',
        ] + scale_filter + encoder_args + [
            '-pix_fmt', 'yuv420p',
            self.temp_video_file
        ]
        
        self.ffmpeg_proc = subprocess.Popen(
            v_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        self.is_recording = True
        self.start_time = time.time()
        
        self.video_thread = threading.Thread(target=self._video_worker, args=(mon, src_w, src_h), daemon=True)
        self.video_thread.start()
        
        if self.record_sys or self.record_mic:
            self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
            self.audio_thread.start()
            
        return True

    def toggle_pause(self):
        if not self.is_recording:
            return False
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_start = time.time()
        else:
            self.total_paused_time += (time.time() - self.pause_start)
        return self.is_paused

    def get_duration(self):
        if not self.is_recording:
            return 0
        if self.is_paused:
            return self.pause_start - self.start_time - self.total_paused_time
        return time.time() - self.start_time - self.total_paused_time

    def _video_worker(self, mon, target_w, target_h):
        self._setup_desktop_session()
        frame_interval = 1.0 / self.fps
        next_frame_time = time.time()
        
        try:
            with mss.MSS() as sct:
                while not self._stop_event.is_set():
                    now = time.time()
                    if now < next_frame_time:
                        time.sleep(max(0.0005, next_frame_time - now))
                        continue
                    
                    next_frame_time += frame_interval
                    
                    if not self.is_paused:
                        img = sct.grab(mon)
                        if self.ffmpeg_proc and self.ffmpeg_proc.stdin:
                            try:
                                self.ffmpeg_proc.stdin.write(img.raw)
                            except (BrokenPipeError, OSError):
                                break
        except Exception:
            pass

    def _audio_worker(self):
        import wave
        sample_rate = 48000
        channels = 2
        chunk_size = 1920
        
        try:
            spk = sc.default_speaker()
            loopback = sc.get_microphone(id=spk.id, include_loopback=True) if self.record_sys and spk else None
            mic = sc.default_microphone() if self.record_mic else None
        except Exception:
            loopback = None
            mic = None
        
        audio_frames = []
        
        try:
            loop_rec = loopback.recorder(samplerate=sample_rate, channels=channels) if loopback else None
            mic_rec = mic.recorder(samplerate=sample_rate, channels=1) if mic else None
            
            with loop_rec if loop_rec else dummy_context() as lr, \
                 mic_rec if mic_rec else dummy_context() as mr:
                
                while not self._stop_event.is_set():
                    mixed = np.zeros((chunk_size, 2), dtype=np.float32)
                    
                    if lr:
                        try:
                            sys_data = lr.record(numframes=chunk_size)
                            self.current_sys_level = float(np.max(np.abs(sys_data))) if len(sys_data) else 0.0
                            if not self.is_paused:
                                mixed += sys_data * self.sys_volume
                        except Exception:
                            pass
                    else:
                        self.current_sys_level = 0.0
                            
                    if mr:
                        try:
                            mic_data = mr.record(numframes=chunk_size)
                            self.current_mic_level = float(np.max(np.abs(mic_data))) if len(mic_data) else 0.0
                            if not self.is_paused:
                                mic_stereo = np.repeat(mic_data, 2, axis=1)
                                mixed += mic_stereo * self.mic_volume
                        except Exception:
                            pass
                    else:
                        self.current_mic_level = 0.0
                        
                    if not self.is_paused:
                        mixed = np.clip(mixed, -1.0, 1.0)
                        pcm = (mixed * 32767).astype(np.int16).tobytes()
                        audio_frames.append(pcm)
        except Exception:
            pass
            
        try:
            if audio_frames:
                with wave.open(self.temp_audio_file, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(audio_frames))
        except Exception:
            pass

    def stop(self):
        if not self.is_recording:
            return None
            
        self._stop_event.set()
        
        if self.video_thread:
            self.video_thread.join(timeout=3.0)
            
        if self.audio_thread:
            self.audio_thread.join(timeout=3.0)
            
        if self.ffmpeg_proc:
            try:
                if self.ffmpeg_proc.stdin:
                    self.ffmpeg_proc.stdin.close()
                self.ffmpeg_proc.wait(timeout=5.0)
            except Exception:
                self.ffmpeg_proc.kill()

        self.is_recording = False
        self.is_paused = False
        self.current_sys_level = 0.0
        self.current_mic_level = 0.0
        
        fmt_spec = FORMAT_SPECS.get(self.container_format, FORMAT_SPECS["MP4 (Universal)"])
        has_audio = os.path.exists(self.temp_audio_file) and os.path.getsize(self.temp_audio_file) > 1000
        has_video = os.path.exists(self.temp_video_file)
        
        if has_video and has_audio:
            ffmpeg_bin = get_ffmpeg_path()
            mux_cmd = [
                ffmpeg_bin, '-y',
                '-i', self.temp_video_file,
                '-i', self.temp_audio_file,
                '-c:v', 'copy',
                '-c:a', fmt_spec["audio_codec"],
                '-b:a', fmt_spec["audio_bitrate"],
                '-shortest',
                self.output_path
            ]
            subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            try: os.remove(self.temp_video_file)
            except OSError: pass
            try: os.remove(self.temp_audio_file)
            except OSError: pass
            
        elif has_video:
            if os.path.exists(self.output_path):
                try: os.remove(self.output_path)
                except OSError: pass
            os.rename(self.temp_video_file, self.output_path)
            
        return self.output_path

class dummy_context:
    def __enter__(self): return None
    def __exit__(self, exc_type, exc_val, exc_tb): pass
