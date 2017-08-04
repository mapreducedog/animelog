#!/bin/bash
filename="$1"	
location=${0/animelog.sh}
if [ -f "$filename" ] #test if this is a file
then
	mpv "$filename" > /dev/null 2>&1 & disown
	python2 "$location""animelog.py" "$filename"
else
	python2 "$location""animelog.py" "$@"
fi


