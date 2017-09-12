import sys
import json

def convert(filename):
    with open(filename, 'r') as infile:
        data = json.load(infile)
    new_data = {}
    for key, value in data.iteritems():
        new_data[key] = {'watchers' : value }
    with open(filename, 'w') as outfile:
        json.dump(new_data, outfile, indent = 1)
    

if __name__ == '__main__':
    if len(sys.argv) > 1:
        convert(sys.argv[-1])
