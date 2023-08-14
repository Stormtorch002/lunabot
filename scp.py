import sys
import os 


file = sys.argv[1]
folder = '/'.join(file.split('/')[:-1])
os.system(f'scp {file} vps:./bots/lunabot/{folder}')