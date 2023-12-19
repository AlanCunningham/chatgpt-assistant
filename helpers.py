import vlc
import subprocess
import time


def play_audio(audio_file_path):
    """
    Plays a given audio file and waits until it's finished playing
    """
    player = vlc.MediaPlayer(audio_file_path)
    player.play()
    time.sleep(1)
    # Ensure the program doesn't cut off the text to speech
    while player.is_playing():
        time.sleep(1)


def display_image(image_file_path):
    """
    Displays an image to the console framebuffer imageviewer (fbi)
    """
    # Remove the current image by killing the fbi process
    subprocess.call(f"sudo killall -15 fbi", shell=True)
    # Display the new image
    subprocess.call(f"sudo fbi -T 1 {image_file_path} --noverbose &", shell=True)
