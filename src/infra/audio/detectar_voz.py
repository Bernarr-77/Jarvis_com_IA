import speech_recognition as sr

# 1. Cria o "ouvido" do nosso assistente
reconhecedor = sr.Recognizer()

# 2. Liga o microfone
with sr.Microphone() as microfone:
    print("A limpar o ruído de fundo... (silêncio)")
    reconhecedor.adjust_for_ambient_noise(microfone)
    
    print("Pode falar! Diga 'Oi Jarvis'...")
    # O Python fica à espera que você fale
    audio = reconhecedor.listen(microfone)

    print("A processar a voz...")
    
    try:
        # Pede ao Google para traduzir o áudio para texto (em Português)
        texto = reconhecedor.recognize_google(audio, language="pt-PT")
        print(f"O computador ouviu: {texto}")

        # Verifica se a palavra 'jarvis' está no meio do que você disse
        if "jarvis" in texto.lower():
            print("🚀 J.A.R.V.I.S. ATIVADO COM SUCESSO! 🚀")
            # É aqui que depois vamos colocar a música a tocar!
        else:
            print("Ouvi a sua voz, mas não chamou pelo Jarvis.")

    except sr.UnknownValueError:
        print("Não consegui entender o que disse.")
    except sr.RequestError:
        print("Sem ligação à internet para usar o reconhecimento da Google.")