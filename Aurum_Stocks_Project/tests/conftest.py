"""Put src/ on sys.path so `import aurum_stocks` works under pytest (src layout)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
