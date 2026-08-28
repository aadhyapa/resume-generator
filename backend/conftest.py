import sys
from pathlib import Path

# Make the backend package importable (app, agents, algorithms, llm, models, ...)
# for every test under backend/tests, without each test file needing its own
# sys.path.append hack.
sys.path.insert(0, str(Path(__file__).resolve().parent))
