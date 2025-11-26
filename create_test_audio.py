"""
Basit Test Audio Oluştur
"""
import wave
import struct
import math
from pathlib import Path

def create_simple_test_audio():
    """2 saniyelik test audio oluştur (440Hz sine wave)"""
    
    # Parametreler
    duration = 2  # saniye
    sample_rate = 16000  # Hz (Whisper için optimal)
    frequency = 440.0  # Hz (A4 notası)
    
    # Dosya yolu
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    filepath = test_dir / "test_audio.wav"
    
    print(f"\n🎵 Test audio oluşturuluyor...")
    print(f"   Dosya: {filepath}")
    print(f"   Süre: {duration} saniye")
    print(f"   Sample Rate: {sample_rate} Hz")
    print(f"   Frequency: {frequency} Hz")
    
    # WAV dosyası oluştur
    with wave.open(str(filepath), 'w') as wav_file:
        # Mono, 16-bit
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        # Sine wave oluştur
        num_samples = duration * sample_rate
        
        for i in range(num_samples):
            # Sine wave hesapla
            value = math.sin(2.0 * math.pi * frequency * i / sample_rate)
            # 16-bit integer'a dönüştür
            data = struct.pack('<h', int(value * 32767.0))
            wav_file.writeframes(data)
    
    file_size = filepath.stat().st_size
    print(f"\n✅ Audio dosyası oluşturuldu!")
    print(f"   Boyut: {file_size:,} bytes ({file_size/1024:.2f} KB)")
    print(f"   Yol: {filepath.absolute()}\n")
    
    return str(filepath.absolute())

if __name__ == "__main__":
    audio_path = create_simple_test_audio()
    print(f"🎉 Hazır! Upload için dosya: {audio_path}")
