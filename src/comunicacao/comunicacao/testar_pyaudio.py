#!/usr/bin/env python3
"""
Grava 3 segundos de áudio diretamente via PyAudio (sem passar pelo
speech_recognition) de um device_index específico, e salva como .wav
pra você conferir com aplay se realmente capturou som.

Uso:
    python3 testar_pyaudio.py 4
    aplay teste_pyaudio.wav

Troque o "4" pelo índice que você quer testar (4 = sof-hda-dsp hw:1,0,
8 = sof-hda-dsp hw:1,6/DMIC).
"""
import sys
import wave
import pyaudio

DEVICE_INDEX = int(sys.argv[1]) if len(sys.argv) > 1 else 4
DURACAO_SEGUNDOS = 3
ARQUIVO_SAIDA = "teste_pyaudio.wav"

p = pyaudio.PyAudio()

info = p.get_device_info_by_index(DEVICE_INDEX)
print(f"Gravando do dispositivo [{DEVICE_INDEX}]: {info['name']}")
print(f"Taxa de amostragem padrão do device: {info['defaultSampleRate']}")

taxa = int(info['defaultSampleRate'])
canais = min(int(info['maxInputChannels']), 2) or 1

print(f"Usando: {canais} canal(is), {taxa} Hz")

stream = p.open(
    format=pyaudio.paInt16,
    channels=canais,
    rate=taxa,
    input=True,
    input_device_index=DEVICE_INDEX,
    frames_per_buffer=1024,
)

print(f"Gravando {DURACAO_SEGUNDOS} segundos... FALE ALGO AGORA!")
frames = []
for _ in range(0, int(taxa / 1024 * DURACAO_SEGUNDOS)):
    dados = stream.read(1024, exception_on_overflow=False)
    frames.append(dados)

print("Gravação finalizada.")

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(ARQUIVO_SAIDA, 'wb')
wf.setnchannels(canais)
wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
wf.setframerate(taxa)
wf.writeframes(b''.join(frames))
wf.close()

# Calcula o volume médio (RMS) pra já dar uma pista sem precisar nem ouvir
import audioop
todo_audio = b''.join(frames)
rms = audioop.rms(todo_audio, 2)
print(f"Volume médio (RMS) capturado: {rms}")
if rms < 20:
    print("=> Isso é praticamente silêncio. O device provavelmente está errado ou mudo.")
else:
    print("=> Captou algum sinal de áudio! Roda 'aplay teste_pyaudio.wav' pra ouvir.")

print(f"\nSalvo em: {ARQUIVO_SAIDA}")
