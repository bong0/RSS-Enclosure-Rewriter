#!/usr/bin/env python3
# Podcast feed rewriter/modifier with cleanup support
# This program is meant to be run after running a podcatcher
#(tested w/ podget) which sets up a dir structure like:
# Category
#  ^- Podcast Name
#    ^- Episode
# Author: bongo Dec 2011

import sys
import os
import re
import time
import unicodedata
from xml.etree import ElementTree as etree
from urllib.request import urlopen
from urllib.parse import urlparse, quote

##### CONSTANTS #######
podcastDir = str("/var/www/virtual/bongo/html/podcasts/")
externalUrl = "http://bongo.scorpius.uberspace.de/podcasts/"
keepPodcasts = 3 # keep n last podcasts of each feed
#######################
categories = set()
localPodcasts = dict()

output = "verb"
for arg in sys.argv:
  if(arg == "-oM"):
   output = "min"
  elif(arg == "-oN"):
   output = None

#prepare feed input
with open("/home/bongo/.podget/serverlist", "r") as servers: #read and extract rss feed URLs from settings
  for line in servers.readlines():
    if(re.match("^\s?#", line)):
       continue
    url = line.split()[0]

    if(re.search("/$", url)):
      url = url[:-1]
    feedFile = urlparse(url).path.split("/")[-1]
    if(output and output=="verb"):
      print("fetching "+ line.split()[0])
    feed = urlopen(line.split()[0]).read()

    categories.add(line.split()[1]) #add category of #add category of feed
    
    #detect encoding of feed
    encoding = "UTF-8"
    match = re.findall("encoding=\".*\"", str(feed))[0]
    if(match):
      encoding = match.split("\"")[1]

    #prepare local link to files:
    for category in categories:
       for (path, dirs, files) in os.walk(podcastDir+category):
         for file in files:
           ctime = int(os.stat(os.path.join(path, file)).st_ctime)
           localPodcasts[os.path.join(path, file)] = ctime
       
       #cleanup old podcasts 
       for dir in os.listdir(podcastDir+category):
          dir = podcastDir+category+"/"+dir+"/"
          while(len(os.listdir(dir)) > keepPodcasts):             
            podclist = dict()
            for podc in os.listdir(dir):
              podclist[localPodcasts[dir+podc]] = dir+podc
            oldest = sorted(podclist)[0]
            os.remove(podclist[oldest])
            if(output and (output=="verb"||output="min")):
              print("removed "+podclist[oldest])
             
    
    parser = etree.XMLParser(feed, encoding=encoding)
    parser.feed(feed)
    tree = parser.close()

    podcastName = tree.find("channel/title")
    podcastName = podcastName.text
    table = {
          0xe4: "ae",
          ord('ö'): "oe",
          ord('ü'): "ue",
          ord('ß'): None,
        }
    podcastName = podcastName.translate(table)
    podcastName = re.sub("(\s)+", "_", podcastName)
    podcastName = re.sub(",", "", podcastName)
    podcastName = str(unicodedata.normalize('NFKD', podcastName).encode('ascii','ignore'))[2:-1]
    

    #process enclosures
    for item in tree.findall("channel/item"):
      for enclosure in item.iterfind("enclosure"):
        if(output and output=="verb"):
          print("found "+enclosure.attrib["url"])
        #find according local file
        podName = os.path.basename( urlparse(enclosure.attrib["url"]).path ) #extract filename
        podNameRE = re.compile(podName)
        if(output and output=="verb"):
          print("episode name:"+podName) 
        for podcast in localPodcasts.keys(): # search for file locally
          if(podNameRE.search(os.path.basename(podcast))):
            if(output and output=="verb"):
              print("RE matched!!")
            podcast = os.path.relpath(podcast, start=podcastDir)
            enclosure.attrib["url"] = quote(externalUrl+ podcast, safe=":/")
            if(output and output=="verb"):
              print("modded to "+enclosure.attrib["url"])
      
    with open("/home/bongo/html/podcasts/feeds/"+podcastName+".rss", "wb") as feed:
      feed.write(etree.tostring(tree, encoding="UTF-8"))

#chmod podcasts
for file in localPodcasts.keys():
  if(os.path.exists(podcastDir+file)):
    try:
      os.chmod(podcastDir+file, 0o604)
    except:
      print("could not chmod podcast: "+file)

#chmod category dirs
for category in categories:
  os.chmod(podcastDir+category, 0o701)

if(output):
  print("Rewrote "+str(len(localPodcasts))+" enclosures successfully")
