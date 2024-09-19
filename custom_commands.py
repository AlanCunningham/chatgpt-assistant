import helpers
import apprise_sender
import prompts
import settings
import random
import time
import shutil
import os
import requests
import logging
import gpt
from datetime import datetime


current_image = None


def run_command(openai_client, assistant, assistant_thread, recognised_speech):
    """
    Runs a custom command if certain keywords are in the recognised
    speech.  Returns True if a custom command is run, otherwise False so
    we can send the recognised speech to ChatGPT instead.
    The OpenAI Assistant parameters are used for the Bird Summary custom command.
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

    # List of phrases to retrieve a bird summary from BirdNET Pi.
    # This command requires all of these phrases to be in the
    # recognised speech.
    bird_summary_phrases = [
        "bird",
        "summary"
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

    elif all(
        bird_summary_phrase in recognised_speech
        for bird_summary_phrase in bird_summary_phrases
    ):
        # Send the top 10 birds from today's BirdNET Pi chart,
        # and send them to ChatGPT. Only runs if the bird_net_pi_ip_address
        # setting in settings.py is populated.
        if settings.bird_net_pi_ip_address:
            logging.info("Custom command: Bird summary")
            helpers.display_image("assistant_images/thinking.png")
            helpers.play_audio("audio/hmm.mp3")

            # Download the daily chart to send to GPT-4o Vision (Assistant API
            # doesn't yet support Vision)
            # The daily chart contains today's date - for example:
            # http://ip_address/Charts/Combo-2024-06-15.png
            date_string = datetime.now().strftime("%Y-%m-%d")
            daily_chart_image_url = f"http://{settings.bird_net_pi_ip_address}/Charts/Combo-{date_string}.png"
            daily_chart_response = requests.get(daily_chart_image_url, stream=True)
            if daily_chart_response.ok:
                with open("bird_chart.png", "wb") as image_file:
                    daily_chart_response.raw.decode_content = True
                    shutil.copyfileobj(daily_chart_response.raw, image_file)

            # Convert the image to base64
            daily_chart_base64 = helpers.encode_image("bird_chart.png")

            # Append the recognised speech to the bird summary prompt, so the user can ask for the
            # response as a poem etc
            modified_bird_summary_prompt = f"{prompts.bird_summary_prompt}\n{recognised_speech}"

            # Send to ChatGPT-4o Vision
            gpt_response = gpt.send_image_to_chatgpt(daily_chart_base64, modified_bird_summary_prompt)

            # Now send the response to the Assistant, so the response gets added
            # to the Assistant's memory and we can generate an image. First we'll
            # tweak what we want the Assistant to do:
            amended_prompt = f"""
                {recognised_speech}. The following is a summary of birds that have visited my garden
                today. Repeat it exactly as it is written:
                {gpt_response}
            """
            gpt.send_to_assistant(
                openai_client, assistant, assistant_thread, amended_prompt
            )
            return True
        else:
            return False

    else:
        # The recognised speech didn't contain any keywords that
        # triggered a custom command.
        logging.info("Custom command: None recognised")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(filename)s %(lineno)d - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
        ],
    )
    run_command("Show me a bird summary")
