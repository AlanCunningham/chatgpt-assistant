import custom_commands
import family_bell
import gpt
import helpers
import logging
import settings
import speech_recognition
import threading
import pvporcupine
from pvrecorder import PvRecorder


def main():
    gpt.setup()
    # test_input = "An interesting fact"
    # send_to_assistant(client, assistant, assistant_thread, test_input)

    # List the recording devices
    for i, device in enumerate(PvRecorder.get_available_devices()):
        logging.info("Device %d: %s" % (i, device))

    running = True
    wait_for_hotword = True
    first_session_listen = True

    # Start the family bell timer check
    family_bell_check_thread = threading.Thread(
        target=family_bell.check_time,
    )
    family_bell_check_thread.should_abort_immediately = True
    family_bell_check_thread.start()

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
                    frame_length=handle.frame_length, device_index=0
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
                helpers.display_image("assistant_images/listening.png")
        else:
            # Hotword detected, continue with speech recognition
            microphone = speech_recognition.Microphone()
            speech_result = speech_recognition.Recognizer()

            logging.info("Ready for input:")
            with microphone as source:
                audio = speech_result.listen(source, phrase_time_limit=10)
            try:
                # Speech recognised

                recognised_speech = speech_result.recognize_openai(audio)
                #recognised_speech = speech_result.recognize_google(audio)
                logging.info(f"Recognised speech: {recognised_speech}")
                # wait_for_hotword = True
                # first_session_listen = True

                # Check if the recognised speech contains the keyword to run
                # a custom command.

                # Check if the family bell is active
                if family_bell.is_family_bell_active:
                    helpers.display_image("assistant_images/family_bell.png")
                    family_bell.run_through_steps(recognised_speech)

                # Custom commands
                elif custom_commands.run_command(recognised_speech):
                    logging.info("Running custom command")
                    if recognised_speech in custom_commands.cancel_phrases:
                        # Reset speech recognition and wait for the hotword
                        wait_for_hotword = True
                        first_session_listen = True

                # Normal usage - send the request to ChatGPT
                else:
                    helpers.display_image("assistant_images/thinking.png")
                    helpers.play_audio("audio/hmm.mp3")
                    gpt.send_to_assistant(recognised_speech)
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
