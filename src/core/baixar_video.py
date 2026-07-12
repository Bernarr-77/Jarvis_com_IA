import yt_dlp

def baixar_audio_youtube(link):
    # Configurações secretas do extrator
    opcoes = {
        'format': 'bestaudio/best', # Pega a melhor qualidade de áudio
        'outtmpl': '%(title)s.%(ext)s', # O nome do ficheiro será o título original do vídeo
        
        # Converte para MP3 automaticamente
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    print("🔍 A procurar o vídeo... Aguarde um momento!")
    
    try:
        # Executa o download
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            ydl.download([link])
        print("\n✅ Áudio descarregado e salvo com sucesso na sua pasta!")
        
    except Exception as erro:
        print(f"\n❌ Ups! Ocorreu um erro: {erro}")

# --- ÁREA DE TESTE ---
print("=== EXTRATOR DE ÁUDIO DO YOUTUBE ===")
url_video = input("Cole o link do vídeo aqui: ")

baixar_audio_youtube(url_video)