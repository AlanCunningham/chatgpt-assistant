from datetime import datetime
import helpers
import gpt
import random
import time

is_family_bell_active = False
current_bell_time = ""
current_step = 0

art_styles = [
    "cartoon",
    "realistic",
    "hand drawn",
    "cute picture that would look nice in a nursery",
    "drawn with crayons, imperfect, with some of the colouring going outside of the lines",
    "a child's drawing (simple, scribbly, cute)",
]

animal_types = [
    "a dog",
    "a sheep",
    "a cow",
    "a dinosaur",
    "an animal",
]

schedule = {
    "18:30": {
        "title": "It's almost time for bed!",
        "ending": "You're all ready for bed - enjoy your bedtime story, and good night.",
        "steps": [
            "Put your pyjamas on.",
            "Have a lovely warm milk",
            "Brush your teeth and make sure they're all nice and clean.",
        ],
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
        "first",
        "all ready",
    ]
    negative_phrases = [
        "stop",
        "cancel",
    ]
    if any(
        confirmation_phrase in input_text
        for confirmation_phrase in confirmation_phrases
    ):
        helpers.play_audio("audio/epiphany.m4a")
        image_prompt = f"In the following art style ({random.choice(art_styles)}), generate a fun little picture of {random.choice(animal_types)}, doing the following:"
        if current_step > len(schedule[current_bell_time]["steps"]) - 1:
            # Ran through all steps, reset the family bell
            announcement = schedule[current_bell_time]["ending"]
            image_prompt = f"{image_prompt} {schedule[current_bell_time]['ending']}"
            current_step = 0
            is_family_bell_active = False
            current_bell_time = ""
        else:
            print(
                f"Current step: {current_step} | Number of steps: {len(schedule[current_bell_time]['steps']) - 1}"
            )
            print(
                f"{schedule[current_bell_time]['steps'][current_step]}"
            )

            image_prompt = f"{image_prompt} {schedule[current_bell_time]['steps'][current_step]}"
            if current_step == 0:
                announcement_start = (
                    "Your first step is to"
                )

            elif current_step == len(schedule[current_bell_time]["steps"]) - 1:
                announcement_start = "Your final step is to"

            else:
                announcement_start = "Your next step is to"

            announcement = f"{announcement_start} {schedule[current_bell_time]['steps'][current_step]}"
            current_step += 1

        print(image_prompt)
        gpt.start_image_thread(image_prompt, "")
        gpt.whisper_text_to_speech(announcement)

    elif any(negative_phrase in input_text for negative_phrase in negative_phrases):
        print("Stopping family bell")
        gpt.whisper_text_to_speech("Stopping family bell")
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
