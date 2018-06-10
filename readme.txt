
Flags:
    animelog has four types of flags:
    selection flags: (such as --title, --current, --airing, )
         these specify what titles from the should be selected to perform actions on
    mutator flags: (such as --episode, --next, --date)
         these change change or add attributes to the current selection
    action flags: (such as --play, --finish, --db-alias, implicit print) 
         these perform actions with as input the selection after applying mutators.
    
    side-effect flags: (such as --set, --db-update, --help)
         these perform actions for their side effect, and do not require a selection of titles
    
    a query tackes the general form of :
   [<selection> ...] [<mutator> ...][<action>][<side-effect>]
    that is to say
    a query can consists of any combination any number of selection and mutator flag, an optionally one action flags and/or one side-effect flags (Note that the only useful side-effect flag in combination with an action flag is --set)
    take for example the query "animelog --play --next --current --title 'Foobar Adventures'", 
this has the selection flags : --current and --title, the mutator flag --next, and the action flag --play.
    
     if no side-effect flag or action flag has been declared, but a mutator or selection flag has, then the result of applying those specified flags will outputted to stdout.
     


addding aliases:
    if the name of a show as it exists in your log, is different from that in the remote database, you can add an alias.
    animelog --title "Foobar Adventures" --db-alias "The Legendary Adventures of Foobar - The Adventuring"
   
    if this is still ambiguous, (for example, if two shows in the remote database have exactly the same name),
you can also alias by id by setting the alias to "id:<id-number>". Suggested ID-numbers are reported when updating the local database: example
    animelog --title "Foobar Adventures" --db-alias "id:123456"
   

shows not supplied by external database:
    shows that are not supplied by the remote database, are regarded as if no episodes have aired, and thus when 
    querying with the -n flag, will be suppressed. 
    If this is not what you want, you can add the number of episodes (in this example 45),
    of the title by using the --db-set-episodes flag as follows:
    animelog --title "Foobar Adventures" --db-set-episodes 45
 
    this will put the show to "having all episodes aired" and thus always be displayed when you query with the -n flag.
    this will persist over full-updates, and the show will automatically finish when you watch the last episode.
   
    if the show your watching has season specification, you should do so as well when setting total number of episodes, you can use any 
    format that is also parsed by --simulate e.g.
    animelog --title "Foobar Adventures" --db-set-epsodes s03e12 
 
managing the local database:
    animelog is designed to work even without internet, so rather than updating the local database of airing times whenever a new show is watched,
    this is done by a commandline flag.  
    
    if you just want to add newly watched shows to the database use:
    animelog --db-update
    which will copy titles in the log that do not have entries in the local database from the remote to the local database. It will not change anything else about the database.
    
    animelog --db-full-update
    will perform a full update, which includes the partial update, but also updates other entries by reading them again from the remote database. 
    a common thing that might change is the airing status of the show as a result of this.
    
    animelog --db-minimize 
    will remove all shows from the database that arent being watched, thus reducing the filesize of the database
    

autocompletion:
  if you have bash autocompletion enabled, you can autocomplete flags and arguments (by pressing tab). For titles of shows, autocompletion will only suggest those of current watchers. if you just changed current_watchers, be sure to start a new bash session, to reload the newest autocompletion options. Likewise, a newly watched show will only be suggested with autocompletion in bash sessions after it was first played.




examples:
    "Part IV: A New show"
    animelog "~/Videos/The Foobar - 01.mkv"
    will play the supplied file and log it to the current watchers.

    "Normal-mode"
    animelog -pnct "The Foobar" (or animelog --play --next --current --title "The Foobar")
        play the next episode of "The Foobar", if all current watchers are watching it. (and record it to the log of the current watchers)
    
    "What's out?"
    animelog -nacu  (or animelog --next --airing --current --unwatched)
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
    
Warnings: 
    be careful with --drop/--finish, as it will drop/finish everything in the selection from the current watchers, as long as at least selection criteria has been specified. 
    so --drop --current will drop all shows that would otherwise be displayed by "--current"
    if you want to test, use the selection commands without --drop, and see if you're happy with the selection. 

