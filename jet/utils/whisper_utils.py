import os

import dotenv
import openai

dotenv.load_dotenv()

OPENAI_WHISPER_API_TYPE = os.getenv("OPENAI_WHISPER_API_TYPE")
OPENAI_WHISPER_API_BASE = os.getenv("OPENAI_WHISPER_API_BASE")
OPENAI_WHISPER_API_KEY = os.getenv("OPENAI_WHISPER_API_KEY")
OPENAI_WHISPER_API_VERSION = os.getenv("OPENAI_WHISPER_API_VERSION")
OPENAI_WHISPER_MODEL_NAME = os.getenv("OPENAI_WHISPER_MODEL_NAME")


def transcribe(wav_file):
    assert OPENAI_WHISPER_API_TYPE in [None, "azure", "openai"]
    kwargs = {
        "file": wav_file,
        "api_type": OPENAI_WHISPER_API_TYPE,
        "api_base": OPENAI_WHISPER_API_BASE,
        "api_key": OPENAI_WHISPER_API_KEY,
        "api_version": OPENAI_WHISPER_API_VERSION,
    }
    if OPENAI_WHISPER_API_TYPE == "azure":
        kwargs["model"] = OPENAI_WHISPER_MODEL_NAME
        kwargs["deployment_id"] = OPENAI_WHISPER_MODEL_NAME
    else:  # openai
        kwargs["model"] = OPENAI_WHISPER_MODEL_NAME

    transcript = openai.Audio.transcribe(**kwargs)

    return transcript.text


if __name__ == "__main__":
    file = open("/path/to/sample.wav", "rb")
    print(transcribe(file))
