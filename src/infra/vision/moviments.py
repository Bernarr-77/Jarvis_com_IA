import cv2
import numpy as np
from typing import Any, List, Tuple
import mediapipe as mp


mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

class RastreadorDeMaos:
    def __init__(self, max_maos: int, confianca_minima: float):
        self.max_maos = max_maos
        self.confianca_minima = confianca_minima
        self.modelo = mp_hands.Hands(static_image_mode=False, max_num_hands=self.max_maos,min_detection_confidence=self.confianca_minima)


    def processar_frame(self, frame: np.ndarray) -> List:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultados = self.modelo.process(frame_rgb)
        if not resultados.multi_hand_landmarks:
            return []
        return resultados.multi_hand_landmarks

    def desenhar_maos(self, frame: np.ndarray, maos_detectadas: List) -> None:

        for landmarks in maos_detectadas:
            mp_drawing.draw_landmarks(
                frame, 
                landmarks, 
                mp_hands.HAND_CONNECTIONS
            )
