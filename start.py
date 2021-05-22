import sys
import gpiozero as GPIO
import time
import os
import re
import vlc
from configparser import ConfigParser
from enum import Enum
from signal import pause

# SYSTEM CONFIG
USB_LABEL = '"RPI"'
TRACK_JUMP = 15000

# PIN DEFINITIONS
SHUTDOWN_PIN = 23
READY_PIN = 24
LED_STATE_PIN = 18
PREV_PIN = 5
REWIND_PIN = 6
PLAY_PIN = 13
FF_PIN = 19
NEXT_PIN = 26
SOURCE_PIN = 21

# STATE MACHINE
class S(Enum):
	Init = 1
	Error = 2
	Paused = 3
	Playing = 4
	SwitchingChapter = 5
	SwitchingBooks = 6

# CURRENT DATA
media = vlc.MediaPlayer('')
events = media.event_manager()
loadNextTrackFlag = False
config = ConfigParser()
state = S.Init
maxBook = 0
maxTrack = 0
book = 0
track = 0

# GPIO DECLARATIONS
shutdownBtn = GPIO.Button(SHUTDOWN_PIN)

readySignal = GPIO.LED(READY_PIN)
stateLedSignal = GPIO.LED(LED_STATE_PIN)

prevBtn = GPIO.Button(PREV_PIN)
rewindBtn = GPIO.Button(REWIND_PIN)
playBtn = GPIO.Button(PLAY_PIN)
ffBtn = GPIO.Button(FF_PIN)
nextBtn = GPIO.Button(NEXT_PIN)
sourceBtn = GPIO.Button(SOURCE_PIN)

# SYSTEM FUNCTIONS
def switchState(newState):
    global state
    state = newState
    print('Switching state to:',  newState.name)

def setAudioPosition(value, isRelative):
    global media
    value = int(value)
    current = media.get_time()
    length = media.get_length()
    if isRelative:
        newPos = current + value
    else:
        newPos = value
    if newPos < 0:
        newPos = 0
    if newPos > length:
        newPos = length
    print('Set new position:', newPos / 1000, ' Prev position:', current / 1000, ' Track length:', length / 1000)
    media.set_time(newPos)

def trackFinished(event):
    global loadNextTrackFlag
    loadNextTrackFlag = True

def loadTrackAudio():
    global media
    global events
    print('Loading audio file... BOOK:', book, 'TRACK:', track)
    events.event_detach(vlc.EventType.MediaPlayerEndReached)
    media.stop()
    media = vlc.MediaPlayer('/media/RPI/b' + str(book) + '/' + str(track) + '.mp3')
    events = media.event_manager()
    events.event_attach(vlc.EventType.MediaPlayerEndReached, trackFinished)
    media.audio_set_volume(100) # volumen level 0-100
    media.play()

def switchTrack(trackId):
    global track
    trackId = int(trackId)
    if trackId > maxTrack:
        trackId = 1
    if trackId < 1:
        trackId = maxTrack
    track = trackId
    print('Switching track to', track, 'MAX:', maxTrack)
    loadTrackAudio()

def switchBook(bookId, trackId):
    global book
    global maxTrack
    global config
    bookId = int(bookId)
    if bookId > maxBook:
        bookId = 1
    if bookId < 1:
        bookId = maxBook
    book = bookId
    maxTrack = int(config['B'+str(book)]['Count'])
    print('Switching book to', book, 'MAX:', maxBook)
    switchTrack(trackId)

def saveResumeData():
    global config
    config['RESUME']['Book'] = str(book)
    config['RESUME']['Track'] = str(track)
    config['RESUME']['Time'] = str(media.get_time())
    with open('/media/RPI/config.ini', 'w') as conf:
        config.write(conf)
    print('Resume data saved!')

# INIT SYSTEM
readySignal.on()
print('System initialized')

# FIND AND MOUNT USB STICK
print('Detecting USB devices...')
devices = os.popen('sudo blkid').readlines()
usbDetected = False
usbs = []
for u in devices:
    loc = [u.split(':')[0]]
    if '/dev/sd' not in loc[0]:
        continue
    loc += re.findall(r'"[^"]+"', u)
    columns = ['loc'] + re.findall(r'\b(\w+)=', u)
    usbs.append(dict(zip(columns, loc)))
for u in usbs:
    print('Device %(LABEL)s is located at %(loc)s with UUID of %(UUID)s'%u)
    if u['LABEL'] == USB_LABEL:
        print('Target device detected! Mounting...')
        os.system('sudo mkdir -p /media/RPI')
        os.system('sudo mount %(loc)s /media/RPI'%u)
        print('Device mounted')
        usbDetected = True

# LOAD RESUME SETTINGS
if usbDetected:
    config.read('/media/RPI/config.ini')
    maxBook = int(config['BOOKS']['Count'])
    switchBook(config['RESUME']['Book'], config['RESUME']['Track'])
    setAudioPosition(config['RESUME']['Time'], False)
    if book == 0 or track == 0:
        switchState(S.Error)
    else:
        switchState(S.Paused)
else:
    switchState(S.Error)

# SHUTDOWN EVENT
def systemShutdown():
    readySignal.off()
    print('System shutdown...')
    os.system('sudo poweroff')

shutdownBtn.when_pressed = systemShutdown

# NEXT TRACK EVENT
def checkNextTrackEvent():
    global loadNextTrackFlag
    if loadNextTrackFlag:
        loadNextTrackFlag = False
        print('\nSwitching to the next track...')
        switchTrack(track + 1)
        saveResumeData()

# BUTTON EVENTS
def prevChapter():
    print('prev button pressed')
    switchTrack(track - 1)
    saveResumeData()

def rewindTrack():
    print('rewind button pressed')
    setAudioPosition(TRACK_JUMP * -1, True)

def playPause():
    print('play/pause button pressed')
    media.pause()
    saveResumeData()

def ffTrack():
    print('fast foward button pressed')
    setAudioPosition(TRACK_JUMP, True)

def nextChapter():
    print('next button pressed')
    switchTrack(track + 1)
    saveResumeData()

def switchSource():
    print('source button pressed')
    switchBook(book + 1, 1)

# DISABLE BUTTON IF ERROR STATE
if state == S.Error:
    print('\nConfig error detected - you need to restart the system!')
    pause()

# BUTTON EVENTS
prevBtn.when_pressed = prevChapter
rewindBtn.when_pressed = rewindTrack
playBtn.when_pressed = playPause
ffBtn.when_pressed = ffTrack
nextBtn.when_pressed = nextChapter
sourceBtn.when_pressed = switchSource

if len(sys.argv) > 1 and sys.argv[1] == '-vkb':
    # VIRTUAL KEYBOARD BUTTONS MODE
    while True:
        checkNextTrackEvent()
        print('(Skip this input to detect next track event)')
        k = input('Button key:')
        if k == 'q':
            prevChapter()
        if k == 'w':
            rewindTrack()
        if k == 'e':
            playPause()
        if k == 'r':
            ffTrack()
        if k == 't':
            nextChapter()
        if k == 's':
            switchSource()
        if k == 'p':
            systemShutdown()
else:
    # AUTOSTART VERSION MODE
    while True:
        checkNextTrackEvent()
