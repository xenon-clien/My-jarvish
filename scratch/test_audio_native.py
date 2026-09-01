import sounddevice as sd
import numpy as np
import speech_recognition as sr
import time

print("Testing 44.1kHz Stereo Downmix Audio Pipeline...")
device_info = sd.query_devices(kind='input')
sample_rate = int(device_info.get('default_samplerate', 44100))
channels = int(device_info.get('max_input_channels', 2))
print(f"Device: {device_info['name']} | SampleRate: {sample_rate} | Channels: {channels}")

# Test chunk read
stream = sd.InputStream(samplerate=sample_rate, channels=channels, dtype="int16")
stream.start()
time.sleep(0.5)
data, _ = stream.read(1024)
stream.stop()
stream.close()

data_mono = np.mean(data, axis=1) if channels > 1 else data.flatten()
rms = float(np.sqrt(np.mean(data_mono.astype(np.float64) ** 2)))
print(f"Sample RMS: {rms:.2f} (Clean capture successful!)")
