from datetime import datetime
import helpers
import gpt
import time

is_family_bell_active = False
current_bell_time = ""
current_step = 0

schedule = {
    "18:30": {
        "title": "It's almost time for bed!",
        "ending": "You're all ready for bed - enjoy your bedtime story, and good night.",
        "steps": [
            "Brush your teeth and make sure they're all nice and clean.",
            "Put your pyjamas on.",
            "Think of something lovely that happened today.",
        ],
        "prompt": "A fun picture of a little dinosaur, in his pyjamas, doing the following:",
    }
}


def run_through_steps(input_text):
    """
    Checks the user's input and runs through the steps
    """
    global is_family_bell_active, current_bell_time, current_step
    confirmation_phrases = [
        "start",
        "ready",
        "yes",
        "yeah",
        "let's go",
        "next",
        "step",
        "done",
        "all done",
        "finished",
        "already",
    ]
    negative_phrases = [
        "no",
        "nope",
        "stop",
        "cancel",
        "never mind",
        "nevermind",
    ]
    if any(
        confirmation_phrase in input_text
        for confirmation_phrase in confirmation_phrases
    ):
        if current_step > len(schedule[current_bell_time]["steps"]) - 1:
            # Ran through all steps, reset the family bell
            announcement = schedule[current_bell_time]["ending"]
            image_prompt = f"{schedule[current_bell_time]['prompt']} {schedule[current_bell_time]['ending']}"
            current_step = 0
            is_family_bell_active = False
            current_bell_time = ""
        else:
            print(
                f"Current step: {current_step} | Number of steps: {len(schedule[current_bell_time]['steps']) - 1}"
            )
            print(
                f"{schedule[current_bell_time]['prompt']} {schedule[current_bell_time]['steps'][current_step]}"
            )

            image_prompt = f"{schedule[current_bell_time]['prompt']} {schedule[current_bell_time]['steps'][current_step]}"
            if current_step == 0:
                announcement_start = (
                    "Great! Let's get started then! Your first step is to"
                )

            elif current_step == len(schedule[current_bell_time]["steps"]) - 1:
                announcement_start = "Your final step is to"

            else:
                announcement_start = "Your next step is to"

            announcement = f"{announcement_start} {schedule[current_bell_time]['steps'][current_step]}"
            current_step += 1

        gpt.start_image_thread(image_prompt, "")
        gpt.whisper_text_to_speech(announcement)

    elif any(negative_phrase in input_text for negative_phrase in negative_phrases):
        print("Stopping family bell")
        # Reset the family bell
        current_step = 0
        is_family_bell_active = False
        current_bell_time = ""


def announce_family_bell(schedule_time):
    """
    Announce the family bell
    """
    announcement = f"""
        {schedule[schedule_time]['title']}. It looks like you have
        {len(schedule[schedule_time]['steps'])} steps. Let me know when you're
        ready to start, and say done when you've finished each step!
    """

    gpt.whisper_text_to_speech(announcement, insert_audio_path="audio/glimpse.m4a")


def check_time():
    """
    Checks the current time and updates athe family bell status
    """
    global is_family_bell_active, current_bell_time

    while True:
        now = str(datetime.now().strftime("%H:%M"))
        if any(now in schedule_time for schedule_time in schedule):
            # print(f"Schedule time: {schedule_time}")
            # Activate the family bell status
            is_family_bell_active = True
            bell = schedule[now]["title"]
            current_bell_time = now
            print(f"Activating family bell: {bell}")
            helpers.display_image("assistant_images/family_bell.png")
            announce_family_bell(now)
        # else:
        # is_family_bell_active = False
        time.sleep(60)


if __name__ == "__main__":
    gpt.setup()
    check_time()
