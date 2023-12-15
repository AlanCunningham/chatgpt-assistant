import apprise
import settings


def send(title, message, image_path):
    """
    Sends a message using Apprise
    :param title: The string for the title of the notification
    :param message: The string of the message to send
    """
    if settings.apprise_services:
        # Create an Apprise instance
        app = apprise.Apprise()
        for service in settings.apprise_services:
            app.add(service)

        app.notify(
            body=message,
            title=title,
            attach=image_path
        )


if __name__ == "__main__":
    send("", "", "dalle_image.png")
