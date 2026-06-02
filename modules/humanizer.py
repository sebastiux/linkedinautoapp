'''
Human-like behavior helpers to make the bot's interactions look less robotic
(randomized timing, human-paced typing, occasional scrolling).

Controlled by `humanize_actions` in config/settings.py. These reduce obvious
automation patterns but do NOT guarantee you won't be detected - automating
LinkedIn is against its Terms of Service and can get an account restricted.
Use moderate volume and supervise the run.
'''

import random

from modules.helpers import sleep

# Backwards-compatible defaults if settings.py doesn't define these yet.
try:
    from config.settings import humanize_actions
except Exception:
    humanize_actions = True
try:
    from config.settings import min_action_delay, max_action_delay
except Exception:
    min_action_delay, max_action_delay = 0.6, 2.5
try:
    from config.settings import apply_pause_min, apply_pause_max
except Exception:
    apply_pause_min, apply_pause_max = 2.5, 9.0


def human_delay(min_s: float = None, max_s: float = None) -> None:
    '''Sleeps for a random duration to mimic human reaction time.'''
    if not humanize_actions:
        return
    a = min_action_delay if min_s is None else min_s
    b = max_action_delay if max_s is None else max_s
    if b < a:
        b = a
    sleep(random.uniform(a, b))


def between_applications_delay() -> None:
    '''A slightly longer, randomized pause between job applications.'''
    if not humanize_actions:
        return
    sleep(random.uniform(apply_pause_min, apply_pause_max))


def human_type(element, text: str) -> None:
    '''
    Types `text` into `element` character by character with small random delays,
    which looks far more human than an instant send_keys() of the whole string.
    '''
    text = "" if text is None else str(text)
    if not humanize_actions:
        element.send_keys(text)
        return
    try:
        for ch in text:
            element.send_keys(ch)
            sleep(random.uniform(0.03, 0.16))
            # occasional tiny "thinking" pause
            if random.random() < 0.06:
                sleep(random.uniform(0.2, 0.6))
    except Exception:
        # Fall back to a plain fill if per-character typing fails for any reason
        try:
            element.send_keys(text)
        except Exception:
            pass


def random_scroll(driver, min_px: int = 120, max_px: int = 600) -> None:
    '''Scrolls the page by a random amount, like a human reading.'''
    if not humanize_actions:
        return
    try:
        driver.execute_script(f"window.scrollBy(0, {random.randint(min_px, max_px)});")
        human_delay(0.3, 1.0)
    except Exception:
        pass
