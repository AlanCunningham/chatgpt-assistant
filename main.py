import logging
import time
import vlc
import prompts
import random
import requests
import shutil
import settings
import subprocess
import speech_recognition
import os
import pvporcupine
from pvrecorder import PvRecorder
from openai import OpenAI
import threading
from pathlib import Path


image_thread = None


def play_audio(audio_file_path):
    player = vlc.MediaPlayer(audio_file_path)
    player.play()
    time.sleep(1)
    # Ensure the program doesn't cut off the text to speech
    while player.is_playing():
        time.sleep(1)


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
        subprocess.call(f"sudo fbi -T 1 dalle_image.png --noverbose &", shell=True)


def get_assistant(openai_client):
    """
    Returns an already-created Assistant.
    """
    assistant = openai_client.beta.assistants.retrieve(settings.openai_assistant_id)
    print(assistant)
    return assistant


def whisper_text_to_speech(openai_client, text_to_say):
    """
    Text to speech using OpenAI's Whisper API.
    """
    print("whisper_text_to_speech")
    speech_file_path = Path(__file__).parent / "speech.mp3"
    response = openai_client.audio.speech.create(
        model="tts-1", voice="nova", input=text_to_say
    )
    response.stream_to_file(speech_file_path)

    play_audio(speech_file_path)


def send_to_assistant(openai_client, assistant, assistant_thread, input_text):
    """
    Send text to an OpenAI Assistant and gets the response to pass to Whisper
    and Dall-E.
    """
    message = openai_client.beta.threads.messages.create(
        thread_id=assistant_thread.id, role="user", content=input_text
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant.id,
    )

    run_completed = False
    timeout_limit = 10
    timeout_counter = 0
    while not run_completed:
        if timeout_counter >= timeout_limit:
            print("Timeout exceeded")
            timeout_counter = 0
            break
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=assistant_thread.id,
            run_id=run.id,
        )
        if run.status == "completed":
            run_completed = True
        time.sleep(1)
        timeout_counter += 1

    if timeout_counter >= timeout_limit:
        assistant_output = (
            "Sorry, it looks like something went wrong. Try again in a moment or two."
        )
    else:
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

    # List the recording devices
    for i, device in enumerate(PvRecorder.get_available_devices()):
        print("Device %d: %s" % (i, device))

    # print("Listening")
    # while True:
    #     pcm = hotword_recorder.read()
    #     result = handle.process(pcm)
    #     if result >= 0:
    #         print("Detected!")

    running = True
    wait_for_hotword = True
    first_session_listen = True
    while running:
        if wait_for_hotword:
            if first_session_listen:
                # Hotword setup
                print(pvporcupine.KEYWORDS)
                pvporcupine_api_key = settings.pvporcupine_api_key
                handle = pvporcupine.create(
                    access_key=pvporcupine_api_key, keywords=["porcupine", "alexa"]
                )

                hotword_recorder = PvRecorder(
                    frame_length=handle.frame_length, device_index=3
                )
                hotword_recorder.start()

                print("Waiting for hotword...")
                first_session_listen = False
            # Wait for the hotword
            pcm = hotword_recorder.read()
            result = handle.process(pcm)
            if result >= 0:
                print("Detected!")
                wait_for_hotword = False
                hotword_recorder.delete()
                handle.delete()
        else:
            # Hotword detected, continue with speech recognition
            play_audio("audio/what.mp3")
            microphone = speech_recognition.Microphone()
            speech_result = speech_recognition.Recognizer()

            print("Ready for input:")
            with microphone as source:
                audio = speech_result.listen(source)
            try:
                recognised_speech = speech_result.recognize_google(audio)
                print(recognised_speech)
                wait_for_hotword = True
                first_session_listen = True

                # List of phrases to cancel the conversation before making
                # requests to ChatGPT
                cancel_phrases = [
                    "nevermind",
                    "never mind",
                    "no",
                    "stop",
                    "cancel that",
                    "cancel",
                    "nothing",
                ]
                if any(
                    cancel_phrase in recognised_speech
                    for cancel_phrase in cancel_phrases
                ):
                    end_conversation_phrases = [
                        "audio/oh_ok.mp3",
                        "audio/alright_then.mp3",
                        "audio/nevermind.mp3",
                    ]
                    play_audio(random.choice(end_conversation_phrases))
                else:
                    play_audio("audio/hmm.mp3")
                    send_to_assistant(
                        client, assistant, assistant_thread, recognised_speech
                    )
            except speech_recognition.UnknownValueError:
                print("Could not understand audio")
            except speech_recognition.RequestError as e:
                print(f"Error: {e}")
