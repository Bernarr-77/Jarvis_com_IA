from src.infra.vision.camera import CameraManager
import cv2
import logging
from src.infra.vision.moviments import RastreadorDeMaos
import pyautogui
import math
import pygame
import speech_recognition as sr

pyautogui.PAUSE = 0

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
pygame.mixer.init()
pygame.mixer.music.load("src/AC-DC-Back-in-black.mp3")
jarvis_ativado = False

reconhecedor = sr.Recognizer()
microfone = sr.Microphone()


def callback_voz(reconhecedor, audio):
    global jarvis_ativado
    try:
        texto = reconhecedor.recognize_google(audio, language="pt-PT")
        print(f"O microfone ouviu: {texto}")
        
        if "jar" in texto.lower() and jarvis_ativado == False:
            pygame.mixer.music.play(start=5)
            jarvis_ativado = True
            
    except:
        pass 


with microfone as fonte:
    reconhecedor.adjust_for_ambient_noise(fonte)
reconhecedor.listen_in_background(microfone, callback_voz)
print("Ouvidos ligados! Pode iniciar a câmara...")

def iniciar_sistema():
    global jarvis_ativado
    rastreador = RastreadorDeMaos(max_maos=1, confianca_minima= 0.7)
    cv2.namedWindow("Assistente de Matematica", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Assistente de Matematica", 800, 600)
    y_anterior = 0
    with CameraManager() as captura:
        while True:
            
            sucesso, frame = captura.read()
            frame = cv2.flip(frame, 1 )
            tela_w,tela_h = pyautogui.size()
            if not sucesso:
                logger.error("Falha ao acessar a câmera.")
                break
            processo = rastreador.processar_frame(frame=frame)
            
            if processo:
                rastreador.desenhar_maos(frame=frame, maos_detectadas=processo)
                primeira_mao = processo[0]
                x_indicador = primeira_mao.landmark[8].x
                y_indicador = primeira_mao.landmark[8].y
                pixel_x_indicador = int(x_indicador * tela_w)
                pixel_y_indicador = int(y_indicador * tela_h)

                movimento_y = pixel_y_indicador -  y_anterior
                y_anterior = movimento_y

                x_polegar = primeira_mao.landmark[4].x
                y_polegar = primeira_mao.landmark[4].y
                pixel_x_polegar = int(x_polegar * tela_w)
                pixel_y_polegar = int(y_polegar * tela_h)
                hipotenusa = math.hypot((pixel_x_polegar - pixel_x_indicador), (pixel_y_polegar - pixel_y_indicador))

                if hipotenusa > 45:
                    pyautogui.moveTo(pixel_x_indicador,pixel_y_indicador)
                else:
                    if abs(movimento_y) > 15: 
                        forca_scroll = movimento_y * -3
                        pyautogui.scroll(forca_scroll)

                y_anterior = pixel_y_indicador
            cv2.imshow("Assistente de Matematica", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("Usuário encerra a aplicação.")
                break
    cv2.destroyAllWindows()


if __name__ == '__main__':
    iniciar_sistema()
    callback_voz()
# python -m src.main     