import sys
import gpiozero as GPIO
import os
import re
import vlc
import queue
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
PREV_PIN = 2
REWIND_PIN = 17
PLAY_PIN = 27
FF_PIN = 22
NEXT_PIN = 4
SOURCE_PIN = 3
MESSAGES_PIN = 14
VOLUME_CHANNEL = 0

# STATE MACHINE
class S(Enum):
    Error = 1
    Paused = 2
    Playing = 3
    PlayingMessage = 4
    SwitchingBooks = 5
    SystemShutdown = 6

# CURRENT DATA
media = vlc.MediaPlayer('')
events = media.event_manager()
trackQueue = queue.Queue()
trackEndedFlag = False
config = ConfigParser()
state = S.PlayingMessage
maxBook = 0
maxTrack = 0
book = 0
track = 0
resumeTime = 0
messages = True
volumeLevel = 0

# GPIO DECLARATIONS
shutdownBtn = GPIO.Button(SHUTDOWN_PIN)

readySignal = GPIO.LED(READY_PIN)
stateLed = GPIO.PWMLED(LED_STATE_PIN)

prevBtn = GPIO.Button(PREV_PIN)
rewindBtn = GPIO.Button(REWIND_PIN)
playBtn = GPIO.Button(PLAY_PIN)
ffBtn = GPIO.Button(FF_PIN)
nextBtn = GPIO.Button(NEXT_PIN)
sourceBtn = GPIO.Button(SOURCE_PIN)
messagesBtn = GPIO.Button(MESSAGES_PIN)

volumePot = GPIO.MCP3008(VOLUME_CHANNEL)

# SYSTEM FUNCTIONS
def switchState(newState):
    global state
    state = newState
    print('Switching state to:',  newState.name)
    if state == S.Error:
        stateLed.off()
    elif state == S.Paused:
        stateLed.blink(0.8, 0.8)
    else:
        stateLed.on()

def isState(stateToCheck):
    return state == stateToCheck

def saveResumeData():
    global config
    if usbDetected:
        config['RESUME']['Book'] = str(book)
        config['RESUME']['Track'] = str(track)
        currentTime = media.get_time()
        if currentTime < 60000:
            config['RESUME']['Time'] = '0'
        else:
            config['RESUME']['Time'] = str(currentTime // 1000)
        config['RESUME']['Messages'] = '1' if messages else '0'
        with open('/media/RPI/config.ini', 'w') as conf:
            config.write(conf)
        print('Resume data saved!')

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

def trackEnded(event):
    global trackEndedFlag
    trackEndedFlag = True

def loadTrackAudio():
    global media
    global events
    global trackQueue
    global resumeTime
    events.event_detach(vlc.EventType.MediaPlayerEndReached)
    media.stop()
    if trackQueue.empty():
        if track < 10:
            trackFileName = '00' + str(track)
        elif track < 100:
            trackFileName = '0' + str(track)
        else:
            trackFileName = str(track)
        pathToFile = '/media/RPI/b' + str(book) + '/' + trackFileName + '.mp3'
        print('Loading audio file... BOOK:', book, 'TRACK:', track)
        switchState(S.Playing)
        saveResumeData()
        media = vlc.MediaPlayer(pathToFile, 'start-time=' + str(resumeTime) + '.0')
        if book > 0 and track > 0:
            resumeTime = 0
    else:
        pathToFile = trackQueue.get()
        print('Loading message file... PATH:', pathToFile)
        if not isState(S.Error):
            switchState(S.PlayingMessage)
        media = vlc.MediaPlayer(pathToFile)
    events = media.event_manager()
    events.event_attach(vlc.EventType.MediaPlayerEndReached, trackEnded)
    media.audio_set_volume(volumeLevel)
    media.play()

def playNumberMessage(number):
    number = int(number)
    if number == 0:
        return
    firstNumber = number // 100
    secondNumber = (number - firstNumber * 100) // 10
    thirdNumber = number - firstNumber * 100 - secondNumber * 10
    if firstNumber > 0:
        playMessage(firstNumber)
    if secondNumber > 0:
        playMessage(secondNumber)
    playMessage(thirdNumber)

def playMessage(typeId, ignoreSettings = False):
    global trackQueue
    if not messages and not ignoreSettings:
        return
    typeId = str(typeId)
    path = '/home/pi/books/' + typeId + '.mp3'
    print('Adding message track TYPE:', typeId)
    trackQueue.put(path)
    if typeId == 'book':
        playNumberMessage(book)
    if typeId == 'track':
        playNumberMessage(track)

def switchTrack(trackId):
    global track
    trackId = int(trackId)
    if trackId > maxTrack:
        trackId = 1
    if trackId < 1:
        trackId = maxTrack
    track = trackId
    print('Switching track to', track, 'MAX:', maxTrack)
    if not isState(S.PlayingMessage) and not isState(S.SwitchingBooks):
        playMessage('track')
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
    switchState(S.SwitchingBooks)
    playMessage('book')
    loadTrackAudio()
    switchTrack(trackId)
    playMessage('track')

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
    messages = True if config['RESUME']['Messages'] == '1' else False
    resumeTime = int(config['RESUME']['Time'])
    playMessage('start')
    maxBook = int(config['BOOKS']['Count'])
    switchBook(config['RESUME']['Book'], config['RESUME']['Track'])
    if book == 0 or track == 0:
        switchState(S.Error)
else:
    switchState(S.Error)

# SHUTDOWN EVENT
def poweroffSystem():
    readySignal.off()
    os.system('sudo poweroff')

def systemShutdownSignal():
    print('System shutdown...')
    if messages:
        playMessage('end')
        loadTrackAudio()
        switchState(S.SystemShutdown)
    else:
        poweroffSystem()

shutdownBtn.when_pressed = systemShutdownSignal

# NEXT TRACK EVENT
def checkTrackEndedEvent():
    global trackEndedFlag
    global trackQueue
    if trackEndedFlag:
        if isState(S.SystemShutdown):
            poweroffSystem()
        else:
            trackEndedFlag = False
            print('\nSwitching to the next track...')
            if trackQueue.empty():
                if isState(S.Playing):
                    switchTrack(track + 1)
                else:
                    loadTrackAudio()
            else:
                loadTrackAudio()

# VOLUME LEVEL
def checkVolumeLevel():
    global volumeLevel
    currentLevel = int(volumePot.value * 100)
    if currentLevel != volumeLevel:
        volumeLevel = currentLevel
        media.audio_set_volume(volumeLevel)

# BUTTON EVENTS
def prevChapter():
    print('prev button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    switchTrack(track - 1)

def rewindTrack():
    print('rewind button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    setAudioPosition(TRACK_JUMP * -1, True)

def playPause():
    print('play/pause button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    if media.is_playing():
        switchState(S.Paused)
    else:
        switchState(S.Playing)
    media.pause()
    saveResumeData()

def ffTrack():
    print('fast foward button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    setAudioPosition(TRACK_JUMP, True)

def nextChapter():
    print('next button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    switchTrack(track + 1)

def switchSource():
    print('source button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    switchBook(book + 1, 1)

def toggleMessages():
    global messages
    print('message button pressed')
    if isState(S.PlayingMessage) or isState(S.SwitchingBooks):
        return
    messages = not messages
    playMessage('beep', True)
    loadTrackAudio()
    saveResumeData()

# DISABLE BUTTON IF ERROR STATE
if state == S.Error:
    print('\nConfig error detected - you need to restart the system!')
    playMessage('error', True)
    loadTrackAudio()
    while True:
        checkTrackEndedEvent()
        checkVolumeLevel()

# BUTTON EVENTS
prevBtn.when_pressed = prevChapter
rewindBtn.when_pressed = rewindTrack
playBtn.when_pressed = playPause
ffBtn.when_pressed = ffTrack
nextBtn.when_pressed = nextChapter
sourceBtn.when_pressed = switchSource
messagesBtn.when_pressed = toggleMessages

if len(sys.argv) > 1 and sys.argv[1] == '-vkb':
    # VIRTUAL KEYBOARD BUTTONS MODE
    while True:
        checkTrackEndedEvent()
        checkVolumeLevel()
        print('(Skip this input to detect next track event and volume level)')
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
        if k == 'm':
            toggleMessages()
        if k == 'p':
            systemShutdownSignal()
else:
    # AUTOSTART VERSION MODE
    while True:
        checkTrackEndedEvent()
        checkVolumeLevel()
