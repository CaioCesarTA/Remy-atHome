#!/usr/bin/env python3
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import contextlib
import sys
import warnings

#redireciona o stderr temporariamente pro /dev/null durante
# a abertura de dispositivos de áudio, onde esses avisos são gerados.
@contextlib.contextmanager
def silenciar_stderr():
    stderr_fd = sys.stderr.fileno()
    stderr_copia = os.dup(stderr_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, stderr_fd)
        yield
    finally:
        os.dup2(stderr_copia, stderr_fd)
        os.close(stderr_copia)
        os.close(devnull_fd)

# Silencia o aviso do Hugging Face Hub
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")

import rclpy
from rclpy.node import Node
import speech_recognition as sr
from faster_whisper import WhisperModel
from piper.voice import PiperVoice
import threading
import subprocess
import pygame
import time
import datetime
import ollama


class AssistenteRemy(Node):
    def __init__(self):
        super().__init__('no_comunicacao')
        self.get_logger().info("iniciando a comunicacao de fala do Remy...")

        # Caminho da voz centralizado (evita duplicação/erro se mudar o modelo)
        self.caminho_voz = "/home/caioDocker/ros2_ws/remy_ws/src/comunicacao/scripts/pt_BR-faber-medium.onnx"

        # Trava para garantir que só um falar() aconteça por vez (evita que
        # duas threads disputem o mesmo canal de áudio do pygame ou o
        # mesmo arquivo .wav simultaneamente).
        self.lock_falar = threading.Lock()

        # Chave geral pra ligar/desligar o fallback pra IA (Ollama). Quando
        # False, comandos que não batem com nenhuma intenção fixa recebem
        # uma resposta padrão em vez de chamar o Ollama. Pode ser trocado
        # direto aqui (True/False) ou via variável de ambiente, sem precisar
        # editar o código:
        #     USAR_IA=false ros2 run comunicacao rodar.py
        self.usar_ia = os.environ.get("USAR_IA", "true").lower() not in ("false", "0", "nao", "não")
        self.get_logger().info(f"Fallback para IA (Ollama): {'ATIVADO' if self.usar_ia else 'DESATIVADO'}")

        # 1. Carrega o modelo de Ouvido (Whisper) na CPU
        self.modelo_whisper = WhisperModel("small", device="cpu", compute_type="int8")

        # 2. Carrega o modelo de Boca (Piper)
        self.modelo_voz = PiperVoice.load(self.caminho_voz)
        self.get_logger().info("Voz e audio carregados!")

        # Inicia o mixer de áudio do pygame
        with silenciar_stderr():
            pygame.mixer.init()

        # 3. Cria a Thread paralela para ouvir o microfone
        self.thread_audicao = threading.Thread(target=self.loop_ouvir)
        self.thread_audicao.daemon = True
        self.thread_audicao.start()

        # 4. Cria a Thread paralela para receber comandos digitados (modo de teste)
        self.thread_texto = threading.Thread(target=self.loop_texto)
        self.thread_texto.daemon = True
        self.thread_texto.start()

    def pensar_ollama(self, pergunta):
        """Envia comandos não mapeados para o LLM local processar."""
        self.get_logger().info("Pensando com a IA...")
        try:
            # Você pode trocar 'phi3' para 'llama3' dependendo do modelo que baixar
            resposta = ollama.chat(model='phi3', messages=[
                {
                    'role': 'system',
                    # Esse prompt define a "personalidade" da IA para não falar demais
                    'content': 'Você é o Remy, um robô assistente amigável feito para ajudar idosos e Pessoas Com Deficiencia (PCD). Responda em português, de forma bem natural, prestativa e curta (máximo 2 frases).'
                },
                {
                    'role': 'user',
                    'content': pergunta
                }
            ])
            texto_ia = resposta['message']['content']
            # Remove asteriscos que a IA gera (ex: *sorri*) para o Piper não ler errado
            texto_ia = texto_ia.replace('*', '').strip()

            # Às vezes modelos pequenos "vazam" artefatos de dataset de
            # treinamento (ex: "## Instrucción 2 (más difícil...)"). Corta
            # a resposta no primeiro sinal de cabeçalho markdown ou texto
            # fora do português, mantendo só a parte útil.
            for marcador in ("\n#", "\n##", "\nInstrucción", "\nInstruction"):
                if marcador in texto_ia:
                    texto_ia = texto_ia.split(marcador)[0].strip()

            return texto_ia

        except Exception as e:
            self.get_logger().error(f"Erro na conexão com Ollama: {e}")
            return "Desculpe, estou com dificuldades para acessar meu cérebro principal no momento."

    def falar(self, texto):
        """Transforma texto em áudio chamando o motor do Piper de forma nativa no Linux."""
        if not texto:
            return

        #Garante que a IA saiba onde terminar a frase
        texto = texto.strip()
        if not texto.endswith((".", "!", "?")):
            texto += "."

        self.get_logger().info(f"{texto}")

        # Nome de arquivo único por chamada: evita que duas threads
        # (loop_ouvir e loop_texto) pisem no mesmo arquivo se falarem
        # quase ao mesmo tempo.
        arquivo_saida = f"resposta_remy_{threading.get_ident()}_{int(time.time() * 1000)}.wav"

        # Trava: garante que só um áudio toque por vez no pygame. 
        with self.lock_falar:
            try:
                # Chamada via subprocess (sem shell=True) evita quebra/injeção de comando
                # caso o texto contenha aspas, cifrão, ponto-e-vírgula, etc.
                subprocess.run(
                    [
                        "piper",
                        "--model", self.caminho_voz,
                        "--length_scale", "1.2",
                        "--output_file", arquivo_saida,
                    ],
                    input=texto.encode("utf-8"),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                # Toca o áudio gerado
                if os.path.exists(arquivo_saida) and os.path.getsize(arquivo_saida) > 100:
                    pygame.mixer.music.load(arquivo_saida)
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    pygame.mixer.music.unload()
                else:
                    self.get_logger().error("Falha crítica: O motor Piper não conseguiu gerar o som.")

            except Exception as e:
                self.get_logger().error(f"Erro interno ao tocar o áudio: {e}")

            finally:
                # Mantém a área de trabalho limpa apagando o arquivo temporário
                if os.path.exists(arquivo_saida):
                    try:
                        os.remove(arquivo_saida)
                    except OSError:
                        pass

                # Pequena pausa para não se escutar
                time.sleep(2.0)

    def processar_intencao(self, comando):
        """Lógica simples de if/else para respostas instantâneas (Sem Internet)."""
        # Tudo aqui deve estar em minúsculas, já que 'comando' sempre chega em lower()
        if "o seu nome" in comando:
            self.falar("Meu nome é Remy, sou um projeto de robótica para extensão voltado para a competição da C B R, na categoria at home.")
        elif "que você faz" in comando or "seu objetivo" in comando:
            self.falar("Meu objetivo é auxiliar as pessoas em suas atividades cotidianas e participar da categoria at home da CBR.")
        elif "aura" in comando or "farmar" in comando:
            self.falar("Six seven, six seven, six seven, six seven, six seven, six seven, six seven, six seven, six seven, six seven, six seven, six seven, six seven.")
        elif "que horas" in comando or "horas são" in comando:
            agora = datetime.datetime.now()
            self.falar(f"Agora são {agora.hour} horas e {agora.minute} minutos.")
        elif "bom dia" in comando:
            self.falar("Bom dia! Como posso ajudar você hoje?")
        elif "boa noite" in comando:
            self.falar("Boa noite! Como posso ajudar você hoje?")
        elif "boa tarde" in comando:
            self.falar("Boa tarde! Como posso ajudar você hoje?")
        elif "estou com medo" in comando:
            self.falar("Pra cima deles!")
        elif "extensão" in comando:
            self.falar("Lisa, eu vou puxar o seu pé enquanto vc dorme. Muahh ha ha ha.")
        else:
            if self.usar_ia:
                self.get_logger().info("Comando livre detectado. Enviando para a IA...")
                resposta_ia = self.pensar_ollama(comando)
                self.falar(resposta_ia)
            else:
                self.get_logger().info("Comando livre detectado, mas a IA está desativada.")
                self.falar("Desculpe, não entendi esse comando. Pode tentar de outra forma?")

    def loop_texto(self):
        """Thread que recebe comandos digitados no terminal para testes rápidos."""
        # Espera um pouco só para dar tempo de os logs iniciais do ROS aparecerem
        time.sleep(2)

        while rclpy.ok():
            try:
                # Abre a caixa de texto no terminal para você digitar
                texto_digitado = input("\nDigite o que você quer falar para o Remy: \n")

                if texto_digitado.strip():
                    texto_min = texto_digitado.lower()
                    self.get_logger().info(f"O que eu 'ouvi': '{texto_min}'")
                    self.processar_intencao(texto_min)

            except EOFError:
                break
            except Exception as e:
                self.get_logger().warning(f"Erro no modo de texto: {e}")

    def loop_ouvir(self):
        """Thread que escuta e transcreve continuamente."""
        reconhecedor = sr.Recognizer()
        arquivo_temp = "fala_temp.wav"

        microfone = sr.Microphone()
        with silenciar_stderr():
            fonte = microfone.__enter__()

        try:
            reconhecedor.adjust_for_ambient_noise(fonte, duration=3)
            nivel_ruido = reconhecedor.energy_threshold
            self.get_logger().info(f"Nível de ruído base detectado: {nivel_ruido:.2f}")
            reconhecedor.dynamic_energy_threshold = False
            reconhecedor.energy_threshold = nivel_ruido + 100
            self.get_logger().info(f"Limiar de gravação ajustado para: {reconhecedor.energy_threshold:.2f}")
            self.get_logger().info("Microfone calibrado. Pode falar!")

            # Controla quando avisar "Escutando..." — só na transição de
            # volta pro estado de escuta (depois de falar ou processar um
            # comando), não a cada tentativa/timeout, senão vira spam.
            avisar_escutando = True

            while rclpy.ok():
                try:
                    # Se o Remy estiver falando agora (lock ocupado), espera
                    # em vez de escutar — evita que ele capte a própria voz
                    # pelo microfone e "converse consigo mesmo".
                    if self.lock_falar.locked():
                        avisar_escutando = True  # ao liberar, avisa de novo
                        time.sleep(0.2)
                        continue

                    if avisar_escutando:
                        self.get_logger().info("Escutando...")
                        avisar_escutando = False

                    audio = reconhecedor.listen(fonte, timeout=5, phrase_time_limit=15)
                    with open(arquivo_temp, "wb") as f:
                        f.write(audio.get_wav_data())

                    self.get_logger().info("Transcrevendo...")
                    segmentos, _ = self.modelo_whisper.transcribe(arquivo_temp, language="pt")

                    texto_final = "".join([segmento.text for segmento in segmentos]).strip()

                    if texto_final:
                        texto_min = texto_final.lower()
                        self.get_logger().info(f"o que eu entendi: '{texto_final}'")
                        self.processar_intencao(texto_min)
                        avisar_escutando = True  # terminou de processar, volta a avisar

                    if os.path.exists(arquivo_temp):
                        os.remove(arquivo_temp)

                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    self.get_logger().warning(f"Ocorreu o seguinte erro na transcricao do audio: {e}")
        finally:
            microfone.__exit__(None, None, None)


def main(args=None):
    rclpy.init(args=args)
    no = AssistenteRemy()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        no.get_logger().info("Fechando o programa. Ate a proxima!")
    finally:
        no.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()