#!/bin/bash
filename="$1"	
location=$(dirname $(realpath $0))

if [ -f "$filename" ]
   then
   python2 "$location"/"animelog.py" "$@" & disown
   mpv "$filename">/dev/null 2>&1
else
    python2 "$location"/"animelog.py" "$@"
fi
