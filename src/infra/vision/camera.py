import cv2

class CameraManager:
    def __init__(self, indice_camara: int = 0):
        self.indice_camara = indice_camara
        self.captura = None

    def __enter__(self):
        self.captura = cv2.VideoCapture(self.indice_camara, cv2.CAP_DSHOW)
        if not self.captura.isOpened():
            raise RuntimeError("Falha de infraestrutura: Não foi possível aceder à câmara.")
        # Resolução 720p para imagem nítida
        self.captura.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.captura.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        return self.captura

    def __exit__(self, tipo_erro, valor_erro, traceback):
        if self.captura:
            self.captura.release() 

