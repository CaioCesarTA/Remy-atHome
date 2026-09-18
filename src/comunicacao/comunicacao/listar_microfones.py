#!/usr/bin/env python3
"""
Script standalone para descobrir qual índice de microfone o PyAudio/
speech_recognition está enxergando, sem precisar rodar o nó ROS inteiro
nem fazer colcon build. Basta rodar:

    python3 listar_microfones.py
"""
import speech_recognition as sr

print("=" * 60)
print("Microfones detectados pelo PyAudio:")
print("=" * 60)

nomes = sr.Microphone.list_microphone_names()

if not nomes:
    print("Nenhum microfone foi detectado! Verifique se o PyAudio")
    print("está instalado corretamente (sudo apt install portaudio19-dev)")
else:
    for i, nome in enumerate(nomes):
        print(f"[{i}] {nome}")

print("=" * 60)
print(f"Dispositivo padrão do sistema (device_index=None): ", end="")
try:
    with sr.Microphone() as fonte:
        print("OK, abriu sem erro.")
except Exception as e:
    print(f"ERRO ao abrir: {e}")
