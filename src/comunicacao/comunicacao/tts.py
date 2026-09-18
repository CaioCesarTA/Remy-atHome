import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import time
import google.generativeai as genai

# Coloca a sua chave de API do Google Gemini aqui
CHAVE_API = "SUA_API_KEY_AQUI"
genai.configure(api_key=CHAVE_API)

modelo_ia = genai.GenerativeModel('gemini-1.5-flash')

def ouvir_microfone():
    """Função para escutar e reconhecer a voz do usuário."""
    reconhecedor = sr.Recognizer()
    
    with sr.Microphone() as fonte:
        reconhecedor.adjust_for_ambient_noise(fonte, duration=1)
        print("\n🎙️ Pode falar, estou ouvindo...")
        
        try:
            audio = reconhecedor.listen(fonte, timeout=5, phrase_time_limit=10)
            texto = reconhecedor.recognize_google(audio, language='pt-BR')
            print(f"👤 Você disse: {texto}")
            return texto.lower()
            
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            print("⚠️ Erro de conexão com a internet.")
            return None
        except sr.WaitTimeoutError:
            return None

def pensar_resposta(pergunta):
    """Envia a pergunta para a IA e retorna a resposta."""
    print("🧠 Pensando...")
    try:
        prompt = f"Você é uma assistente de voz virtual muito simpática e prestativa. Responda de forma natural, curta (no máximo 2 frases) e direta ao ponto a seguinte frase: {pergunta}"
        
        resposta = modelo_ia.generate_content(prompt)
        texto_limpo = resposta.text.replace('*', '') 
        return texto_limpo
    except Exception as e:
        print(f"Erro na IA: {e}")
        return "Desculpe, estou com problemas na minha conexão de pensamento."

def falar(texto):
    """Função para transformar texto em voz e reproduzir."""
    if not texto:
        return
        
    print(f"🤖 Assistente: {texto}")
    
    tts = gTTS(text=texto, lang='pt-br', slow=False)
    arquivo_audio = "resposta.mp3"
    tts.save(arquivo_audio)
    

    pygame.mixer.init()
    pygame.mixer.music.load(arquivo_audio)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    
    pygame.mixer.quit()
    os.remove(arquivo_audio)

if __name__ == "__main__":
    if CHAVE_API == "SUA_API_KEY_AQUI":
        print("⚠️ AVISO: Você precisa colocar sua API Key do Google Gemini no código!")
    else:
        falar("Olá! Estou pronta. O que você quer saber?")
        
        while True:
            comando = ouvir_microfone()
            
            if comando:
                if "sair" in comando or "desligar" in comando or "tchau" in comando:
                    falar("Tchauzinho! Até a próxima.")
                    break
                
                resposta_ia = pensar_resposta(comando)
                falar(resposta_ia)