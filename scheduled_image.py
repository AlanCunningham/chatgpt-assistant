import gpt
import helpers
import prompts
import settings
import logging
import os
import random
from openai import OpenAI


def scheduled_image():
    """
    Intended to be run by a cronjob which will automatically show a new image
    on the display.
    """
    client = OpenAI(api_key=settings.openai_api_key)
    assistant = gpt.get_assistant(client)
    assistant_thread = ""
    with open("assistant_thread.txt", "r") as assistant_thread_file:
        assistant_thread = assistant_thread_file.read()

    gpt.send_to_assistant(
        client,
        assistant,
        assistant_thread,
        prompts.scheduled_image_prompt,
        text_to_speech=False,
    )


def display_random_saved_image():
    # Pick a random saved image and display it on the screen
    images = os.listdir("saved_images")
    random_image = random.choice(images)
    helpers.display_image(f"saved_images/{random_image}")

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(filename)s %(lineno)d - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler("/tmp/gpt_assistant_cronjob.log"),
            logging.StreamHandler(),
        ],
    )
    #scheduled_image()
    display_random_saved_image()
