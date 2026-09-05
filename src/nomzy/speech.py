import json
import logging
import random

from .paths import get_speech_path


LOGGER = logging.getLogger(__name__)


DEFAULT_SPEECH = {
    "idle": [
        "woof!",
        "hi, {name}!",
        "still here!",
        "good job, {name}!",
        "sniff sniff",
        "tail wag!",
        "hmm...",
        "doing great!",
        "hello!",
        "tiny steps!",
    ],
    "talk": [
        "hello, {name}!",
        "woof!",
        "I'm here!",
        "what's up?",
        "tiny dog thoughts...",
    ],
    "pet": [
        "happy!",
        "tail wag!",
        "again!",
        "hehe!",
        "thanks, {name}!",
    ],
    "treat": [
        "nom nom!",
        "snack!",
        "thank you, {name}!",
        "treat!",
    ],
    "ball": [
        "ball?!",
        "throw it!",
        "again again!",
        "I saw it!",
    ],
    "pause": [
        "paused",
        "I'll wait!",
    ],
    "resume": [
        "back!",
        "let's go!",
    ],
    "reset": [
        "here!",
        "I'm back!",
    ],
    "hide_return": [
        "back!",
        "hello again!",
    ],
}


def load_speech() -> dict:
    speech_path = get_speech_path()

    speech = {
        category: list(lines)
        for category, lines in DEFAULT_SPEECH.items()
    }

    try:
        if not speech_path.exists():
            LOGGER.warning(
                "Speech configuration %s is missing; using built-in speech",
                speech_path,
            )
            return speech

        with open(speech_path, "r", encoding="utf-8") as file:
            user_speech = json.load(file)

        if not isinstance(user_speech, dict):
            LOGGER.warning(
                "Speech configuration %s is not an object; using defaults",
                speech_path,
            )
            return speech

        for category, lines in user_speech.items():
            if not isinstance(category, str):
                continue

            if not isinstance(lines, list):
                continue

            clean_lines = [
                line
                for line in lines
                if isinstance(line, str) and line.strip()
            ]

            if clean_lines:
                speech[category] = clean_lines

    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        LOGGER.warning(
            "Could not load speech configuration from %s; using defaults: %s",
            speech_path,
            error,
        )

    return speech


def choose_speech(speech: dict, category: str, fallback_category: str = "idle") -> str:
    choices = speech.get(category)

    if not choices:
        choices = speech.get(fallback_category)

    if not choices:
        choices = DEFAULT_SPEECH["idle"]

    return random.choice(choices)
