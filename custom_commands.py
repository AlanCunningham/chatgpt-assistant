import helpers
import apprise_sender
import random
import time
import shutil
import os
import logging


current_image = None


def run_command(recognised_speech):
    """
    Runs a custom command if certain keywords are in the recognised
    speech.  Returns True if a custom command is run, otherwise False so
    we can send the recognised speech to ChatGPT instead.
    """
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

    if any(cancel_phrase in recognised_speech for cancel_phrase in cancel_phrases):
        # Cancel the conversation
        logging.info("Custom command: cancel")
        end_conversation_phrases = [
            "audio/oh_ok.mp3",
            "audio/alright_then.mp3",
        ]
        # helpers.play_audio(random.choice(end_conversation_phrases))
        helpers.display_image("resized.png")
        return True

    elif any(
        send_image_phrase in recognised_speech
        for send_image_phrase in send_image_phrases
    ):
        # Send the last created dall-e image to Telegram
        logging.info("Custom command: Save and send image via apprise")
        helpers.display_image("resized.png")
        helpers.play_audio("audio/sending_image.mp3")
        apprise_sender.send("", "", "dalle_image.png")

        # Save the image to the saved images folder
        filename = time.strftime("%Y%m%d-%H%M%S")
        shutil.copyfile("resized.png", f"saved_images/{filename}.png")
        return True

    elif any(
        show_random_image_phrase in recognised_speech
        for show_random_image_phrase in show_random_image_phrases
    ):
        # Pick a random saved image and display it on the screen
        logging.info("Custom command: Display a random picture")
        global current_image
        images = os.listdir("saved_images")
        if current_image:
            images.remove(current_image)
        random_image = random.choice(images)
        helpers.display_image(f"saved_images/{random_image}")
        current_image = random_image
        return True

    else:
        # The recognised speech didn't contain any keywords that
        # triggered a custom command.
        logging.info("Custom command: None recognised")
        return False
