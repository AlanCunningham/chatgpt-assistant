import logging
import time
import vlc
import prompts
import requests
import shutil
import settings
import subprocess
import speech_recognition
import os
from eff_word_net.streams import SimpleMicStream
from eff_word_net.engine import HotwordDetector
from eff_word_net.audio_processing import Resnet50_Arc_loss
import eff_word_net.audio_processing
from eff_word_net import samples_loc
from openai import OpenAI
import threading
from pathlib import Path


image_thread = None


def generate_chatgpt_image(openai_client, user_text, assistant_output_text):
    """
    Generates a dall-e image based on given text (usually the output of the
    GPT assistant)
    """
    print("Generating image")
    image_prompt = (
        f"{prompts.assistant_image_prompt}\n{user_text}\n{assistant_output_text}"
    )

    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    print(image_url)

    # Download the image
    response = requests.get(image_url, stream=True)
    if response.ok:
        with open("dalle_image.png", "wb") as image_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, image_file)
        subprocess.call(f"feh -F dalle_image.png &", shell=True)


def get_assistant(openai_client):
    """
    Returns an already-created Assistant.
    """
    assistant = openai_client.beta.assistants.retrieve(settings.openai_assistant_id)
    print(assistant)
    return assistant


def whisper_text_to_speech(openai_client, text_to_say):
    print("whisper_text_to_speech")
    speech_file_path = Path(__file__).parent / "speech.mp3"
    response = openai_client.audio.speech.create(
        model="tts-1", voice="nova", input=text_to_say
    )
    response.stream_to_file(speech_file_path)

    player = vlc.MediaPlayer(speech_file_path)
    player.play()
    time.sleep(1)
    # Ensure the program doesn't cut off the text to speech
    while player.is_playing():
        time.sleep(1)


def send_to_assistant(openai_client, assistant, assistant_thread, input_text):
    message = openai_client.beta.threads.messages.create(
        thread_id=assistant_thread.id, role="user", content=input_text
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant.id,
    )

    run_completed = False
    while not run_completed:
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=assistant_thread.id,
            run_id=run.id,
        )
        if run.status == "completed":
            run_completed = True
        time.sleep(1)

    thread_messages = openai_client.beta.threads.messages.list(assistant_thread.id)
    # The most recent assistant's response will be the first item in the list
    assistant_output = thread_messages.data[0].content[0].text.value
    print(assistant_output)

    global image_thread
    image_thread = threading.Thread(
        target=generate_chatgpt_image, args=(client, input_text, assistant_output)
    )
    image_thread.should_abort_immediately = True
    image_thread.start()

    whisper_text_to_speech(openai_client, assistant_output)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(filename)s %(lineno)d - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler("/tmp/chatbot_scambaiter.log"),
            logging.StreamHandler(),
        ],
    )

    client = OpenAI(api_key=settings.openai_api_key)
    assistant = get_assistant(client)
    assistant_thread = client.beta.threads.create()

    # test_input = "An interesting fact"
    # send_to_assistant(client, assistant, assistant_thread, test_input)

    # Set up hotword detection
    base_model = Resnet50_Arc_loss()
    mycroft_hotword = HotwordDetector(
        hotword="mycroft",
        model=base_model,
        reference_file=os.path.join(samples_loc, "mycroft_ref.json"),
        threshold=0.7,
        relaxation_time=2,
    )

    mic_stream = SimpleMicStream(
        window_length_secs=1.5,
        sliding_window_secs=0.75,
    )
    mic_stream.start_stream()

    running = True
    waiting_for_hotword = True
    first_session_listen = True
    while running:
        if waiting_for_hotword:
            if first_session_listen:
                print("Waiting for hotword...")
                first_session_listen = False
            # Wait for the hotword
            frame = mic_stream.getFrame()
            result = mycroft_hotword.scoreFrame(frame)
            if not result:
                continue
            if result["match"]:
                waiting_for_hotword = False
                print("Hotword uttered")
        else:
            # Hotword detected, continue with speech recognition
            print("Ready for input:")
            speech_result = speech_recognition.Recognizer()
            with speech_recognition.Microphone() as source:
                audio = speech_result.listen(source)
            try:
                recognised_speech = speech_result.recognize_google(audio)
                print(recognised_speech)
                waiting_for_hotword = True
                first_session_listen = True
                send_to_assistant(
                    client, assistant, assistant_thread, recognised_speech
                )
            except speech_recognition.UnknownValueError:
                print("Could not understand audio")
            except speech_recognition.RequestError as e:
                print(f"Error: {e}")
