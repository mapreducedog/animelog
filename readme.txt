

examples:
    "Part IV: A New show"
    animelog "~/Videos/The Foobar - 01.mkv"
    will play the supplied file and log it to the current watchers.

    "Normal-mode"
    animelog -pnct "The Foobar" (or animelog --play --next --current --title "The Foobar")
        play the next episode of "The Foobar", if all current watchers are watching it. (and record it to the log of the current watchers)
    
    "What's out?"
    animelog -nacu  (or animelog --next --airin --current --unwatched)
        output the next episode of airing shows that current watchers are watching, if a new episode has aired.
    
    "
    "What were we watching?"
    animelog -sc alice bob 
    set the current watchers to alice and bob, and output shows both Alice & Bob are watching with the last watched episode.    
    alternatively you could use "animelog -w Alice Bob" here, which has the same output, but does not change the active watchers
    

    "Just play something"
    animelog -pnc (or animelog --play --next --current)
        sequentially play the next episode of all shows the current watchers are watching 
        (if the files are on the machine ofcourse). 
    
