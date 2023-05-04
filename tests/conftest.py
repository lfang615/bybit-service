import sys
from pathlib import Path  
from dotenv import load_dotenv
import sys
from pathlib import Path

load_dotenv()
project_directory = Path(__file__).parent.parent
sys.path.insert(0, str(project_directory))
