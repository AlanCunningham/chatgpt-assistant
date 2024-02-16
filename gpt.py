import helpers
import prompts
import settings
import logging
import requests
import shutil
import threading
import time
from PIL import Image
from pathlib import Path


image_thread = None


def get_assistant(openai_client):
    """
    Returns an already-created Assistant.
    """
    assistant = openai_client.beta.assistants.retrieve(settings.openai_assistant_id)
    logging.info(assistant)
    return assistant


def whisper_text_to_speech(openai_client, text_to_say):
    """
    Text to speech using OpenAI's Whisper API.
    """
    speech_file_path = Path(__file__).parent / "speech.mp3"
    response = openai_client.audio.speech.create(
        model="tts-1", voice="nova", input=text_to_say
    )
    response.stream_to_file(speech_file_path)
    helpers.play_audio(speech_file_path)


def generate_chatgpt_image(openai_client, user_text, assistant_output_text):
    """
    Generates a dall-e image based on given text (usually the output of the
    GPT assistant)
    """
    logging.info("Generating image")
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
    logging.info(image_url)

    # Download the image
    response = requests.get(image_url, stream=True)
    if response.ok:
        with open("dalle_image.png", "wb") as image_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, image_file)

        # Resize the image to display on the smaller, 800x480 display. This
        # doesn't maintain the aspect ratio.
        image = Image.open("dalle_image.png")
        resized_image = image.resize((800, 480))
        resized_image.save("resized.png")
        helpers.display_image("resized.png")


def send_to_assistant(
    openai_client, assistant, assistant_thread_id, input_text, text_to_speech=True
):
    """
    Send text to an OpenAI Assistant and gets the response to pass to Whisper
    and Dall-E.
    """

    # Encourage the GPT3 response to be brief. This is usually set on
    # the assistant prompt, however I've found responses can still be
    # rather long.
    brief_prompt = "Remember to keep responses brief."
    amended_input_text = f"{input_text}\n{brief_prompt}"

    logging.info(f"Input text: {amended_input_text}")

    message = openai_client.beta.threads.messages.create(
        thread_id=assistant_thread_id, role="user", content=amended_input_text
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=assistant_thread_id,
        assistant_id=assistant.id,
    )

    run_completed = False
    timeout_limit = 10
    timeout_counter = 0
    while not run_completed:
        if timeout_counter >= timeout_limit:
            logging.info("Timeout exceeded")
            timeout_counter = 0
            break
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=assistant_thread_id,
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
        thread_messages = openai_client.beta.threads.messages.list(assistant_thread_id)
        # The most recent assistant's response will be the first item in the list
        assistant_output = thread_messages.data[0].content[0].text.value
    logging.info(f"Assistant output: {assistant_output}")

    global image_thread
    image_thread = threading.Thread(
        target=generate_chatgpt_image,
        args=(openai_client, input_text, assistant_output),
    )
    image_thread.should_abort_immediately = True
    image_thread.start()

    if text_to_speech:
        whisper_text_to_speech(openai_client, assistant_output)
