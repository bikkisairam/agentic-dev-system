import sys
import os

# Ensure the project root is on sys.path so generated.{slug}.app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
