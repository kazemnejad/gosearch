import os

nwjs = os.path.join(os.path.expanduser("~"), "Apps", "nwjs", "nw")
os.system(nwjs + " " + os.getcwd())
