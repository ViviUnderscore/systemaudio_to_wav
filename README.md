# sysaudrec

Tkinter app to record **system audio output** ("what you hear") to **WAV** on Windows via WASAPI loopback using `soundcard`.

## Features
- 🟥 **Record** / 🟩 **Stop** buttons
- Choose **output folder**
- Optional **custom file name** (auto-adds `.wav` and makes `name_01.wav`, `name_02.wav` if the file exists)
- 16-bit PCM, **48 kHz**, **stereo** by default
- Works best on **Windows 10/11**

---

## Requirements
- Windows 10/11
- Python **3.9+**
- Default playback device set correctly in Windows Sound settings

---

## Quick start (Windows, `cmd.exe`)

py -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
python -m sysaudrec
The GUI opens. Pick a folder and (optionally) type a file name, then Record → Stop.
Files save to the chosen folder. If a name already exists, _01, _02, … are appended.

Troubleshooting
"Binary mode of fromstring is removed, use frombuffer instead"
Pin NumPy < 2.0 (the app already targets this, but here are the commands):

.\.venv\Scripts\activate
pip uninstall -y numpy
pip install "numpy<2.0" --no-cache-dir
pip install -e . --no-deps
"No loopback capture device found"
Ensure your intended playback device is Default in Windows Sound settings.

List loopback devices:

python -c "import soundcard as sc; print([m.name for m in sc.all_microphones(include_loopback=True)])"
If multiple audio outputs (USB/HDMI), switch defaults and relaunch.

Verify a saved WAV has audio (no speakers needed)

python -c "import wave, numpy as np; p=r'PATH\\TO\\YOUR.wav'; w=wave.open(p,'rb'); n=w.getnframes(); f=w.readframes(n); w.close(); x=np.frombuffer(f, dtype=np.int16); rms=int((x.astype('float64')**2).mean()**0.5) if x.size else 0; print('rms=',rms)"
Non-zero rms means real signal.

Visualize audio without speakers
Windows Media Player → Ctrl+3 → right-click → Visualizations → Bars and Waves → Bars

Audacity → open the WAV to see waveform/spectrogram

License MIT © 2025 Tiān Jié Héng Feel free to fork, and fuck off! :)
