import logging
import time
import vlc
import prompts
import settings
from openai import OpenAI
from pathlib import Path


def generate_chatgpt_image(openai_client, input_text):
    """
    Generates a dall-e image based on given text (usually the output of the
    GPT assistant)
    """
    image_prompt = f"{prompts.assistant_image_prompt}\n{input_text}"

    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    print(response)


def get_assistant(openai_client):
    """
    Returns an already-created Assistant.
    """
    assistant = openai_client.beta.assistants.retrieve(settings.openai_assistant_id)
    print(assistant)
    return assistant


def whisper_text_to_speech(openai_client, text_to_say):
    speech_file_path = Path(__file__).parent / "speech.mp3"
    response = openai_client.audio.speech.create(
        model="tts-1", voice="nova", input=text_to_say
    )
    response.stream_to_file(speech_file_path)

    player = vlc.MediaPlayer(speech_file_path)
    player.play()
    time.sleep(1)
    # while player.is_playing():
    # time.sleep(1)


def send_to_assistant(openai_client, assistant, input_text):
    thread = openai_client.beta.threads.create()
    message = openai_client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=input_text
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    run_completed = False
    while not run_completed:
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        if run.status == "completed":
            run_completed = True
        time.sleep(1)

    thread_messages = openai_client.beta.threads.messages.list(thread.id)
    # The most recent assistant's response will be the first item in the list
    assistant_output = thread_messages.data[0].content[0].text.value
    print(assistant_output)

    whisper_text_to_speech(openai_client, assistant_output)

    image_response = generate_chatgpt_image(client, assistant_output)
    print("Finished")


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

    test_input = "Who is Brian Limond?"
    assistant = get_assistant(client)
    send_to_assistant(client, assistant, test_input)
