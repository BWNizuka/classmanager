import os
from dotenv import load_dotenv

load_dotenv()
print("DEBUG URI:", os.getenv("MONGO_URI"))
