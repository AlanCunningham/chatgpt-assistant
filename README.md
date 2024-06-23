# ChatGPT Assistant

A ChatGPT assistant connected to a small Raspberry Pi display, with voice activation (using [porcupine](https://github.com/Picovoice/porcupine))
and image generation (using Dall-E).

![image](https://github.com/AlanCunningham/chatgpt-assistant/assets/9663408/74424f3f-2209-4c42-8904-15d3c6e50b35)

## Overview and features
The display behaves a bit like a Google Home display, but with ChatGPT and Dall-E.
- Hotword activation is handled offline by [porcupine](https://github.com/Picovoice/porcupine).  Saying the default hotword, "Porcupine",
activates the display and starts listening for input.
- Speech is then recognised by Google text to speech.
- The speech input is sent to the ChatGPT Assistant API.
- The ChatGPT output is sent to the OpenAI Whisper API, to get high quality speech synthesis. This is then played on the display's speakers.
- Meanwhile, both the user input and ChatGPT output is sent to Dall-E 3.  The output image is downloaded, resized for my display (800x480), and
displayed to the user.

The whole process takes about 10-20 seconds.

There's also a few custom commands, that if recognised will bypass the above process and do something else.  For example:
- Saying an included "cancel" command will stop the display listening to user input and revert back to waiting for hotword activation.
- Saying an included "Send that to me" or "Send that on telegram" command will send the most recently generated image to a given chat service
using [apprise](https://github.com/caronc/apprise).  The image will also be saved to the "saved_images" directory.  I've commited my
saved images to this repo.
- Saying an included "Show me a random picture" command will choose an image from the saved_images directory at random and display to the user.

Optionally, you can also run the **scheduled_image.py** file on a cronjob and it will create an image based on the topics you've talked about with
ChatGPT in the current session.  Sessions are recreated on application restarts.

## API keys
This project requires an OpenAI API key to make the requests to ChatGPT Assistant, Whisper, and Dall-E.  **These do cost money** - the amount of which
may change over time.  Image generation with Dall-E 3 is the bulk
of the cost.

You will need to create a [ChatGPT Assistant](https://platform.openai.com/docs/assistants/overview) and save the `assistant_id` to settings.py.  As part
of this process, you will set a prompt on the ChatGPT Assistant website.  The prompt I've set up is:

> You are a helpful voice assistant.  You are based in [location and country].
> 
> If asked to create an image, imagine and give a description of what the image might look like. Through this, you are able to create images.
> 
> Keep responses brief.


You will also need a [porcupine API key](https://picovoice.ai/platform/porcupine/).  While porcupine hotword detection is handled offline, it looks like
the API key limits the amount of devices you can run it on at the same time.  API usage is free for at least one device.

## Hardware
Here's a list of hardware I'm using:
- A Raspberry Pi 4 - though this might run on previous versions.
- The official [Raspberry Pi touchscreen display](https://www.raspberrypi.com/documentation/accessories/display.html), which has a resolution of 800x480.
Images from Dall-E default to 1024x1024, so I'm resizing them to 800x480 for this display. This does lose the aspect ratio in the process.
- A USB microphone
- Some speakers


## Installation
This project is intended to be installed onto a Raspberry Pi using Raspberry PI OS-Lite (terminal-only mode with no desktop environment).  As such, I had to
install the following global packages
```
sudo apt-get install python3-dev
sudo apt-get install portaudio19-dev python-pyaudio python3-pyaudio
sudo apt-get install fbi
```

Next, clone the project and install the dependencies into a python virtual environment:
```
# Clone the repository
$ git clone git@github.com:AlanCunningham/chatgpt-assistant.git

# Create a python virtual environment
$ python3 -m venv venv

# Activate the virtual environment
$ source venv/bin/activate

# Install the python dependencies using the requirements.txt file provided
(venv) $ pip install -r requirements.txt
```

Enter your Open AI, your ChatGPT Assistant `assistant_id`, and porcupine API keys into settings.py in the designated sections. Optionally, you can also provide a chat service (such as Telegram)
if you want to be able to send generated images to yourself.  **Make sure not to commit any of these keys in this file.**

Start the program:
```
(venv) $ python main.py
```
Say "Porcupine" to activate the display to start listening to input.
