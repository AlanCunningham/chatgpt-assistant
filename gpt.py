import base64
import helpers
import prompts
import settings
import logging
import requests
import shutil
import threading
import time
import os
from datetime import datetime
from openai import OpenAI
from PIL import Image
from pathlib import Path


client = ""
assistant = ""
assistant_thread = ""
image_thread = None


def setup():
    global client, assistant, assistant_thread
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    client = OpenAI(api_key=settings.openai_api_key)
    assistant = client.beta.assistants.retrieve(settings.openai_assistant_id)
    logging.info(assistant)
    assistant_thread = client.beta.threads.create()
    # Save the assistant thread to a text file, so we can use it in our
    # scheduled image cronjob
    with open("assistant_thread.txt", "w") as assistant_thread_file:
        assistant_thread_file.write(assistant_thread.id)



def whisper_text_to_speech(text_to_say, insert_audio_path=False):
    """
    Text to speech using OpenAI's Whisper API.
    insert_audio_path: A filepath of an audio file to play before playing the
    speech_to_text. For example, we might want to request the speech to text,
    then play the family bell audio, and then play the text to speech. This
    reduces the delay between family bell audio and speech to text.
    """
    speech_file_path = Path(__file__).parent / "speech.mp3"

    # The speech synthesis seems to have trouble saying "degrees celsius" when
    # it sees °C (e.g. from the weather custom command). Replace °C with just
    # the word "degrees"
    text_to_say = text_to_say.replace("°C", " degrees")

    response = client.audio.speech.create(
        model="tts-1", voice="fable", input=text_to_say
    )
    response.stream_to_file(speech_file_path)
    if insert_audio_path:
        helpers.play_audio(insert_audio_path)
    helpers.play_audio(speech_file_path)


def whisper_text_to_speech_test(text_to_say, insert_audio_path=False):
    completion = client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "fable", "format": "mp3"},
        messages=[
            {
                "role": "system",
                "content": "Say the following text exactly as is",
            },
            {
                "role": "user",
                "content": text_to_say,
            }
        ],
    )
    mp3_bytes = base64.b64decode(completion.choices[0].message.audio.data)
    speech_file_path = Path(__file__).parent / "speech.mp3"
    with open(speech_file_path, "wb") as f:
        f.write(mp3_bytes)
    if insert_audio_path:
        helpers.play_audio(insert_audio_path)
    helpers.play_audio(speech_file_path)


def add_microphone_to_image():
    print("Adding microphone to image")
    image = Image.open("resized.png")
    microphone_image = Image.open("assistant_images/microphone.png")
    resized_microphone_image = microphone_image.resize((100, 100))
    image.paste(resized_microphone_image)
    image.save("resized_microphone.png")


def _generate_chatgpt_image(user_text, assistant_output_text):
    """
    Generates a dall-e image based on given text (usually the output of the
    GPT assistant)
    """
    logging.info("Generating image")
    image_prompt = (
        f"{prompts.assistant_image_prompt}\n{user_text}\n{assistant_output_text}"
    )

    response = client.images.generate(
        model="gpt-image-1",
        prompt=image_prompt,
        size="1024x1024",
        quality="medium",
        n=1,
    )
    if response:
        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        with open("dalle_image.png", "wb") as image_file:
            image_file.write(image_bytes)

        # Resize the image to display on the smaller, 800x480 display. This
        # doesn't maintain the aspect ratio.
        image = Image.open("dalle_image.png")
        resized_image = image.resize((800, 480))
        resized_image.save("resized.png")
        helpers.display_image("resized.png")
        add_microphone_to_image()


def start_image_thread(input_text, assistant_output):
    global image_thread
    image_thread = threading.Thread(
        target=_generate_chatgpt_image,
        args=(input_text, assistant_output),
    )
    image_thread.should_abort_immediately = True
    image_thread.start()


def send_to_assistant(input_text, text_to_speech=True):
    """
    Send text to an OpenAI Assistant and gets the response to pass to Whisper
    and Dall-E.
    """

    # Encourage the GPT3 response to be brief. This is usually set on
    # the assistant prompt, however I've found responses can still be
    # rather long.
    current_datetime = datetime.now().strftime("%c")
    brief_prompt = "Remember to keep responses brief."
    amended_input_text = f"The date and time is {current_datetime}.\n{input_text}\n{brief_prompt}"

    logging.info(f"Input text: {amended_input_text}")

    message = client.beta.threads.messages.create(
        thread_id=assistant_thread.id, role="user", content=amended_input_text
    )

    run = client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant.id,
    )

    run_completed = False
    timeout_limit = 300
    timeout_counter = 0
    while not run_completed:
        if timeout_counter >= timeout_limit:
            logging.info("Timeout exceeded")
            timeout_counter = 0
            break
        run = client.beta.threads.runs.retrieve(
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
        thread_messages = client.beta.threads.messages.list(assistant_thread.id)
        # The most recent assistant's response will be the first item in the list
        assistant_output = thread_messages.data[0].content[0].text.value
    logging.info(f"Assistant output: {assistant_output}")

    start_image_thread(input_text, assistant_output)

    if text_to_speech:
        whisper_text_to_speech(assistant_output)


def send_image_to_chatgpt(base64_image, prompt):
    """
    Sends an image to ChatGPT Vision API for analysis. The Assistant API doesn't
    support images yet, so this workaround until then.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.openai_api_key}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": prompt
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
                }
            ]
            }
        ],
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    add_microphone_to_image()
