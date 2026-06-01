'''
Manual LinkedIn login helper.

Opens Chrome using the SAME automation profile the bot uses, navigates to the
LinkedIn login page, and waits for you to log in by hand (handy for 2FA or
captchas). Your session is saved into the automation profile, so when you run
the bot afterwards it is already logged in and goes straight to applying.

Run it on your own machine with:
    python manual_login.py
'''

# Importing this opens Chrome (matching driver + persistent automation profile)
from modules.open_chrome import driver
from modules.helpers import print_lg

import pyautogui


def main() -> None:
    try:
        print_lg("Opening LinkedIn login page for manual sign-in...")
        driver.get("https://www.linkedin.com/login")

        pyautogui.confirm(
            "Log in to LinkedIn in the browser window that just opened.\n\n"
            "Complete any 2FA / captcha until you reach your LinkedIn home feed.\n\n"
            "Then click the button below to SAVE the session.",
            "Manual LinkedIn Login",
            ["OK, I'm logged in"],
        )

        # Nudge to the feed so the login cookies are definitely written
        try:
            driver.get("https://www.linkedin.com/feed/")
        except Exception:
            pass

        print_lg("Session saved to the automation profile.")
        print_lg("You can now run the bot (Save & Run) - it will already be logged in.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
