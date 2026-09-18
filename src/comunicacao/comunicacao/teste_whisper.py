import speech_recognition as sr
from faster_whisper import WhisperModel
import os

# 1. Carrega o modelo do Whisper para a memória de vídeo
# O tamanho "small" é excelente para português e muito rápido.
print("⏳ Carregando o modelo do Whisper...")
modelo_whisper = WhisperModel("small", device="cuda", compute_type="float16")
print("✅ Modelo carregado!")

def ouvir_e_transcrever():
    reconhecedor = sr.Recognizer()
    arquivo_temp = "fala_temp.wav"

    with sr.Microphone() as fonte:
        reconhecedor.adjust_for_ambient_noise(fonte, duration=1)
        print("\n🎙️ Pode falar, estou ouvindo (Offline)...")
        
        try:
            # Captura a voz e salva o áudio da memória para um arquivo
            audio = reconhecedor.listen(fonte, timeout=5, phrase_time_limit=15)
            with open(arquivo_temp, "wb") as f:
                f.write(audio.get_wav_data())
            
            print("🧠 Transcrevendo...")
            
            # O Whisper analisa o arquivo de áudio
            segmentos, info = modelo_whisper.transcribe(arquivo_temp, language="pt")
            
            texto_final = ""
            for segmento in segmentos:
                texto_final += segmento.text + " "
                
            texto_limpo = texto_final.strip()
            print(f"👤 Você disse: {texto_limpo}")
            
            # Limpa a sujeira
            os.remove(arquivo_temp)
            return texto_limpo.lower()

        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"⚠️ Erro: {e}")
            return None

if __name__ == "__main__":
    while True:
        comando = ouvir_e_transcrever()
        
        if comando and ("sair" in comando or "desligar" in comando):
            print("Encerrando o sistema auditivo.")
            break