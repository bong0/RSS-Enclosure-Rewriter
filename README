RSS-Enclosure-Rewriter
======================

This is a podcast feed rewriter/modifier with cleanup support
This program is meant to be run after running podget (http://podget.sourceforge.net/)  which sets up a dir structure like:

  Category
    ^- Podcast Name
      ^- Episode

## Config suggestions:
In your .podget/podgetrc set the following:

  cleanup=0
  #playlist_namebase=New-

### Podget bugs
I experienced one bug in podget which comes from a failed workaround for bad-formatted filenames, therefore I suggest you to als set the following options

  filename_formatfix2=0
  filename_formatfix3=0
  filename_formatfix4=0



# The background
I wanted a personal podcast caching solution, because often servers are overcrowded upon release at times I listen (currently in the late evening).
So my solution consists of a cron-like script in daemon-tools which looks like this:

## run 
  
  #!/bin/sh -e
  RUNWHEN=",H=21"
  
  exec 2>&1 \
  rw-add n d1S now1s \
  rw-match \$now1s $RUNWHEN wake \
  sh -c '
  echo "@$wake" | tai64nlocal | sed "s/^/next run time: /"
  exec "$@"' arg0 \
  rw-sleep \$wake \
  $HOME/bin/fetchPodcasts.sh

## fetchPodcasts.sh
  #!/bin/bash
  HOME=/home/USER
  echo "[+] starting podget update now"
  $HOME/bin/podget -s --dir_config $HOME/.podget/ | uniq
  echo "[+] update finished"
  $HOME/scripts/cacher.py -oM

