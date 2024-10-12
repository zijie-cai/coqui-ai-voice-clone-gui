import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Canvas
import os
import wave
import sounddevice as sd
import numpy as np
import customtkinter as ctk  # Import customtkinter
from huggingface_hub import InferenceClient
import random
from translate import Translator
import time
from langdetect import detect, detect_langs
from translate import Translator
from os import environ
import re
from google.cloud import translate
import time
from datetime import datetime
import html
from tkinter import PhotoImage
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Canvas
import os
import wave
import sounddevice as sd
import numpy as np
import customtkinter as ctk
import time
from google.cloud import translate
from TTS.api import TTS
import torch
from lingua import LanguageDetectorBuilder, Language
import threading

# Initialize TTS model
device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

language_detector_options = {
    "en": Language.ENGLISH,
    "es": Language.SPANISH,
    "fr": Language.FRENCH,
    "de": Language.GERMAN,
    "it": Language.ITALIAN,
    "pt": Language.PORTUGUESE,
    "pl": Language.POLISH,
    "tr": Language.TURKISH,
    "ru": Language.RUSSIAN,
    "nl": Language.DUTCH,
    "cs": Language.CZECH,
    "ar": Language.ARABIC,
    "zh-cn": Language.CHINESE,
    "ja": Language.JAPANESE,
    "hu": Language.HUNGARIAN,
    "ko": Language.KOREAN,
    "hi": Language.HINDI,
}


# Function to handle speech generation in a separate thread
def generate_speech():
    global filepath, generated_filepath

    # Get the text from the text entry box
    text = text_entry.get("1.0", tk.END).strip()
    if not text:
        messagebox.showinfo("Information", "Please enter some text to speak.")
        return

    if not filepath:
        messagebox.showinfo(
            "Information", "Please upload a speaker WAV file or record one."
        )
        return

    # Show the "Generating..." status
    status_label.config(
        text=interface_text.get("generating", "Generating..."), fg="red"
    )
    status_label.pack(pady=5)

    # Hide the play button if it exists
    if "play_button" in globals() and play_button.winfo_exists():
        play_button.pack_forget()

    # Start a new thread for the TTS generation to avoid blocking the UI
    threading.Thread(target=generate_speech_thread, args=(text,)).start()


# Function to play the generated audio
def play_audio_clone():
    global is_playing_clone

    if generated_filepath and os.path.exists(generated_filepath):
        if not is_playing_clone:
            # Start playing the audio
            with wave.open(generated_filepath, "rb") as wf:
                fs = wf.getframerate()
                data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                sd.play(data, samplerate=fs)
                play_button.configure(text="❚❚")  # Change to pause icon
                is_playing_clone = True
                root.after(100, check_playback_status)
        else:
            # Stop playback
            sd.stop()
            play_button.configure(text="▶")  # Change back to play icon
            is_playing_clone = False


# Function to hide the status message in case of an error
def hide_status():
    status_label.config(text="", fg="black")


# Threaded function to perform the speech generation
def generate_speech_thread(text):
    global filepath, generated_filepath

    # Prepare languages for detection based on your defined options
    languages = [language_detector_options[code] for code in language_options.values()]
    detector = LanguageDetectorBuilder.from_languages(*languages).build()

    # Detect the language of the input text
    try:
        detected_language = detector.detect_language_of(text)
        detected_language_code = detected_language.iso_code_639_1.name.lower()
    except Exception as e:
        root.after(
            0, lambda: messagebox.showerror("Error", f"Failed to detect language: {e}")
        )
        root.after(0, hide_status)
        return

    # Define the output file name
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    output_filename = f"{base_name}_output.wav"
    i = 1
    while os.path.exists(output_filename):
        output_filename = f"{base_name}_output_{i}.wav"
        i += 1

    try:
        # Generate the speech
        tts.tts_to_file(
            text=text,
            speaker_wav=filepath,
            language=detected_language_code,
            file_path=output_filename,
        )

        # Switch back to the main thread to update the UI
        root.after(0, lambda: complete_generation(output_filename))

    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {e}"))
        root.after(0, hide_status)


# Function to handle completion of the generation process
def complete_generation(output_filename):
    global generated_filepath, generated_audio_data

    generated_filepath = output_filename

    # Load the audio data into memory for playback
    with wave.open(generated_filepath, "rb") as wf:
        generated_audio_data = np.frombuffer(
            wf.readframes(wf.getnframes()), dtype=np.int16
        )
        fs = wf.getframerate()  # Get the sample rate from the audio file

    # Remove the status label
    # Update status label to indicate completion
    status_label.config(text="Speech generation completed!", fg="green")

    # Show the play button once the audio is ready
    create_play_button()


# Function to create the play button dynamically if it doesn't already exist
def create_play_button():
    global play_button

    if "play_button" not in globals() or not play_button.winfo_exists():
        # Create a new play button if it doesn't exist
        play_button = ctk.CTkButton(
            main_frame,
            text="▶",  # Start with the play icon
            command=play_audio_clone,
            corner_radius=15,
            fg_color=("lightgray", "dimgray"),
            hover_color=("#bfbfbf", "#4a4a4a"),
            text_color=("black", "white"),
        )

    # Pack the play button to show it in the UI
    play_button.pack(pady=5)


# Global variable for playback state
is_playing_clone = False


# Function to check if the audio playback is finished
def check_playback_status():
    global is_playing_clone

    if not sd.get_stream().active:
        # Playback finished
        play_button.configure(text="▶")  # Change back to play icon
        is_playing_clone = False
    else:
        # Playback still ongoing, check again after 100 ms
        root.after(100, check_playback_status)


PROJECT_ID = environ.get("PROJECT_ID", "tts-ai-434817")

PARENT = f"projects/{PROJECT_ID}"


def translate_text(text: str, target_language_code: str) -> translate.Translation:
    client = translate.TranslationServiceClient()

    response = client.translate_text(
        parent=PARENT,
        contents=[text],
        target_language_code=target_language_code,
    )

    # Return the translated text directly as a plain string without quotes
    return response.translations[0].translated_text.strip()


def detect_language(text: str) -> translate.DetectedLanguage:
    client = translate.TranslationServiceClient()

    response = client.detect_language(parent=PARENT, content=text)

    return response.languages[0]


# Function to handle translation of selected text
def translate_selected_text():
    try:
        selected_text = text_entry.selection_get()  # Get highlighted text
    except tk.TclError:
        messagebox.showinfo("No Selection", "Please select some text to translate.")
        return

    if not selected_text:
        messagebox.showinfo("No Selection", "Please select some text to translate.")
        return

    # Detect the language of the selected text
    detected_language = detect_language(selected_text)
    detected_language_code = detected_language.language_code  # Detected language code

    # Get the selected language for translation
    selected_language = language_var.get()

    interface_lang = translations[selected_language]["languages"]

    target_language = list(interface_lang.keys())[
        list(interface_lang.values()).index(translation_language_var.get())
    ]

    target_language_code = language_options.get(target_language, "en")

    # Perform the translation
    translated_text = translate_text(selected_text, target_language_code)

    translated_text = html.unescape(translated_text)
    # Check the radio button selection (replace or not)
    if replace_translated_text.get():
        # Replace the selected text with the translation
        text_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)  # Remove the selected text
        text_entry.insert(tk.INSERT, translated_text)  # Insert the translated text

    else:
        # Display the translation result in a message box
        messagebox.showinfo(
            "Translation Result",
            f"{selected_text} ({detected_language_code})\n\n ↓ \n\n {translated_text} ({target_language_code})",
        )


# List of random activities
activities = [
    "a daily routine",
    "a workout session",
    "a morning jog",
    "cooking breakfast",
    "walking the dog",
    "an evening yoga session",
    "studying for an exam",
    "cleaning the house",
    "a weekend road trip",
    "attending a meeting",
]

# Language options with language codes
language_options = {
    "English": "en",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Português": "pt",
    "Polski": "pl",
    "Türkçe": "tr",
    "Русский": "ru",
    "Nederlands": "nl",
    "Čeština": "cs",
    "العربية": "ar",
    "中文": "zh-cn",
    "日本語": "ja",
    "Magyar": "hu",
    "한국어": "ko",
    "हिंदी": "hi",
}

# Initialize the Hugging Face Inference Client
client = InferenceClient(
    "HuggingFaceH4/zephyr-7b-beta",
    token="", # replace with your free huggingface user token
)


# Function to generate a complex prompt
def generate_complex_prompt():
    # Randomly choose an activity
    activity = random.choice(activities)

    # Prepare the prompt
    prompt_input = f"Write a sentence about {activity}.Include minimal details and use average vocabulary."

    # Get the response from the Hugging Face API
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt_input}],
        max_tokens=75,
        stream=False,
        # Randomize temperature and top_p each time the function is called
        temperature=random.uniform(0.7, 1.3),  # Random temperature between 0.7 and 1.3
        top_p=random.uniform(0.7, 1.0),  # Random top_p between 0.7 and 1.0
    )

    # Extract and return the generated prompt
    prompt = response.choices[0].message.content
    prompt = ensure_ends_with_period(prompt)

    return prompt


# Ensure the generated prompt ends with a period
def ensure_ends_with_period(prompt):
    last_period_index = prompt.rfind(".")
    if last_period_index != -1:
        prompt = prompt[: last_period_index + 1].strip()
    return prompt


# Function to handle generating a prompt and updating the GUI with translation
def generate_prompt_callback():
    global prompt_textbox
    generated_prompt = generate_complex_prompt()

    # Get the selected language for translation
    selected_language = language_var.get()

    interface_lang = translations[selected_language]["languages"]

    lang = list(interface_lang.keys())[
        list(interface_lang.values()).index(prompt_language_var.get())
    ]

    # Get language code from the options dictionary
    language_code = language_options.get(lang, "en")

    # Use translation if the language is not English
    if language_code != "en":
        # Initialize the Translator
        # translator = Translator(to_lang=language_code)

        translated_prompt = translate_text(
            text=generated_prompt, target_language_code=language_code
        )

        translated_prompt = html.unescape(translated_prompt)

        # Translate the generated prompt
        # translated_prompt = translator.translate(generated_prompt)

        # Update the GUI with the translated prompt
        prompt_text.set(translated_prompt)
    else:
        # No translation needed for English
        prompt_text.set(generated_prompt)

    # Clear the existing text in the textbox and update it with the new prompt
    prompt_textbox.configure(state="normal")  # Set the textbox to normal to modify it
    prompt_textbox.delete("1.0", tk.END)  # Clear previous text
    prompt_textbox.insert(tk.END, prompt_text.get())  # Insert new prompt
    prompt_textbox.configure(state="disabled")  # Disable editing after update


translations = {
    "English": {
        "title": "Coqui AI TTS GUI",
        "enter_text": "Enter Text:",
        "no_file_selected": "No file selected",
        "upload_wav_file": "Upload WAV File",
        "record_wav_file": "Record WAV File",
        "generate_speech": "Generate Speech",
        "select_prompt_language": "Select Prompt Language:",
        "recording_options": "Recording Options",
        "generate_prompt": "Generate Prompt",
        "dark_mode": "Dark Mode",
        "ai_writer": "AI Writer 📝",
        "highlight_translate": "Highlight and Translate:",
        "with_replacement": "With replacement",
        "without_replacement": "Without replacement",
        "recording_list": "Recording List:",
        "generating": "Generating...",
        "languages": {
            "English": "English",
            "Español": "Spanish",
            "Français": "French",
            "Deutsch": "German",
            "Italiano": "Italian",
            "Português": "Portuguese",
            "Polski": "Polish",
            "Türkçe": "Turkish",
            "Русский": "Russian",
            "Nederlands": "Dutch",
            "Čeština": "Czech",
            "العربية": "Arabic",
            "中文": "Chinese",
            "日本語": "Japanese",
            "Magyar": "Hungarian",
            "한국어": "Korean",
            "हिंदी": "Hindi",
        },
    },
    "Español": {
        "title": "Interfaz de Coqui AI TTS",
        "enter_text": "Ingresar texto:",
        "no_file_selected": "Ningún archivo seleccionado",
        "upload_wav_file": "Subir archivo WAV",
        "record_wav_file": "Grabar archivo WAV",
        "generate_speech": "Generar Voz",
        "select_prompt_language": "Seleccionar idioma:",
        "recording_options": "Opciones de Grabación",
        "generate_prompt": "Generar Pregunta",
        "dark_mode": "Modo Oscuro",
        "ai_writer": "Escritor AI 📝",
        "highlight_translate": "Resaltar y Traducir:",
        "with_replacement": "Con reemplazo",
        "without_replacement": "Sin reemplazo",
        "recording_list": "Lista de Grabaciones:",
        "generating": "Generando...",
        "languages": {
            "English": "Inglés",
            "Español": "Español",
            "Français": "Francés",
            "Deutsch": "Alemán",
            "Italiano": "Italiano",
            "Português": "Portugués",
            "Polski": "Polaco",
            "Türkçe": "Turco",
            "Русский": "Ruso",
            "Nederlands": "Holandés",
            "Čeština": "Checo",
            "العربية": "Árabe",
            "中文": "Chino",
            "日本語": "Japonés",
            "Magyar": "Húngaro",
            "한국어": "Coreano",
            "हिंदी": "Hindi",
        },
    },
    "Français": {
        "title": "Interface de Coqui AI TTS",
        "enter_text": "Entrez du texte:",
        "no_file_selected": "Aucun fichier sélectionné",
        "upload_wav_file": "Télécharger un fichier WAV",
        "record_wav_file": "Enregistrer un fichier WAV",
        "generate_speech": "Générer la parole",
        "select_prompt_language": "Sélectionner la langue:",
        "recording_options": "Options d'enregistrement",
        "generate_prompt": "Générer une question",
        "dark_mode": "Mode Sombre",
        "ai_writer": "Écrivain IA 📝",
        "highlight_translate": "Surligner et Traduire:",
        "with_replacement": "Avec remplacement",
        "without_replacement": "Sans remplacement",
        "recording_list": "Liste des Enregistrements:",
        "generating": "Génération en cours...",
        "languages": {
            "English": "Anglais",
            "Español": "Espagnol",
            "Français": "Français",
            "Deutsch": "Allemand",
            "Italiano": "Italien",
            "Português": "Portugais",
            "Polski": "Polonais",
            "Türkçe": "Turc",
            "Русский": "Russe",
            "Nederlands": "Néerlandais",
            "Čeština": "Tchèque",
            "العربية": "Arabe",
            "中文": "Chinois",
            "日本語": "Japonais",
            "Magyar": "Hongrois",
            "한국어": "Coréen",
            "हिंदी": "Hindi",
        },
    },
    "Deutsch": {
        "title": "Coqui AI TTS Benutzeroberfläche",
        "enter_text": "Text eingeben:",
        "no_file_selected": "Keine Datei ausgewählt",
        "upload_wav_file": "WAV-Datei hochladen",
        "record_wav_file": "WAV-Datei aufnehmen",
        "generate_speech": "Sprache generieren",
        "select_prompt_language": "Sprache auswählen:",
        "recording_options": "Aufnahmeoptionen",
        "generate_prompt": "Frage generieren",
        "dark_mode": "Dunkelmodus",
        "ai_writer": "KI-Schreiber 📝",
        "highlight_translate": "Markieren und Übersetzen:",
        "with_replacement": "Mit Ersetzung",
        "without_replacement": "Ohne Ersetzung",
        "recording_list": "Aufnahmeliste:",
        "generating": "Generieren...",
        "languages": {
            "English": "Englisch",
            "Español": "Spanisch",
            "Français": "Französisch",
            "Deutsch": "Deutsch",
            "Italiano": "Italienisch",
            "Português": "Portugiesisch",
            "Polski": "Polnisch",
            "Türkçe": "Türkisch",
            "Русский": "Russisch",
            "Nederlands": "Niederländisch",
            "Čeština": "Tschechisch",
            "العربية": "Arabisch",
            "中文": "Chinesisch",
            "日本語": "Japanisch",
            "Magyar": "Ungarisch",
            "한국어": "Koreanisch",
            "हिंदी": "Hindi",
        },
    },
    "Italiano": {
        "title": "Interfaccia di Coqui AI TTS",
        "enter_text": "Inserisci testo:",
        "no_file_selected": "Nessun file selezionato",
        "upload_wav_file": "Carica file WAV",
        "record_wav_file": "Registra file WAV",
        "generate_speech": "Genera Voce",
        "select_prompt_language": "Seleziona lingua:",
        "recording_options": "Opzioni di registrazione",
        "generate_prompt": "Genera Domanda",
        "dark_mode": "Modalità Scura",
        "ai_writer": "Scrittore AI 📝",
        "highlight_translate": "Evidenzia e Traduci:",
        "with_replacement": "Con sostituzione",
        "without_replacement": "Senza sostituzione",
        "recording_list": "Elenco delle Registrazioni:",
        "generating": "Generazione in corso...",
        "languages": {
            "English": "Inglese",
            "Español": "Spagnolo",
            "Français": "Francese",
            "Deutsch": "Tedesco",
            "Italiano": "Italiano",
            "Português": "Portoghese",
            "Polski": "Polacco",
            "Türkçe": "Turco",
            "Русский": "Russo",
            "Nederlands": "Olandese",
            "Čeština": "Ceco",
            "العربية": "Arabo",
            "中文": "Cinese",
            "日本語": "Giapponese",
            "Magyar": "Ungherese",
            "한국어": "Coreano",
            "हिंदी": "Hindi",
        },
    },
    "Português": {
        "title": "Interface Coqui AI TTS",
        "enter_text": "Digite o texto:",
        "no_file_selected": "Nenhum arquivo selecionado",
        "upload_wav_file": "Enviar arquivo WAV",
        "record_wav_file": "Gravar arquivo WAV",
        "generate_speech": "Gerar Fala",
        "select_prompt_language": "Selecione o idioma:",
        "recording_options": "Opções de Gravação",
        "generate_prompt": "Gerar Pergunta",
        "dark_mode": "Modo Escuro",
        "ai_writer": "Escritor AI 📝",
        "highlight_translate": "Destaque e Traduza:",
        "with_replacement": "Com substituição",
        "without_replacement": "Sem substituição",
        "recording_list": "Lista de Gravações:",
        "generating": "Gerando...",
        "languages": {
            "English": "Inglês",
            "Español": "Espanhol",
            "Français": "Francês",
            "Deutsch": "Alemão",
            "Italiano": "Italiano",
            "Português": "Português",
            "Polski": "Polonês",
            "Türkçe": "Turco",
            "Русский": "Russo",
            "Nederlands": "Holandês",
            "Čeština": "Tcheco",
            "العربية": "Árabe",
            "中文": "Chinês",
            "日本語": "Japonês",
            "Magyar": "Húngaro",
            "한국어": "Coreano",
            "हिंदी": "Hindi",
        },
    },
    "Polski": {
        "title": "Interfejs Coqui AI TTS",
        "enter_text": "Wpisz tekst:",
        "no_file_selected": "Nie wybrano pliku",
        "upload_wav_file": "Prześlij plik WAV",
        "record_wav_file": "Nagraj plik WAV",
        "generate_speech": "Generuj Mowę",
        "select_prompt_language": "Wybierz język:",
        "recording_options": "Opcje nagrywania",
        "generate_prompt": "Generuj pytanie",
        "dark_mode": "Tryb Ciemny",
        "ai_writer": "Pisarz AI 📝",
        "highlight_translate": "Zaznacz i Przetłumacz:",
        "with_replacement": "Z zamianą",
        "without_replacement": "Bez zamiany",
        "recording_list": "Lista Nagrań:",
        "generating": "Generowanie...",
        "languages": {
            "English": "Angielski",
            "Español": "Hiszpański",
            "Français": "Francuski",
            "Deutsch": "Niemiecki",
            "Italiano": "Włoski",
            "Português": "Portugalski",
            "Polski": "Polski",
            "Türkçe": "Turecki",
            "Русский": "Rosyjski",
            "Nederlands": "Holenderski",
            "Čeština": "Czeski",
            "العربية": "Arabski",
            "中文": "Chiński",
            "日本語": "Japoński",
            "Magyar": "Węgierski",
            "한국어": "Koreański",
            "हिंदी": "Hindi",
        },
    },
    "Türkçe": {
        "title": "Coqui AI TTS Arayüzü",
        "enter_text": "Metni girin:",
        "no_file_selected": "Dosya seçilmedi",
        "upload_wav_file": "WAV Dosyasını Yükle",
        "record_wav_file": "WAV Dosyası Kaydet",
        "generate_speech": "Konuşma Üret",
        "select_prompt_language": "Dil Seçin:",
        "recording_options": "Kayıt Seçenekleri",
        "generate_prompt": "Soru Üret",
        "dark_mode": "Karanlık Mod",
        "ai_writer": "AI Yazar 📝",
        "highlight_translate": "Vurgula ve Çevir:",
        "with_replacement": "Değiştirerek",
        "without_replacement": "Değiştirmeden",
        "recording_list": "Kayıt Listesi:",
        "generating": "Oluşturuluyor...",
        "languages": {
            "English": "İngilizce",
            "Español": "İspanyolca",
            "Français": "Fransızca",
            "Deutsch": "Almanca",
            "Italiano": "İtalyanca",
            "Português": "Portekizce",
            "Polski": "Lehçe",
            "Türkçe": "Türkçe",
            "Русский": "Rusça",
            "Nederlands": "Flemenkçe",
            "Čeština": "Çekçe",
            "العربية": "Arapça",
            "中文": "Çince",
            "日本語": "Japonca",
            "Magyar": "Macarca",
            "한국어": "Korece",
            "हिंदी": "Hintçe",
        },
    },
    "Русский": {
        "title": "Интерфейс Coqui AI TTS",
        "enter_text": "Введите текст:",
        "no_file_selected": "Файл не выбран",
        "upload_wav_file": "Загрузить файл WAV",
        "record_wav_file": "Записать файл WAV",
        "generate_speech": "Создать речь",
        "select_prompt_language": "Выберите язык:",
        "recording_options": "Параметры записи",
        "generate_prompt": "Сгенерировать вопрос",
        "dark_mode": "Темный режим",
        "ai_writer": "Писатель ИИ 📝",
        "highlight_translate": "Выделить и Перевести:",
        "with_replacement": "С заменой",
        "without_replacement": "Без замены",
        "recording_list": "Список Записей:",
        "generating": "Создание...",
        "languages": {
            "English": "Английский",
            "Español": "Испанский",
            "Français": "Французский",
            "Deutsch": "Немецкий",
            "Italiano": "Итальянский",
            "Português": "Португальский",
            "Polski": "Польский",
            "Türkçe": "Турецкий",
            "Русский": "Русский",
            "Nederlands": "Голландский",
            "Čeština": "Чешский",
            "العربية": "Арабский",
            "中文": "Китайский",
            "日本語": "Японский",
            "Magyar": "Венгерский",
            "한국어": "Корейский",
            "हिंदी": "Хинди",
        },
    },
    "Nederlands": {
        "title": "Coqui AI TTS Interface",
        "enter_text": "Voer tekst in:",
        "no_file_selected": "Geen bestand geselecteerd",
        "upload_wav_file": "WAV-bestand uploaden",
        "record_wav_file": "WAV-bestand opnemen",
        "generate_speech": "Spraak genereren",
        "select_prompt_language": "Selecteer taal:",
        "recording_options": "Opnameopties",
        "generate_prompt": "Vraag genereren",
        "dark_mode": "Donkere modus",
        "ai_writer": "AI Schrijver 📝",
        "highlight_translate": "Markeer en Vertaal:",
        "with_replacement": "Met vervanging",
        "without_replacement": "Zonder vervanging",
        "recording_list": "Opnamelijst:",
        "generating": "Bezig met genereren...",
        "languages": {
            "English": "Engels",
            "Español": "Spaans",
            "Français": "Frans",
            "Deutsch": "Duits",
            "Italiano": "Italiaans",
            "Português": "Portugees",
            "Polski": "Pools",
            "Türkçe": "Turks",
            "Русский": "Russisch",
            "Nederlands": "Nederlands",
            "Čeština": "Tsjechisch",
            "العربية": "Arabisch",
            "中文": "Chinees",
            "日本語": "Japans",
            "Magyar": "Hongaars",
            "한국어": "Koreaans",
            "हिंदी": "Hindi",
        },
    },
    "Čeština": {
        "title": "Rozhraní Coqui AI TTS",
        "enter_text": "Zadejte text:",
        "no_file_selected": "Nebyl vybrán žádný soubor",
        "upload_wav_file": "Nahrát soubor WAV",
        "record_wav_file": "Nahrát soubor WAV",
        "generate_speech": "Generovat řeč",
        "select_prompt_language": "Vyberte jazyk:",
        "recording_options": "Možnosti nahrávání",
        "generate_prompt": "Generovat otázku",
        "dark_mode": "Tmavý režim",
        "ai_writer": "AI Psaní 📝",
        "highlight_translate": "Zvýraznit a Přeložit:",
        "with_replacement": "S výměnou",
        "without_replacement": "Bez výměny",
        "recording_list": "Seznam Nahrávek:",
        "generating": "Generování...",
        "languages": {
            "English": "Angličtina",
            "Español": "Španělština",
            "Français": "Francouzština",
            "Deutsch": "Němčina",
            "Italiano": "Italština",
            "Português": "Portugalština",
            "Polski": "Polština",
            "Türkçe": "Turečtina",
            "Русский": "Ruština",
            "Nederlands": "Nizozemština",
            "Čeština": "Čeština",
            "العربية": "Arabština",
            "中文": "Čínština",
            "日本語": "Japonština",
            "Magyar": "Maďarština",
            "한국어": "Korejština",
            "हिंदी": "Hindština",
        },
    },
    "العربية": {
        "title": "واجهة Coqui AI TTS",
        "enter_text": "أدخل النص:",
        "no_file_selected": "لم يتم اختيار ملف",
        "upload_wav_file": "تحميل ملف WAV",
        "record_wav_file": "تسجيل ملف WAV",
        "generate_speech": "توليد الكلام",
        "select_prompt_language": "اختر اللغة:",
        "recording_options": "خيارات التسجيل",
        "generate_prompt": "توليد السؤال",
        "dark_mode": "الوضع الداكن",
        "ai_writer": "الكاتب الذكاء الاصطناعي 📝",
        "highlight_translate": "تحديد النص وترجمته:",
        "with_replacement": "مع الاستبدال",
        "without_replacement": "بدون استبدال",
        "recording_list": "قائمة التسجيلات:",
        "generating": "جارٍ التوليد...",
        "languages": {
            "English": "الإنجليزية",
            "Español": "الإسبانية",
            "Français": "الفرنسية",
            "Deutsch": "الألمانية",
            "Italiano": "الإيطالية",
            "Português": "البرتغالية",
            "Polski": "البولندية",
            "Türkçe": "التركية",
            "Русский": "الروسية",
            "Nederlands": "الهولندية",
            "Čeština": "التشيكية",
            "العربية": "العربية",
            "中文": "الصينية",
            "日本語": "اليابانية",
            "Magyar": "المجرية",
            "한국어": "الكورية",
            "हिंदी": "الهندية",
        },
    },
    "中文": {
        "title": "Coqui AI TTS 界面",
        "enter_text": "输入文本:",
        "no_file_selected": "未选择文件",
        "upload_wav_file": "上传 WAV 文件",
        "record_wav_file": "录制 WAV 文件",
        "generate_speech": "生成语音",
        "select_prompt_language": "选择语言:",
        "recording_options": "录音选项",
        "generate_prompt": "生成问题",
        "dark_mode": "深色模式",
        "ai_writer": "AI 作家 📝",
        "highlight_translate": "突出并翻译:",
        "with_replacement": "带替换",
        "without_replacement": "不替换",
        "recording_list": "录音列表:",
        "generating": "生成中...",
        "languages": {
            "English": "英语",
            "Español": "西班牙语",
            "Français": "法语",
            "Deutsch": "德语",
            "Italiano": "意大利语",
            "Português": "葡萄牙语",
            "Polski": "波兰语",
            "Türkçe": "土耳其语",
            "Русский": "俄语",
            "Nederlands": "荷兰语",
            "Čeština": "捷克语",
            "العربية": "阿拉伯语",
            "中文": "中文",
            "日本語": "日语",
            "Magyar": "匈牙利语",
            "한국어": "韩语",
            "हिंदी": "印地语",
        },
    },
    "日本語": {
        "title": "Coqui AI TTS インターフェース",
        "enter_text": "テキストを入力:",
        "no_file_selected": "ファイルが選択されていません",
        "upload_wav_file": "WAVファイルをアップロード",
        "record_wav_file": "WAVファイルを録音",
        "generate_speech": "音声を生成",
        "select_prompt_language": "言語を選択:",
        "recording_options": "録音オプション",
        "generate_prompt": "質問を生成",
        "dark_mode": "ダークモード",
        "ai_writer": "AI ライター 📝",
        "highlight_translate": "ハイライトして翻訳:",
        "with_replacement": "置換付き",
        "without_replacement": "置換なし",
        "recording_list": "録音リスト:",
        "generating": "生成中...",
        "languages": {
            "English": "英語",
            "Español": "スペイン語",
            "Français": "フランス語",
            "Deutsch": "ドイツ語",
            "Italiano": "イタリア語",
            "Português": "ポルトガル語",
            "Polski": "ポーランド語",
            "Türkçe": "トルコ語",
            "Русский": "ロシア語",
            "Nederlands": "オランダ語",
            "Čeština": "チェコ語",
            "العربية": "アラビア語",
            "中文": "中国語",
            "日本語": "日本語",
            "Magyar": "ハンガリー語",
            "한국어": "韓国語",
            "हिंदी": "ヒンディー語",
        },
    },
    "Magyar": {
        "title": "Coqui AI TTS Felület",
        "enter_text": "Írja be a szöveget:",
        "no_file_selected": "Nincs kiválasztva fájl",
        "upload_wav_file": "WAV fájl feltöltése",
        "record_wav_file": "WAV fájl felvétele",
        "generate_speech": "Beszéd létrehozása",
        "select_prompt_language": "Nyelv kiválasztása:",
        "recording_options": "Felvételi lehetőségek",
        "generate_prompt": "Kérdés létrehozása",
        "dark_mode": "Sötét mód",
        "ai_writer": "AI Író 📝",
        "highlight_translate": "Kiemelés és Fordítás:",
        "with_replacement": "Cserével",
        "without_replacement": "Csere nélkül",
        "recording_list": "Felvételi Lista:",
        "generating": "Generálás folyamatban...",
        "languages": {
            "English": "Angol",
            "Español": "Spanyol",
            "Français": "Francia",
            "Deutsch": "Német",
            "Italiano": "Olasz",
            "Português": "Portugál",
            "Polski": "Lengyel",
            "Türkçe": "Török",
            "Русский": "Orosz",
            "Nederlands": "Holland",
            "Čeština": "Cseh",
            "العربية": "Arab",
            "中文": "Kínai",
            "日本語": "Japán",
            "Magyar": "Magyar",
            "한국어": "Koreai",
            "हिंदी": "Hindi",
        },
    },
    "한국어": {
        "title": "Coqui AI TTS 인터페이스",
        "enter_text": "텍스트 입력:",
        "no_file_selected": "파일이 선택되지 않음",
        "upload_wav_file": "WAV 파일 업로드",
        "record_wav_file": "WAV 파일 녹음",
        "generate_speech": "음성 생성",
        "select_prompt_language": "언어 선택:",
        "recording_options": "녹음 옵션",
        "generate_prompt": "질문 생성",
        "dark_mode": "어두운 모드",
        "ai_writer": "AI 작가 📝",
        "highlight_translate": "강조하고 번역:",
        "with_replacement": "대체로",
        "without_replacement": "대체 없이",
        "recording_list": "녹음 목록:",
        "generating": "생성 중...",
        "languages": {
            "English": "영어",
            "Español": "스페인어",
            "Français": "프랑스어",
            "Deutsch": "독일어",
            "Italiano": "이탈리아어",
            "Português": "포르투갈어",
            "Polski": "폴란드어",
            "Türkçe": "터키어",
            "Русский": "러시아어",
            "Nederlands": "네덜란드어",
            "Čeština": "체코어",
            "العربية": "아랍어",
            "中文": "중국어",
            "日本語": "일본어",
            "Magyar": "헝가리어",
            "한국어": "한국어",
            "हिंदी": "힌디어",
        },
    },
    "हिंदी": {
        "title": "Coqui AI TTS इंटरफ़ेस",
        "enter_text": "पाठ दर्ज करें:",
        "no_file_selected": "कोई फ़ाइल चयनित नहीं की गई",
        "upload_wav_file": "WAV फ़ाइल अपलोड करें",
        "record_wav_file": "WAV फ़ाइल रिकॉर्ड करें",
        "generate_speech": "वाणी उत्पन्न करें",
        "select_prompt_language": "भाषा चुनें:",
        "recording_options": "रिकॉर्डिंग विकल्प",
        "generate_prompt": "प्रश्न उत्पन्न करें",
        "dark_mode": "डार्क मोड",
        "ai_writer": "AI लेखक 📝",
        "highlight_translate": "हाइलाइट करें और अनुवाद करें:",
        "with_replacement": "प्रतिस्थापन के साथ",
        "without_replacement": "बिना प्रतिस्थापन",
        "recording_list": "रिकॉर्डिंग सूची:",
        "generating": "उत्पन्न हो रहा है...",
        "languages": {
            "English": "अंग्रेज़ी",
            "Español": "स्पेनिश",
            "Français": "फ्रेंच",
            "Deutsch": "जर्मन",
            "Italiano": "इतालवी",
            "Português": "पुर्तगाली",
            "Polski": "पोलिश",
            "Türkçe": "तुर्की",
            "Русский": "रूसी",
            "Nederlands": "डच",
            "Čeština": "चेक",
            "العربية": "अरबी",
            "中文": "चीनी",
            "日本語": "जापानी",
            "Magyar": "हंगेरियन",
            "한국어": "कोरियाई",
            "हिंदी": "हिंदी",
        },
    },
}

# Global variable for colors and canvas
current_colors = {}
record_shape = None


def update_circle_button_colors():
    global current_colors
    dark_mode_colors = {
        "default": "dimgray",
        "hover": "#4a4a4a",
        "recording": "red",
        "recording_hover": "#b22222",
        "border": "white",  # White border for dark mode
    }
    light_mode_colors = {
        "default": "lightgray",
        "hover": "#bfbfbf",
        "recording": "red",
        "recording_hover": "#b22222",
        "border": "black",  # Black border for light mode
    }

    # Choose colors based on current mode
    if ctk.get_appearance_mode() == "Dark":
        current_colors = dark_mode_colors
    else:
        current_colors = light_mode_colors

    # Check if the canvas and record_shape exist before attempting to update them
    if "canvas" in globals() and "record_shape" in globals():
        try:
            if canvas.winfo_exists():
                # Update the fill color
                canvas.itemconfig(record_shape, fill=current_colors["default"])
                # Update the outline (border) color
                canvas.itemconfig(
                    record_shape, outline=current_colors["border"], width=1
                )
        except Exception as e:
            print(f"Error updating recording circle color: {e}")


def update_language(selected_language):
    global interface_text, recording_list_label
    interface_text = translations[selected_language]
    # Update the main window title based on selected language
    root.title(interface_text["title"])

    # Update main window
    text_label.config(text=interface_text["enter_text"])
    file_label.config(text=interface_text["no_file_selected"])
    upload_button.configure(text=interface_text["upload_wav_file"])
    record_button.configure(text=interface_text["record_wav_file"])
    generate_button.configure(text=interface_text["generate_speech"])
    ai_writer_button.configure(text=interface_text["ai_writer"])
    theme_switch.configure(
        text=interface_text["dark_mode"]
    )  # Update dark mode switch text

    if "recording_list_label" in globals() and recording_list_label.winfo_exists():
        recording_list_label.configure(text=interface_text["recording_list"])
    # Update the "Highlight and Translate" label
    highlight_label.config(
        text=interface_text.get("highlight_translate", "Highlight and Translate:")
    )

    # Update the radio buttons
    replace_radiobutton.config(
        text=interface_text.get("with_replacement", "With replacement")
    )
    no_replace_radiobutton.config(
        text=interface_text.get("without_replacement", "Without replacement")
    )

    # Update translation language option menu
    translated_languages = [
        interface_text["languages"][lang] for lang in language_options
    ]
    trans_language_option_menu.configure(values=translated_languages)

    translation_language_var.set(interface_text["languages"][selected_language])

    # Update the status label if it shows the "generating" message
    current_status = status_label.cget("text")
    if "generating" in current_status.lower():
        generating_text = interface_text.get("generating", "Generating...")
        status_label.config(text=generating_text)

    # Update recording window language if open
    if "recording_window" in globals() and recording_window.winfo_exists():
        # Update the title and prompt label
        recording_window.title(interface_text["recording_options"])
        prompt_label.config(text=interface_text["select_prompt_language"])

        prompt_language_var.set(interface_text["languages"][selected_language])

        # Update the text of the generate prompt button
        generate_prompt_button.configure(text=interface_text["generate_prompt"])

        option_menu.configure(values=translated_languages)

        # Update the dynamic prompt text to match the current language
        update_prompt_text(selected_language)

        # Update the textbox with the newly translated prompt text
        prompt_textbox.configure(state="normal")
        prompt_textbox.delete("1.0", tk.END)
        prompt_textbox.insert(tk.END, prompt_text.get())
        # Apply the center tag to center the text
        prompt_textbox.tag_config("center", justify="center")
        prompt_textbox.tag_add("center", "1.0", "end")

        prompt_textbox.configure(state="disabled")


def update_prompt_text(selected_language):

    # Dictionary for the prompt text in different languages
    prompt_translations = {
        "English": "Follow the received prompt to start recording.",
        "Español": "Siga el aviso recibido para comenzar a grabar.",
        "Français": "Suivez l'invite reçue pour commencer l'enregistrement.",
        "Deutsch": "Folgen Sie der erhaltenen Aufforderung, um die Aufnahme zu starten.",
        "Italiano": "Segui il prompt ricevuto per avviare la registrazione.",
        "Português": "Siga o aviso recebido para iniciar a gravação.",
        "Polski": "Postępuj zgodnie z otrzymanym poleceniem, aby rozpocząć nagrywanie.",
        "Türkçe": "Kaydı başlatmak için alınan talimatı izleyin.",
        "Русский": "Следуйте полученной подсказке, чтобы начать запись.",
        "Nederlands": "Volg de ontvangen prompt om te beginnen met opnemen.",
        "Čeština": "Postupujte podle přijaté výzvy, abyste zahájili nahrávání.",
        "العربية": "اتبع الإرشاد المستلم لبدء التسجيل.",
        "中文": "请按照收到的提示开始录音。",
        "日本語": "受け取ったプロンプトに従って録音を開始してください。",
        "Magyar": "Kövesse a kapott utasítást a felvétel megkezdéséhez.",
        "한국어": "수신된 프롬프트를 따라 녹음을 시작하세요.",
        "हिंदी": "रिकॉर्डिंग शुरू करने के लिए प्राप्त संकेत का पालन करें।",
    }

    # Set the prompt_text based on the selected language
    prompt_text.set(
        prompt_translations.get(
            selected_language, "Feel free to follow the received prompt to read aloud."
        )
    )


def open_file():
    global filepath
    file = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if file:
        filepath = file
        file_label.config(text=os.path.basename(file))


def open_recording_window():
    global button_frame, container, delete_button, bottom_frame, custom_list_frame, recording_window, prompt_label, generate_prompt_button, record_shape, canvas, option_menu, prompt_language_var, prompt_text, timer_label, start_time, play_button, prompt_textbox, recording_list_label

    recording_window = Toplevel(root)
    recording_window.title(interface_text["recording_options"])
    recording_window.geometry("400x550")  # Set the same size as the main window

    recording_window.configure(bg="#2b2b2b")
    container = tk.Frame(recording_window, bg="#2b2b2b")
    container.pack(expand=True, fill=tk.BOTH, padx=8, pady=8)

    prompt_language_var = tk.StringVar(recording_window)

    prompt_language_var.set(
        interface_text["languages"]["English"]
    )  # Set a default value

    prompt_label = tk.Label(
        container, text=interface_text["select_prompt_language"], bg="#2b2b2b"
    )
    prompt_label.pack(pady=4)

    # Update the language options in the dropdown to be displayed in the selected interface language
    translated_languages = [
        interface_text["languages"][lang] for lang in language_options
    ]

    option_menu = ctk.CTkOptionMenu(
        container,
        values=translated_languages,  # Use the keys from the dictionary
        variable=prompt_language_var,
        fg_color=("lightgray", "dimgray"),  # Light and dark mode colors
        button_color=("lightgray", "dimgray"),
        button_hover_color=("#bfbfbf", "#4a4a4a"),
        dropdown_fg_color=("lightgray", "dimgray"),
        dropdown_hover_color=("#bfbfbf", "#4a4a4a"),
        dropdown_text_color=("black", "white"),  # Text colors for light/dark mode
        text_color=("black", "white"),  # Text colors for selected option
        corner_radius=10,  # Rounded corners for smooth, modern look
    )
    option_menu.pack(pady=4)

    generate_prompt_button = ctk.CTkButton(
        container,
        text=interface_text["generate_prompt"],
        command=generate_prompt_callback,  # Hooked up to the generate_complex_prompt function
        corner_radius=15,
        fg_color=("lightgray", "dimgray"),
        hover_color=("#bfbfbf", "#4a4a4a"),
        text_color=("black", "white"),
    )
    generate_prompt_button.pack(pady=8)

    # Initialize the prompt_text based on the selected language
    prompt_text = tk.StringVar()

    update_prompt_text(language_var.get())

    # Create the Text widget to display the prompt text with default "Prompt Text"
    prompt_textbox = ctk.CTkTextbox(
        container,
        height=120,  # Adjust height as needed
        width=340,  # Adjust width as needed
        corner_radius=10,  # Smooth, modern look
        fg_color="transparent",  # Transparent background
        text_color="white",  # Adjust text color for dark mode (adjust as needed)
        state="normal",  # Initially set to normal to insert text
        wrap="word",  # Handle word wrapping
    )

    # Insert the default text from prompt_text (StringVar)
    prompt_textbox.insert(tk.END, prompt_text.get())

    # Apply the center tag to center the text
    prompt_textbox.tag_config("center", justify="center")
    prompt_textbox.tag_add("center", "1.0", "end")

    # Make sure the user can select the text for copy and paste but not edit it
    prompt_textbox.configure(state="disabled")
    prompt_textbox.pack(pady=0)

    # Create a frame at the bottom for the timer and circle button
    bottom_frame = tk.Frame(container, bg="#2b2b2b")
    bottom_frame.pack(side=tk.BOTTOM, pady=0)

    # Add a label for the recording list frame
    recording_list_label = tk.Label(
        bottom_frame, text=interface_text["recording_list"], bg="#2b2b2b"
    )
    recording_list_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5)

    # Create a scrollable frame for recordings
    custom_list_frame = ctk.CTkScrollableFrame(
        bottom_frame,
        width=320,
        height=100,
        corner_radius=10,
        fg_color=("lightgray", "dimgray"),
        scrollbar_button_color=("dimgray", "lightgrey"),
        scrollbar_button_hover_color=("#4a4a4a", "#bfbfbf"),
    )
    custom_list_frame._scrollbar.configure(height=0)
    custom_list_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=5)

    update_recordings_list()  # Load initial data into the scrollable custom listbox
    # Create a frame to hold the buttons
    button_frame = tk.Frame(bottom_frame, bg="#2b2b2b")
    button_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

    # Create the Upload button
    upload_button = ctk.CTkButton(
        button_frame,
        text="⬆",
        command=upload_recording,
        font=("Helvetica", 16),
        corner_radius=15,
        fg_color=("lightgray", "dimgray"),
        hover_color=("#bfbfbf", "#4a4a4a"),
        text_color=("black", "white"),
        width=80,
        height=20,
    )
    upload_button.pack(side="left", expand=True, pady=10)

    # Create the Play button
    play_button = ctk.CTkButton(
        button_frame,
        text="▶",
        command=play_audio,
        font=("Helvetica", 16),
        corner_radius=15,
        fg_color=("lightgray", "dimgray"),
        hover_color=("#bfbfbf", "#4a4a4a"),
        text_color=("black", "white"),
        width=80,
        height=20,
    )
    play_button.pack(side="left", expand=True, pady=10)

    # Create the Delete button
    delete_button = ctk.CTkButton(
        button_frame,
        text="✖",
        command=delete_selected_recordings,
        font=("Helvetica", 16),
        corner_radius=15,
        fg_color=("lightgray", "dimgray"),
        hover_color=("#bfbfbf", "#4a4a4a"),
        text_color=("black", "white"),
        width=80,
        height=20,
    )
    delete_button.pack(side="left", expand=True, pady=10)
    # Create a smaller CTkLabel for the timer
    timer_label = ctk.CTkLabel(
        bottom_frame,
        text="00:00:00",
        font=("Helvetica", 16),  # Smaller font size for a more compact display
        fg_color="transparent",  # Transparent background by default
        text_color="white",  # White text color for the timer
        corner_radius=5,  # Rounded corners for the label
        width=75,  # Width of the timer label
        height=30,  # Height of the timer label
    )
    timer_label.grid(
        row=3, column=0, columnspan=2, pady=0
    )  # Position right above the circle button

    # Create a canvas for the recording button (circle) in the bottom frame
    canvas = Canvas(
        bottom_frame, width=60, height=60, bg="#2b2b2b", highlightthickness=0
    )
    canvas.grid(
        row=4, column=0, columnspan=2, padx=(0, 2), pady=0
    )  # Place the canvas below the timer

    update_circle_button_colors()  # Set the initial colors based on current mode

    record_shape = canvas.create_oval(10, 10, 50, 50, fill=current_colors["default"])

    def on_enter(event):
        if record_state:
            canvas.itemconfig(
                record_shape, fill=current_colors["recording_hover"]
            )  # Darker red when hovering during recording
        else:
            canvas.itemconfig(
                record_shape, fill=current_colors["hover"]
            )  # Hover color when not recording

    def on_leave(event):
        if record_state:
            canvas.itemconfig(
                record_shape, fill=current_colors["recording"]
            )  # Return to red when not hovering during recording
        else:
            canvas.itemconfig(
                record_shape, fill=current_colors["default"]
            )  # Return to default when not hovering in non-recording state

    # Bind hover events
    canvas.tag_bind(record_shape, "<Enter>", on_enter)
    canvas.tag_bind(record_shape, "<Leave>", on_leave)

    canvas.tag_bind(record_shape, "<Button-1>", lambda x: toggle_recording())

    update_ui_colors()  # Apply the current theme's colors to the new window


# Global variables for playback state
is_playing = False
playback_position = 0


def upload_recording():
    global filepath, audio_data
    selected_indices = [idx for idx, selected in selected_labels.items() if selected]

    if not selected_indices:
        messagebox.showwarning("Warning", "No recording selected to upload.")
        return

    uploaded_files_count = 0
    for selected_idx in selected_indices:
        selected_recording = recordings[selected_idx - 1]

        if "audio_data" in selected_recording:
            audio_data = selected_recording["audio_data"]
        else:
            # Read the WAV file to ensure it's uploaded correctly
            with wave.open(selected_recording["filepath"], "rb") as wf:
                audio_data = np.frombuffer(
                    wf.readframes(wf.getnframes()), dtype=np.int16
                )

        # Save or update the file path
        if not selected_recording.get("filepath"):
            filename = f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            save_wav_file(filename, audio_data, fs)
            selected_recording["filepath"] = filename

        filepath = selected_recording["filepath"]
        uploaded_files_count += 1

    file_label.config(text=f"{uploaded_files_count} file(s) uploaded")
    messagebox.showinfo(
        "Success", f"{uploaded_files_count} file(s) uploaded successfully."
    )


def delete_selected_recordings():
    global recordings

    # Identify selected recordings
    selected_indices = [idx for idx, selected in selected_labels.items() if selected]

    # Error handling if no recordings are selected
    if not selected_indices:
        messagebox.showwarning("Warning", "No recording selected for deletion.")
        return

    # Delete selected recordings
    for idx in sorted(
        selected_indices, reverse=True
    ):  # Reverse to avoid indexing issues
        del recordings[idx - 1]  # Adjust index for 0-based list

    # Update the recording list in the GUI
    update_recordings_list()

    # Update the label based on the remaining number of recordings
    file_label.config(
        text=f"{len(recordings)} files remaining" if recordings else "No files uploaded"
    )

    messagebox.showinfo(
        "Success", f"{len(selected_indices)} files deleted successfully."
    )


def play_audio():
    global is_playing
    # Identify selected recordings
    selected_indices = [idx for idx, selected in selected_labels.items() if selected]

    # Error handling if no or multiple recordings are selected
    if len(selected_indices) == 0:
        messagebox.showwarning("Warning", "No recording selected.")
        return
    elif len(selected_indices) > 1:
        messagebox.showwarning("Warning", "Please select only one recording to play.")
        return

    # Get the selected recording index
    selected_idx = selected_indices[0]
    selected_recording = recordings[selected_idx - 1]  # Adjust index for 0-based list

    # Extract audio data from the selected recording
    try:
        if "audio_data" in selected_recording:
            audio_data = selected_recording["audio_data"]
        else:
            # Load from file if audio_data is not in memory
            with wave.open(selected_recording["filepath"], "rb") as wf:
                audio_data = np.frombuffer(
                    wf.readframes(wf.getnframes()), dtype=np.int16
                )

        if not is_playing:
            # Start playing the audio
            sd.play(audio_data, fs)
            play_button.configure(text="❚❚")  # Change to pause icon
            is_playing = True
            # Start checking the status of playback
            root.after(100, check_if_playback_finished)
        else:
            # Stop playing the audio
            sd.stop()
            play_button.configure(text="▶")  # Change back to play icon
            is_playing = False
    except Exception as e:
        messagebox.showerror("Error", f"Could not play/stop audio: {e}")


def check_if_playback_finished():
    global is_playing
    if not sd.get_stream().active:
        # Playback has finished
        play_button.configure(text="▶")  # Reset the icon to play
        is_playing = False
    else:
        # Playback is still running, check again after 100 ms
        root.after(100, check_if_playback_finished)


def save_wav_file(filename, data, fs=44100):
    """Save audio data as a WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)  # Mono channel
        wf.setsampwidth(2)  # 16-bit samples
        wf.setframerate(fs)  # Sample rate
        wf.writeframes((data * 32767).astype(np.int16).tobytes())
    print(f"Recording saved as {filename}")


def toggle_recording():
    global record_state, audio_data, start_time
    if record_state:
        # Stop recording
        record_state = False
        sd.stop()
        duration = time.time() - start_time
        audio_data = audio_data[: int(duration * fs)]
        canvas.itemconfig(record_shape, fill=current_colors["default"])
        timer_label.configure(text="00:00:00", fg_color="transparent")

        # Save the audio data as a WAV file
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        save_wav_file(filename, audio_data, fs)
        recordings.append(
            {
                "filename": filename,
                "duration": duration,
                "filepath": filename,
                "audio_data": audio_data.copy(),
            }
        )
        update_recordings_list()  # Update the GUI list
        print(f"Recording saved as {filename} with duration {duration:.2f} seconds.")
    else:
        # Start recording
        record_state = True
        audio_data = np.zeros(
            (int(3600 * fs), 1), dtype=np.float32
        )  # Buffer for 1 hour
        sd.rec(
            int(3600 * fs), samplerate=fs, channels=1, dtype="float32", out=audio_data
        )
        start_time = time.time()
        canvas.itemconfig(record_shape, fill=current_colors["recording"])
        update_timer()
        print("Recording started...")


# Global dictionary to track selected state of labels
selected_labels = {}
recordings = []  # This will store dictionaries with recording info and file paths


def update_recordings_list():
    global selected_labels
    # Clear existing CTkLabels in the custom_list_frame and reset selected labels tracking
    for widget in custom_list_frame.winfo_children():
        widget.destroy()
    selected_labels.clear()

    # Get the appropriate text color based on the current theme
    text_color = (
        dark_mode_colors["text"]
        if ctk.get_appearance_mode() == "Dark"
        else light_mode_colors["text"]
    )

    # Adding new recordings to the custom listbox
    for idx, recording in enumerate(recordings, start=1):
        label = ctk.CTkLabel(
            custom_list_frame,
            text=f"{idx}. {recording['filename']} - {recording['duration']:.2f} sec",
            anchor="w",
            padx=10,
            text_color=text_color,  # Set the initial text color here
        )
        label.pack(fill="x", padx=5, pady=2)
        label.bind(
            "<Button-1>", lambda e, idx=idx, label=label: select_recording(idx, label)
        )
        selected_labels[idx] = False


def select_recording(idx, label):
    # Toggle selection state
    if selected_labels[idx]:
        label.configure(bg_color="transparent")  # Deselect: set background to white
        selected_labels[idx] = False
    else:
        label.configure(bg_color="#5A9BD5")  # Select: set background to blue
        selected_labels[idx] = True
    print(f"Recording #{idx} selected state: {selected_labels[idx]}")


def update_timer():
    if record_state:
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)
        hours, minutes = divmod(minutes, 60)
        timer_label.configure(
            text=f"{hours:02}:{minutes:02}:{seconds:02}", fg_color="red"
        )
        root.after(1000, update_timer)  # Update every second


# List of random topics (historical stories, ancient myths, etc.)
topics = [
    "ancient Greek mythology",
    "the rise of the Roman Empire",
    "medieval European history",
    "the ancient pyramids of Egypt",
    "the folklore of ancient China",
    "Viking myths and sagas",
    "the ancient civilization of Mesopotamia",
    "the Aztec empire and its traditions",
    "the legend of King Arthur",
    "Greek philosophers and their teachings",
]

# Instruction templates for generating the AI prompt
instruction_templates = [
    "Tell a story about {} with minimal details and neutral language.",
    "Generate a text about the history and myths surrounding {}.",
    "Write a simple paragraph about {} and its significance.",
    "Describe a brief historical event or myth from {}.",
    "Create a story involving {} using clear and simple language.",
]


# AI writer callback with Google API for language detection and translation
def ai_writer_callback():
    # Get the current text from the text box
    input_text = text_entry.get("1.0", tk.END).strip()

    if not input_text:
        # Generate random content if input is empty
        topic = random.choice(topics)
        instruction_template = random.choice(instruction_templates)
        prompt_input = instruction_template.format(topic)

        # Generate the response from Hugging Face API
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt_input}],
            max_tokens=50,  # Adjust based on how much continuation you want
            stream=False,
            temperature=random.uniform(0.7, 1.3),
            top_p=random.uniform(0.7, 1.0),
        )
        generated_text = response.choices[0].message.content

        # Translate the generated text to the selected interface language
        selected_language = language_var.get()
        language_code = language_options.get(selected_language, "en")

        if language_code != "en":
            translated_text = translate_text(generated_text, language_code)
        else:
            translated_text = generated_text

        # Update the text entry with the translated response
        text_entry.delete("1.0", tk.END)
        text_entry.insert(tk.END, translated_text)
    else:
        # Detect the language of the last word in the input text
        last_word = input_text.split()[-1]
        detected_language = detect_language(last_word)
        detected_language_code = detected_language.language_code

        # Translate the entire input text to English if it's not already in English
        if detected_language_code != "en":
            translated_input = translate_text(input_text, "en")
        else:
            translated_input = input_text

        # Generate a continuation using the translated input
        prompt_input = (
            f"Continue writing after the following text: '{translated_input}'"
        )

        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt_input}],
            max_tokens=50,
            stream=False,
            temperature=random.uniform(0.7, 1.3),
            top_p=random.uniform(0.7, 1.0),
        )

        generated_text = response.choices[0].message.content

        # Translate the generated text back to the language of the last word
        if detected_language_code != "en":
            final_output = translate_text(generated_text, detected_language_code)
        else:
            final_output = generated_text

        # Update the text entry with the final translated response
        # text_entry.delete("1.0", tk.END)
        text_entry.insert(tk.END, final_output)


# Main application window setup
root = ctk.CTk()
root.title("Coqui AI TTS GUI")
root.geometry("400x600")  # Defined size for the main window
root.configure(fg_color="#2b2b2b")

# Global variables for translation options
replace_translated_text = tk.BooleanVar(value=True)  # Default to replacing text

recordings = []  # List to store recordings

fs = 44100  # Sample rate for the audio
recording = None
record_state = False
filepath = None
audio_data = None
start_time = None

# Add the language option menu in the top-left corner
language_var = ctk.StringVar(value="English")
# Default to English interface text
interface_text = translations["English"]

# Create a frame to hold the language option menu, enter text label, and theme switch
top_frame = tk.Frame(root, bg="#2b2b2b")
top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)  # Adjust padding as needed

# Add the language option menu to the top_frame
language_option_menu = ctk.CTkOptionMenu(
    top_frame,
    values=list(language_options.keys()),
    variable=language_var,
    command=update_language,  # Callback to update the UI when the language is selected
    fg_color=("lightgray", "dimgray"),
    button_color=("lightgray", "dimgray"),
    button_hover_color=("#bfbfbf", "#4a4a4a"),
    dropdown_fg_color=("lightgray", "dimgray"),
    dropdown_hover_color=("#bfbfbf", "#4a4a4a"),
    dropdown_text_color=("black", "white"),
    text_color=("black", "white"),
    corner_radius=10,
    width=100,
)
language_option_menu.pack(side=tk.LEFT, padx=5)

# Add the enter text label to the same frame
text_label = tk.Label(
    top_frame,
    text=interface_text["enter_text"],
    bg="#2b2b2b",
    fg="white",
)
text_label.pack(side=tk.LEFT, expand=True, padx=10)  # Centered with expand and padding


# Function to toggle between light and dark modes
def toggle_mode():
    if theme_switch.get() == 1:  # 1 means switch is "on" (Dark Mode)
        ctk.set_appearance_mode("Dark")
    else:  # 0 means switch is "off" (Light Mode)
        ctk.set_appearance_mode("Light")

    update_ui_colors()

    update_circle_button_colors()  # Update the circle button colors when mode is toggled


# Add the theme switch to the same frame
theme_switch = ctk.CTkSwitch(
    top_frame,
    text=interface_text["dark_mode"],
    command=toggle_mode,
    onvalue=1,
    offvalue=0,
    fg_color=("lightgray", "dimgray"),
    button_color=("white", "dimgray"),
    button_hover_color=("#bfbfbf", "#4a4a4a"),
    text_color="white",
    progress_color="darkgreen",
)
theme_switch.select()  # Default tfo dark mode
theme_switch.pack(side=tk.RIGHT, padx=5)

main_frame = tk.Frame(root, bg="#2b2b2b")
main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)


# Global variable to store the path of the generated audio file
generated_filepath = None

# UI Elements for status and play button
status_label = tk.Label(main_frame, text="", fg="black", bg="#2b2b2b")


text_entry = ctk.CTkTextbox(
    main_frame,
    width=320,
    height=120,
    corner_radius=10,
    fg_color=("lightgray", "dimgray"),  # Background color for light and dark mode
    text_color=("black", "white"),  # Text color
    border_color=("black", "white"),  # Border color
    scrollbar_button_color=("gray", "darkgray"),  # Scrollbar color
    scrollbar_button_hover_color=("lightgray", "gray"),  # Scrollbar hover color
    wrap="word",
)
text_entry.pack(pady=10)

# Add a label for "Highlight and Translate:"
highlight_label = tk.Label(main_frame, text="Highlight and Translate:", bg="#2b2b2b")
highlight_label.pack(pady=5)


# Add a frame for translation options (radio buttons and language menu)
translation_frame = tk.Frame(main_frame, bg="#2b2b2b")
translation_frame.pack(pady=10)

# Radio buttons for choosing whether to replace the selected text with the translation
replace_radiobutton = tk.Radiobutton(
    translation_frame,
    text="With replacement",
    variable=replace_translated_text,
    value=True,
    bg="#2b2b2b",
)
replace_radiobutton.grid(row=0, column=0, padx=5, sticky="w")

no_replace_radiobutton = tk.Radiobutton(
    translation_frame,
    text="Without replacement",
    variable=replace_translated_text,
    value=False,
    bg="#2b2b2b",
)
no_replace_radiobutton.grid(row=1, column=0, padx=5, sticky="w")
# Create a frame for the language option menu and translate button
translation_action_frame = tk.Frame(main_frame, bg="#2b2b2b")
translation_action_frame.pack(pady=10)  # This will pack them together in a single line

# Update translation language option menu
translated_languages = [interface_text["languages"][lang] for lang in language_options]


# Option menu for selecting the target language for translation
translation_language_var = tk.StringVar(translation_action_frame)

translation_language_var.set(interface_text["languages"]["English"])
# Default to English


trans_language_option_menu = ctk.CTkOptionMenu(
    translation_action_frame,  # Use the new frame
    values=translated_languages,
    variable=translation_language_var,
    fg_color=("lightgray", "dimgray"),  # Main background color for light and dark mode
    button_color=("lightgray", "dimgray"),  # Button color
    button_hover_color=("#bfbfbf", "#4a4a4a"),  # Hover effect
    dropdown_fg_color=("lightgray", "dimgray"),  # Dropdown background color
    dropdown_hover_color=("#bfbfbf", "#4a4a4a"),  # Dropdown hover effect
    dropdown_text_color=("black", "white"),  # Text in dropdown options
    text_color=("black", "white"),  # Text in selected option
    corner_radius=10,  # Rounded corners
    width=100,
)

trans_language_option_menu.pack(
    side="left", padx=5
)  # Align it to the left within the frame

# Button to trigger translation of selected text
translate_button = ctk.CTkButton(
    translation_action_frame,  # Use the same frame
    text="🌐",
    command=translate_selected_text,
    corner_radius=15,
    fg_color=("lightgray", "dimgray"),
    hover_color=("#bfbfbf", "#4a4a4a"),
    text_color=("black", "white"),
    width=50,
)
translate_button.pack(
    side="left", padx=5
)  # Align it to the left within the frame, next to the option menu

file_label = tk.Label(main_frame, text=interface_text["no_file_selected"], bg="#2b2b2b")
file_label.pack(pady=5)

upload_button = ctk.CTkButton(
    main_frame,
    text=interface_text["upload_wav_file"],
    command=open_file,
    corner_radius=15,
    fg_color=("lightgray", "dimgray"),  # Light/dark button color
    hover_color=("#bfbfbf", "#4a4a4a"),
    text_color=("black", "white"),  # Text color for light/dark mode
)
upload_button.pack(pady=5)

record_button = ctk.CTkButton(
    main_frame,
    text=interface_text["record_wav_file"],
    command=open_recording_window,
    corner_radius=15,
    fg_color=("lightgray", "dimgray"),  # Light/dark button color
    hover_color=("#bfbfbf", "#4a4a4a"),
    text_color=("black", "white"),
)
record_button.pack(pady=5)

# Add AI Writer button above the Upload WAV button
ai_writer_button = ctk.CTkButton(
    main_frame,
    text=interface_text[
        "ai_writer"
    ],  # You can use a symbol here, or replace with an icon
    command=ai_writer_callback,  # This is the function that will generate the response
    corner_radius=15,
    fg_color=("lightgray", "dimgray"),  # Light/dark button color
    hover_color=("#bfbfbf", "#4a4a4a"),
    text_color=("black", "white"),  # Text color for light/dark mode
)
ai_writer_button.pack(pady=5)  # Place it above the Upload WAV button

generate_button = ctk.CTkButton(
    main_frame,
    text=interface_text["generate_speech"],
    command=generate_speech,
    corner_radius=15,
    fg_color=("lightgray", "dimgray"),  # Light/dark button color
    hover_color=("#bfbfbf", "#4a4a4a"),
    text_color=("black", "white"),
)
generate_button.pack(pady=5)

status_label.pack(pady=5)

# Define the color schemes for light and dark modes
dark_mode_colors = {
    "background": "#2b2b2b",
    "text": "white",
    "button": "dimgray",
    "button_hover": "#4a4a4a",
    "entry_bg": "dimgray",
    "entry_text": "white",
    "canvas_bg": "#2b2b2b",
}

light_mode_colors = {
    "background": "white",
    "text": "black",
    "button": "lightgray",
    "button_hover": "#bfbfbf",
    "entry_bg": "lightgray",
    "entry_text": "black",
    "canvas_bg": "white",
}


def update_ui_colors():
    # Choose colors based on the current mode
    colors = (
        dark_mode_colors if ctk.get_appearance_mode() == "Dark" else light_mode_colors
    )

    # Update the background colors
    root.configure(fg_color=colors["background"])
    top_frame.configure(bg=colors["background"])
    main_frame.configure(bg=colors["background"])
    text_label.configure(bg=colors["background"], fg=colors["text"])
    file_label.configure(bg=colors["background"], fg=colors["text"])
    highlight_label.configure(bg=colors["background"], fg=colors["text"])
    translation_frame.configure(bg=colors["background"])
    translation_action_frame.configure(bg=colors["background"])
    no_replace_radiobutton.configure(
        bg=colors["background"], fg=colors["text"], selectcolor=colors["background"]
    )

    status_label.configure(bg=colors["background"])
    replace_radiobutton.configure(
        bg=colors["background"], fg=colors["text"], selectcolor=colors["background"]
    )
    if play_button in globals() and play_button.winfo_exists():
        play_button.configure(
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["text"],
        )

    # Update button colors
    upload_button.configure(
        fg_color=colors["button"],
        hover_color=colors["button_hover"],
        text_color=colors["text"],
    )
    record_button.configure(
        fg_color=colors["button"],
        hover_color=colors["button_hover"],
        text_color=colors["text"],
    )
    generate_button.configure(
        fg_color=colors["button"],
        hover_color=colors["button_hover"],
        text_color=colors["text"],
    )
    ai_writer_button.configure(
        fg_color=colors["button"],
        hover_color=colors["button_hover"],
        text_color=colors["text"],
    )
    translate_button.configure(
        fg_color=colors["button"],
        hover_color=colors["button_hover"],
        text_color=colors["text"],
    )

    theme_switch.configure(
        fg_color=colors["button"],
        button_color=colors["text"],
        text_color=colors["text"],
    )

    # Update text entry colors
    text_entry.configure(
        fg_color=colors["entry_bg"],
        text_color=colors["entry_text"],
        border_color=colors["text"],
    )

    # Update recording window UI elements if it exists and is open
    if "recording_window" in globals() and recording_window.winfo_exists():
        recording_list_label.configure(bg=colors["background"], fg=colors["text"])
        generate_prompt_button.configure(
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["text"],
        )

        recording_window.configure(bg=colors["background"])
        container.configure(bg=colors["background"])
        bottom_frame.configure(bg=colors["background"])
        button_frame.configure(bg=colors["background"])

        # Update prompt label and language option menu in the recording window
        prompt_label.configure(bg=colors["background"], fg=colors["text"])
        option_menu.configure(
            fg_color=colors["button"],
            button_color=colors["button"],
            button_hover_color=colors["button_hover"],
            dropdown_fg_color=colors["entry_bg"],
            dropdown_hover_color=colors["button_hover"],
            dropdown_text_color=colors["entry_text"],
            text_color=colors["text"],
        )

        prompt_textbox.configure(
            fg_color="transparent",
            text_color=colors["entry_text"],
        )

        # Update prompt button colors
        generate_prompt_button.configure(
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["text"],
        )

        # Update the colors of the upload, play, and delete buttons
        upload_button.configure(
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["text"],
        )
        play_button.configure(
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["text"],
        )
        delete_button.configure(
            fg_color=colors["button"],
            hover_color=colors["button_hover"],
            text_color=colors["text"],
        )

        # Update timer label in the recording window
        timer_label.configure(
            text_color=colors["entry_text"],
        )

        for widget in custom_list_frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=colors["entry_text"])

        canvas.configure(bg=colors["canvas_bg"])
        update_circle_button_colors()  # Update the circle button colors based on mode


root.mainloop()
