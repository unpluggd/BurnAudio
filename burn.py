#!/usr/bin/env python2.7

'''
Based on: http://www.math.columbia.edu/~bayer/Python/iTunes/iTunes.py

Todo:
- replace print with logging
- clean-up functions
'''

import os
import sys
import shlex
import subprocess
import tempfile
import time
import argparse
from datetime import datetime
from shutil import copyfile
from multiprocessing import Process, Pool

from appscript import *

iTunes = None
tempfile.tempdir = '/tmp'

FAAD = ''.join(os.popen('which faad').readlines()).strip()
LAME = ''.join(os.popen('which lame').readlines()).strip()

if FAAD[5:] == 'not found':
  raise SystemExit('faad is not available. Cannot continue.')

if LAME[5:] == 'not found':
  raise SystemExit('lame is not available. Cannot continue.')

__cd_size__ = 734000000

__valid_kinds__ = [
  u'MPEG audio file'
]

__encodable_kinds__ = {
  u'Purchased AAC audio file': 'aac',
  u'AAC audio file': 'aac'
}

__track_lists__ = {}

__list_keys__ = ('title', 'artist', 'number', 'abspath', 'kind', 'size',)

__quality__ = {
  'low': '64',
  'med': '128',
  'high': '192'
}

class TrackNotFound(Exception): pass

def get_app():
  global iTunes
  if not iTunes:
    iTunes = app('iTunes')
  return iTunes

def get_playlists():
  return [x for x in get_app().user_playlists()] 
  
def list_playlists():
  return [x.name() for x in get_playlists()]
  
def search_playlists(name):
  return name.lower() in [pl.lower() for pl in list_playlists()]
  
def get_playlist(name):
  try:
    return [pl for pl in get_playlists() if pl.name().lower() == name.lower()][0]
  except:
    pass
    
def get_tracks(name):
  playlist = get_playlist(name)
  return playlist.file_tracks()
  
def list_tracks(name):
  return [x.name() for x in get_tracks(name)]
  
def get_track_kind(track):
  return track.kind()

def get_track_title(track):
  return track.name()

def get_track_artist(track):
  return track.artist()
  
def get_track_size(track):
  return track.size()
  
def get_track_num(track):
  return track.track_number()
  
def is_track_transcodeable(kind):
  global __encodable_kinds__
  #if not isinstance(track, basestring):
  #  kind = get_track_kind(kind)
  return kind.lower() in [x.lower() for x in __encodable_kinds__.keys()]
  
def get_track_abspath(track):
  try:
    path = track.location().path
    if not os.path.isfile(path):
      raise AttributeError()
    return path
  except AttributeError:
    raise TrackNotFound()

def get_all_tracks_details(name):
  for position, item in enumerate(get_tracks(name)):
    yield (get_track_title(item), get_track_artist(item), get_track_num(item), get_track_abspath(item), get_track_kind(item), get_track_size(item))


def convert_aac_to_mp3(artist, title, tracknum, location, outdir, quality):
  _decode = shlex.split(str('%s -q -o - "%s"' % (FAAD, location)))
  _encode = shlex.split(str('%s -h -S -b %s - "%s/%s - %s - %s.mp3"' % (
    LAME,
    quality,
    outdir, 
    artist,
    title,
    tracknum)))
  decode = subprocess.Popen(_decode, stdout=subprocess.PIPE)
  encode = subprocess.Popen(_encode,
                            stdin=decode.stdout, stdout=subprocess.PIPE)
  output = encode.communicate()[0]
  print "  .. processed: %s - %s - %s" % (artist, title, tracknum)


def copy_mp3(artist, title, tracknum, location, outdir, *args, **kwargs):
  print "  Processing: %s - %s - %s..." % (artist, title, tracknum),
  copyfile(location, '%s/%s - %s - %s.mp3' % (outdir, artist, title, tracknum))
  print "done."

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='Burn an MP3-CD from an iTunes playlist, autoconverting file formats where necessary'
  )
  
  parser.add_argument(
    '--quality',
    dest='quality',
    default=['med'],
    choices=['low','med','high'],
    nargs=1,
    help='Quality of output MP3 audio file'
  )
  
  parser.add_argument(
    'playlists',
    metavar='playlists',
    type=str,
    nargs='+',
    help='The name(s) of the playlist(s) to burn'
  )

  args = parser.parse_args()

  print "Gathering information..."
  
  for name in args.playlists:
    if not search_playlists(name):
      print 'Playlist "%s" not found' % name
    else:
      __track_lists__[name] = [dict(zip(__list_keys__, x)) for x in get_all_tracks_details(name)]

    #print __track_lists__
    
    
  burnsize = 0
  for pl, tracks in __track_lists__.iteritems():
    burnsize += sum(track['size'] for track in tracks)
    
  if burnsize > __cd_size__:
    print '  ERROR: selected tracks will not fit onto a single disk.'
    print 'terminating.'
    raise SystemExit()
  
  estburnsize = int(float(burnsize) * 1.5)
    
  print "  estimated burn size: %d bytes" % estburnsize
  
  if estburnsize > __cd_size__:
    print '  ERROR: estimating converted files to be larger than disk size.'
    print 'terminating.'
    raise SystemExit()

  print "done."

  outputdir = tempfile.mkdtemp(prefix='EncodeAudio-')

  pool = Pool(processes=5)
  '''
  try:
    for playlist, tracks in __track_lists__.iteritems():

      print "Processing playlist: %s" % playlist
      playlistdir = outputdir+'/'+playlist

      print "  .. creating tmp dir: %s" % playlistdir
      os.mkdir(playlistdir)

      print "  .. processing %d tracks" % len(tracks)
      
      for track in tracks:
        if is_track_transcodeable(track['kind']):
          target = convert_aac_to_mp3
        else:
          target = copy_mp3

        if not os.path.isfile(track['abspath']):
          print '> .. file "%s" does not exist' % track['abspath']
          continue
        else:
          print '  .. adding to pool: %s - %s' % (track['artist'], track['title'])
 
        result = pool.apply_async(target,
                    args=(
                      track['artist'], 
                      track['title'], 
                      track['number'],
                      track['abspath'], 
                      playlistdir,
                      __quality__[args.quality[0]]
                      ))
    print "  .. processing pool, please wait..."
    pool.close()
    pool.join()

  except:
    pool.terminate()
    raise SystemExit('Error encountered while processing. Terminating run.')
  '''

  diskdir = tempfile.mkdtemp(prefix='BurnAudio-')
  diskname = 'Music-%s' % datetime.utcnow().strftime('%Y%m%d')

  shlex.split(str('rm -f /tmp/%(name)s.iso' % {'name': diskname }))

  mkdisk = shlex.split(str('hdiutil makehybrid -iso -joliet-volume-name %(name)s -joliet -o %(diskdir)s/%(name)s.iso %(dir)s' % {'name': diskname, 'dir': outputdir, 'diskdir': diskdir }))
  subprocess.call(mkdisk)

  do_burn = raw_input('Continue to burn CD? (y/N)')

  if do_burn.strip().lower() != 'y':
    raise SystemExit('Exiting at user request.')

  print "Actual burn size: %s bytes" % os.path.getsize('%s/%s.iso'% (diskdir, diskname))

  subprocess.call(shlex.split(str("hdiutil burn %s/%s.iso" % (diskdir, diskname))))

  print "\nCompleted.\n"

  subprocess.call(['drutil', 'eject'])

#3693979
