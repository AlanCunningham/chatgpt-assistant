import custom_commands
import gpt
import helpers
import logging
import settings
import speech_recognition
import pvporcupine
from pvrecorder import PvRecorder
from openai import OpenAI


def main():
    client = OpenAI(api_key=settings.openai_api_key)
    assistant = gpt.get_assistant(client)
    assistant_thread = client.beta.threads.create()

    # Save the assistant thread to a text file, so we can use it in our
    # scheduled image cronjob
    with open("assistant_thread.txt", "w") as assistant_thread_file:
        assistant_thread_file.write(assistant_thread.id)

    # test_input = "An interesting fact"
    # send_to_assistant(client, assistant, assistant_thread, test_input)

    # List the recording devices
    for i, device in enumerate(PvRecorder.get_available_devices()):
        logging.info("Device %d: %s" % (i, device))

    running = True
    wait_for_hotword = True
    first_session_listen = True

    while running:
        if wait_for_hotword:
            if first_session_listen:
                # Hotword setup
                logging.info(pvporcupine.KEYWORDS)
                pvporcupine_api_key = settings.pvporcupine_api_key
                handle = pvporcupine.create(
                    access_key=pvporcupine_api_key, keywords=["porcupine"]
                )

                hotword_recorder = PvRecorder(
                    frame_length=handle.frame_length, device_index=3
                )
                hotword_recorder.start()

                logging.info("Waiting for hotword...")
                first_session_listen = False

            # Wait for the hotword
            pcm = hotword_recorder.read()
            result = handle.process(pcm)
            if result >= 0:
                # Hotword detected
                logging.info("Detected!")
                wait_for_hotword = False
                hotword_recorder.delete()
                handle.delete()
        else:
            # Hotword detected, continue with speech recognition
            hotword_responses = [
                "audio/what.mp3",
                "audio/yes_question.mp3",
            ]
            #helpers.play_audio(random.choice(hotword_responses))
            helpers.display_image("assistant_images/listening.png")
            microphone = speech_recognition.Microphone()
            speech_result = speech_recognition.Recognizer()

            logging.info("Ready for input:")
            with microphone as source:
                audio = speech_result.listen(source, phrase_time_limit=10)
            try:
                recognised_speech = speech_result.recognize_google(audio)
                logging.info(f"Recognised speech: {recognised_speech}")
                wait_for_hotword = True
                first_session_listen = True

                # Check if the recognised speech contains the keyword to run
                # a custom command.  If not, then send the recognised speech
                # to ChatGPT.
                if custom_commands.run_command(client, assistant, assistant_thread.id, recognised_speech):
                    logging.info("Running custom command")
                else:
                    helpers.display_image("assistant_images/thinking.png")
                    helpers.play_audio("audio/hmm.mp3")
                    gpt.send_to_assistant(
                        client, assistant, assistant_thread.id, recognised_speech
                    )
            except speech_recognition.UnknownValueError:
                logging.info("Could not understand audio")
                helpers.display_image("resized.png")
                wait_for_hotword = True
                first_session_listen = True
            except speech_recognition.RequestError as e:
                logging.info(f"Error: {e}")


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
