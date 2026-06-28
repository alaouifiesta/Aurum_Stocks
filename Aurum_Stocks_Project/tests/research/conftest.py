import os, sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)                       # import research
sys.path.insert(0, os.path.join(_root, "src")) # import aurum_stocks
