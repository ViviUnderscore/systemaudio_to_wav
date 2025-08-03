# -*- coding: utf-8 -*-
import threading
import wave
import os
from datetime import datetime
from typing import Optional

import numpy as np
import soundcard as sc


class SystemAudioRecorder:
    """
    Records system audio via loopback using soundcard.
    Works across soundcard versions where Speaker.recorder may not exist.
    """

    def __init__(self, samplerate: int = 48000, channels: int = 2, frames_per_chunk: int = 1024):
        self.samplerate = int(samplerate)
        self.channels = int(channels)
        self.frames_per_chunk = int(frames_per_chunk)

        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._wavefile: Optional[wave.Wave_write] = None
        self._recorder = None
        self._outfile_path: Optional[str] = None
        self._exception: Optional[Exception] = None

    @staticmethod
    def _float32_to_int16(x: np.ndarray) -> np.ndarray:
        x = np.clip(x, -1.0, 1.0)
        return (x * 32767.0).astype(np.int16)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """
        Keep Windows-safe characters. Always return a .wav name.
        """
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ()"
        base, _ext = os.path.splitext(name or "")
        base = base or "recording"
        base = "".join(c if c in allowed else "_" for c in base)
        base = base.strip(" .")
        if not base:
            base = "recording"
        return base + ".wav"

    @staticmethod
    def _uniquify(folder: str, filename: str) -> str:
        """
        If folder/filename exists, add _01, _02, ... before extension.
        """
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(filename)
        i = 1
        while True:
            cand = os.path.join(folder, f"{base}_{i:02d}{ext}")
            if not os.path.exists(cand):
                return cand
            i += 1

    @staticmethod
    def _find_loopback_mic() -> "sc.Microphone":
        """
        Prefer the loopback mic that matches the default speaker's name.
        Fall back to the first available loopback microphone.
        """
        spk = sc.default_speaker()
        try:
            mic = sc.get_microphone(id=spk.name, include_loopback=True)
            if mic is not None:
                return mic
        except Exception:
            pass

        for m in sc.all_microphones(include_loopback=True):
            name = getattr(m, "name", "")
            if isinstance(name, str) and ("loopback" in name.lower() or spk.name in name):
                return m

        mics = sc.all_microphones(include_loopback=True)
        if mics:
            return mics[0]

        raise RuntimeError(
            "No loopback capture device found. Ensure your audio driver exposes a loopback device."
        )

    def start(self, folder: str, filename: Optional[str] = None) -> str:
        if self._recording:
            raise RuntimeError("Already recording.")
        os.makedirs(folder, exist_ok=True)

        if filename:
            fname = self._sanitize_filename(filename)
            outpath = self._uniquify(folder, fname)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            outpath = os.path.join(folder, f"system_audio_{ts}.wav")

        self._outfile_path = outpath

        self._wavefile = wave.open(self._outfile_path, "wb")
        self._wavefile.setnchannels(self.channels)
        self._wavefile.setsampwidth(2)  # 16-bit PCM
        self._wavefile.setframerate(self.samplerate)

        mic = self._find_loopback_mic()
        self._recorder = mic.recorder(samplerate=self.samplerate, channels=self.channels)

        self._exception = None
        self._recording = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self._outfile_path

    def _run(self) -> None:
        try:
            assert self._recorder is not None
            assert self._wavefile is not None
            with self._recorder as rec:
                while self._recording:
                    data = rec.record(self.frames_per_chunk)  # float32 [frames, channels]
                    pcm16 = self._float32_to_int16(data)
                    self._wavefile.writeframes(pcm16.tobytes())
        except Exception as e:
            self._exception = e
        finally:
            try:
                if self._wavefile is not None:
                    self._wavefile.close()
            finally:
                self._wavefile = None

    def stop(self) -> str:
        if not self._recording:
            return self._outfile_path or ""
        self._recording = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        err = self._exception
        path = self._outfile_path or ""
        self._outfile_path = None
        self._exception = None
        self._thread = None
        if err:
            raise err
        return path
