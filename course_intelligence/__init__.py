"""Course Intelligence — transforms instructional content into structured
learning elements classified against Bloom's taxonomy."""

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
except ImportError:
    pass
