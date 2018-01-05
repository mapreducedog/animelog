#!/bin/bash
filename="$1"	
location=$(dirname $(realpath $0))

if [ -f "$filename" ]
   then
   python2 -u "$location"/"animelog.py" "$@" & disown
   mpv --quiet "$filename"
else
    python2 -u "$location"/"animelog.py" "$@"
fi
