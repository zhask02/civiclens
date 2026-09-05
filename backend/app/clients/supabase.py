import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../.env")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"],
)