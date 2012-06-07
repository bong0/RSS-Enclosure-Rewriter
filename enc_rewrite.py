#!/usr/bin/env python3
# Podcast feed rewriter/modifier with cleanup support
# This program is meant to be run after running a podcatcher
#(tested w/ podget) which sets up a dir structure like:
# Category
#  ^- Podcast Name
#    ^- Episode
# Author: bongo Dec 2011 - Jan 2012

import sys
import os
import re
import time
import unicodedata
import codecs
from xml.dom import minidom
from xml.etree import ElementTree as etree
from urllib.request import urlopen
from urllib.parse import urlparse, quote

##### CONSTANTS #######
# please, dirs always w/ trailing "/"
podcastDir = str("/var/www/podcasts/") # directory accessible by webserver to serve podcasts
externalUrl = "http://example.com/podcasts/" # url pointing to podcastdir as seen from client
feedDir = str("/var/www/podcasts/feeds/") # directory which serves the modified feeds to the client
podget_cfgdir = str("/home/$USER/.podget/") # directory with your podget configuration files
keepPodcasts = 3 # keep n last podcasts of each feed
#######################
categories = set()
localPodcasts = dict()
podcastNames = [] #list of all podcast names

output = "verb"
for arg in sys.argv:
  if(arg == "-oM"):
   output = "min"
  elif(arg == "-oN"):
   output = None

#prepare generation of opml file that includes all podcasts
xml = minidom.Document()
opml = xml.createElement('opml')
opml.appendChild(xml.createElement('head'))
body = xml.createElement('body')

#prepare feed input
with open(podget_cfgdir+"serverlist", "r") as servers: #read and extract rss feed URLs from settings
  for line in servers.readlines():
    if(re.match("^\s?#", line)): #skip comments
       continue
    url = line.split()[0]

    if(re.search("/$", url)):
      url = url[:-1]
    feedFile = urlparse(url).path.split("/")[-1]
    if(output and output=="verb"):
      print("fetching "+ line.split()[0])
    feed = urlopen(line.split()[0]).read()

    categories.add(line.split()[1]) #add category of feed
    
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
            if(output and (output=="verb" or output=="min")):
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
   
    podcastNames.append(podcastName)

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
      for badEnclosure in item.iterfind(".*content"):
        tree.remove(badEnclosure)
      
    with open(feedDir+podcastName+".rss", "wb") as feed:
      feed.write(etree.tostring(tree, encoding="UTF-8"))
    #add feed to opml
    ##get html url
    htmlUrl = tree.find("channel/link").text
    podTitle = (tree.find("channel/title").text).translate(table)
    outline = xml.createElement('outline') 
    outline.setAttribute('title',podTitle) 
    outline.setAttribute('htmlUrl',htmlUrl)
    outline.setAttribute('xmlUrl',externalUrl+"feeds/"+podcastName+".rss")
    body.appendChild(outline)

#close opml
opml.appendChild(body)
xml.appendChild(opml)
opmlFile = codecs.open(podcastDir+"feeds/all.opml", "w", "utf-8")
xml.writexml(opmlFile, "    ", "", "\n", "UTF-8")

#remove feeds which weren't refreshed (those went out of config)
for file in os.listdir(feedDir):
  if(str(file)[:-4] in podcastNames or str(file) == "all.opml" or str(file)==".htaccess"): #if podcastname was processed, we do nothing
    if(output=="verb"):
      print("skipping file "+str(file)+" on old-feed-cleanup")
    continue
  else:
    try:
      if(output=="verb"):
        print("removing file "+str(file)+" on old-feed-cleanup")
      os.remove(feedDir+str(file))
    except OSError:
      if(output):
        print("could not remove old rss feed from "+feedDir+"!")
    
#chmod feeds
for file in podcastNames:
  file+=".rss"
  try:
    os.chmod(feedDir+file, 0o604)
  except:
    if(output):
      print("could not chmod feed/opml: "+file)

#chmod opml
  try:
    os.chmod(feedDir+"all.opml",0o604)
  except:
    if(output):
      print("could not chmod all.opml")


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
  for dir in os.listdir(podcastDir+category):
      os.chmod(podcastDir+category+"/"+dir, 0o701)

if(output):
  print("Rewrote "+str(len(localPodcasts))+" enclosures successfully")
