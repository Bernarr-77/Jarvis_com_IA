# JARVIS com IA 🦾

Assistente Virtual Inteligente utilizando Visão Computacional e IA Generativa Multimodal.

O **JARVIS** é um projeto de automação e acessibilidade inspirado na ficção científica. Ele é capaz de "ver" o ambiente através da sua câmera, entender o contexto visual, "ouvir" seus comandos de voz e responder de forma inteligente, além de permitir o controle do cursor do mouse do computador usando apenas movimentos e gestos das mãos.

## 🚀 Funcionalidades

*   **Rastreamento de Mãos (Hand Tracking):** Controle o cursor do mouse na tela usando a câmera. Faça o movimento de "pinça" (juntar o polegar e o indicador) para executar cliques e rolagem (scroll).
*   **Inteligência Multimodal (Visão e Contexto):** Utiliza a API do **Google Gemini** para processar frames de vídeo em tempo real combinados com seus comandos de voz. O JARVIS sabe exatamente o que está acontecendo na frente da câmera.
*   **Comandos de Voz em Background:** Fica ouvindo passivamente. Diga a palavra-chave **"Jarvis"** para ativar a escuta de comandos avançados (usando `SpeechRecognition`).
*   **Síntese de Voz Realista (TTS):** As respostas geradas pela IA são vocalizadas usando uma voz clonada altamente realista do personagem JARVIS através da API do **Fish Audio**.
*   **Multithreading:** Arquitetura robusta para que a câmera não trave enquanto o assistente processa a voz e reproduz áudio.

## 🛠️ Tecnologias Utilizadas

*   **Linguagem:** Python 3
*   **Visão Computacional:** OpenCV, MediaPipe
*   **Controle de Interface:** PyAutoGUI
*   **Inteligência Artificial:** Google GenAI (Gemini)
*   **Reconhecimento de Voz:** SpeechRecognition
*   **Síntese de Voz (TTS):** Fish Audio

## ⚙️ Como Instalar e Rodar

1. Clone este repositório:
   ```bash
   git clone https://github.com/Bernarr-77/Jarvis_com_IA.git
   cd Jarvis_com_IA
   ```
2. Crie e ative um ambiente virtual (recomendado):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure as chaves de API:
   *   Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
       ```env
       GOOGLE_API_KEY=sua_chave_gemini_aqui
       FISH_API_KEY=sua_chave_fish_audio_aqui
       ID_MODEL=id_do_modelo_de_voz_jarvis
       ```
5. Execute o JARVIS:
   ```bash
   python -m src.main
   ```

## 👨‍💻 Autoria e Licença

Desenvolvido inteiramente por **Bernardo**. O código está aberto para estudos, demonstrações em Feiras de Ciências e evolução para uso de automação residencial e acessibilidade. 
