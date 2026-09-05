import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# Path() gives us the folder this file lives in. We go up 2 folders
# (fetch_data -> creator_roi -> src) to reach src/, then up 1 more to reach
# the project's root folder. This way the code works no matter where you
# run it from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# load_dotenv reads the .env file and makes its values available through
# os.environ (a dictionary-like object holding environment variables)
load_dotenv(PROJECT_ROOT / ".env")


def _get_secret(key_name):
    """Checks Streamlit Cloud's secrets first (for deployment), falls back
    to the local .env file (for running on your own machine)."""
    try:
        return st.secrets[key_name]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key_name)


def load_settings():
    """
    Reads config/settings.yaml and returns it as a plain Python dictionary,
    the same way you'd load a JSON file with json.load() (Day 15).
    """
    settings_path = PROJECT_ROOT / "config" / "settings.yaml"
    with open(settings_path, "r") as f:
        settings_dict = yaml.safe_load(f)
    return settings_dict


def get_youtube_api_key():
    """
    Reads the YOUTUBE_API_KEY value from .env or Streamlit secrets.
    Raises a custom, clear error (like Day 17 - custom exceptions /
    defensive programming) if the key is missing, instead of letting the
    program crash later with a confusing error.
    """
    api_key = _get_secret("YOUTUBE_API_KEY")
    if api_key is None:
        raise ValueError(
            "No YOUTUBE_API_KEY found. "
            "Create a .env file in the project folder containing:\n"
            "YOUTUBE_API_KEY=your_key_here"
        )
    return api_key


def get_data_raw_folder():
    """Returns the path to data/raw, creating it if it doesn't exist yet."""
    folder_path = PROJECT_ROOT / "data" / "raw"
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def get_supabase_connection_params():
    
    params = {
        "host": _get_secret("SUPABASE_HOST"),
        "port": _get_secret("SUPABASE_PORT") or "5432",
        "database": _get_secret("SUPABASE_DB") or "postgres",
        "user": _get_secret("SUPABASE_USER") or "postgres",
        "password": _get_secret("SUPABASE_PASSWORD"),
    }
    missing = [k for k, v in params.items() if not v]
    if missing:
        raise ValueError(f"Missing required Supabase config: {', '.join(missing)}")
    return params


def get_gemini_api_key():
    """Reads the Gemini API key from .env or Streamlit secrets."""
    api_key = _get_secret("GEMINI_API_KEY")
    if api_key is None:
        raise ValueError(
            "No GEMINI_API_KEY found. Add it to your .env file - "
            "see setup instructions."
        )
    return api_key