#!/usr/bin/python3

import os
import sys


HOME_DIR = os.path.expanduser("~")
HIST_LOC = os.path.join(HOME_DIR, ".hist_ng.txt")

def main():
    out_file = open(HIST_LOC, 'a')
    out_text = '", "'.join(sys.argv)
    out_file.write('["' + out_text + '"]\n')
    out_file.close()
    pass


if __name__ == "__main__":
    main()
