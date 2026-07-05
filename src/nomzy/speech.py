import json
import random

from .paths import get_speech_path


DEFAULT_SPEECH = {
    "idle": [
        "woof!",
        "hi!",
        "still here!",
        "good job!",
        "sniff sniff",
        "tail wag!",
        "hmm...",
        "doing great!",
        "hello!",
        "tiny steps!",
    ],
    "talk": [
        "hello!",
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
    ],
    "treat": [
        "nom nom!",
        "snack!",
        "thank you!",
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

    if not speech_path.exists():
        return speech

    try:
        with open(speech_path, "r", encoding="utf-8") as file:
            user_speech = json.load(file)

        if not isinstance(user_speech, dict):
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

    except Exception:
        pass

    return speech


def choose_speech(speech: dict, category: str, fallback_category: str = "idle") -> str:
    choices = speech.get(category)

    if not choices:
        choices = speech.get(fallback_category)

    if not choices:
        choices = DEFAULT_SPEECH["idle"]

    return random.choice(choices)