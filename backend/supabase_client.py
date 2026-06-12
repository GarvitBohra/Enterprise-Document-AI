import os
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
except Exception:
    create_client = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase = None


def get_supabase():
    global supabase
    if supabase is not None:
        return supabase

    if not create_client or not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        print(f"Supabase client init failed: {exc}")
        supabase = None
    return supabase
