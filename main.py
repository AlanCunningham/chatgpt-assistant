import apprise_sender
import gpt
import helpers
import logging
import os
import random
import settings
import shutil
import speech_recognition
import time
import pvporcupine
from pvrecorder import PvRecorder
from openai import OpenAI


def main():
    client = OpenAI(api_key=settings.openai_api_key)
    assistant = gpt.get_assistant(client)
    assistant_thread = client.beta.threads.create()

    # test_input = "An interesting fact"
    # send_to_assistant(client, assistant, assistant_thread, test_input)

    # List the recording devices
    for i, device in enumerate(PvRecorder.get_available_devices()):
        print("Device %d: %s" % (i, device))

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
                    access_key=pvporcupine_api_key, keywords=["porcupine"]
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
                # Hotword detected
                print("Detected!")
                wait_for_hotword = False
                hotword_recorder.delete()
                handle.delete()
        else:
            # Hotword detected, continue with speech recognition
            hotword_responses = [
                "audio/what.mp3",
                "audio/yes_question.mp3",
            ]
            helpers.play_audio(random.choice(hotword_responses))
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
                    "stop",
                    "cancel that",
                    "cancel",
                    "nothing",
                    "forget it",
                ]

                # List of phrases to send the dall-e image to telegram
                send_image_phrases = [
                    "send",
                    "telegram",
                ]

                # List of phrases to display a random image from the saved
                # images folder.
                show_random_image_phrases = [
                    "random",
                ]

                if any(
                    cancel_phrase in recognised_speech
                    for cancel_phrase in cancel_phrases
                ):
                    # Cancel the conversation
                    end_conversation_phrases = [
                        "audio/oh_ok.mp3",
                        "audio/alright_then.mp3",
                    ]
                    helpers.play_audio(random.choice(end_conversation_phrases))

                elif any(
                    send_image_phrase in recognised_speech
                    for send_image_phrase in send_image_phrases
                ):
                    # Send the last created dall-e image to Telegram
                    helpers.play_audio("audio/sending_image.mp3")
                    apprise_sender.send("", "", "dalle_image.png")

                    # Save the image to the saved images folder
                    filename = time.strftime("%Y%m%d-%H%M%S")
                    shutil.copyfile("resized.png", f"saved_images/{filename}.png")

                elif any(
                    show_random_image_phrase in recognised_speech
                    for show_random_image_phrase in show_random_image_phrases
                ):
                    # Pick a random saved image and display it on the screen
                    random_image = random.choice(os.listdir("saved_images"))
                    helpers.display_image(random_image)

                else:
                    helpers.play_audio("audio/hmm.mp3")
                    gpt.send_to_assistant(
                        client, assistant, assistant_thread, recognised_speech
                    )
            except speech_recognition.UnknownValueError:
                print("Could not understand audio")
                wait_for_hotword = True
                first_session_listen = True
            except speech_recognition.RequestError as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(filename)s %(lineno)d - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler("/tmp/gpt_assistant.log"),
            logging.StreamHandler(),
        ],
    )

    main()
