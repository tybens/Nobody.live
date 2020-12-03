#!/usr/bin/env python3

import json
import os.path
import datetime
import redis
from threading import Thread
from time import sleep

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, send, emit, join_room, leave_room

# check if in production and change static location
dir_path = os.path.dirname(os.path.realpath(__file__))
static_folder = '/var/www/static' if (dir_path == '/srv/lonelyraids.com') else 'static'

app = Flask(__name__, static_url_path='', static_folder=static_folder) 
CORS(app)
app.config['SECRET_KEY'] = 'secret!!'
socketio = SocketIO(app, cors_allowed_origins='*')
main_redis = redis.Redis(decode_responses=True, db=0)
stats_redis = redis.Redis(decode_responses=True, db=1)

streamRaid = None
raidLength = 60
countdown = raidLength
connections = 0
class CountdownTask: 
      
    def __init__(self): 
        self._running = True
          
    def terminate(self): 
        self._running = False
          
    def run(self):
        global streamRaid
        global countdown
        # countdown
        while countdown > 0 and self._running:
            sleep(1)
            countdown -= 1
        # reset global variables
        streamRaid = None
        countdown = raidLength

c = CountdownTask()
timer_thread = Thread(target=c.run)

def getStreams(count = 1):
    results = []
    for i in range(int(count)):
        key = main_redis.randomkey()

        if not key:
            return results

        stream = json.loads(key)
        stream['fetched'] = main_redis.get(key)
        stream['ttl'] = main_redis.ttl(key)
        results.append(stream)
    return results

@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/stream')
def get_stream():
    streams = getStreams()
    if streams:
        return streams[0]
    return '{}'

@app.route('/streamraid')
def get_streamraid():
    global streamRaid
    global timer_thread
    global c

    if streamRaid is None:
        streamRaid = getStreams()[0]
        timer_thread = Thread(target=c.run)
        timer_thread.start()


    return streamRaid

@app.route('/countdown')
def get_countdowntime():
    global timer_thread
    global countdown
    if timer_thread.isAlive():
        return {'countdown': countdown}
    return {'countdown': 0}



@app.route('/streams', defaults={'count': 20})
@app.route('/streams/<count>')
def get_streams(count):
    streams = getStreams(count)

    if streams:
        return jsonify(streams)
    return '[]'


@app.route('/stats/json')
def get_stats_json():
    stats = json.loads(stats_redis.get('stats'))
    stats['streams'] = stats_redis.dbsize()

    return jsonify(stats)


@app.route('/status')
@app.route('/stats')
def get_stats_human():
    stats = json.loads(stats_redis.get('stats'))

    return (f"{int(stats['ratelimit_remaining'])}/{int(stats['ratelimit_limit'])} API tokens left "
            f"({round((1 - int(stats['ratelimit_remaining']) / int(stats['ratelimit_limit'])) * 100, 2)}% spent). "
            f"{main_redis.dbsize() - 1} streams loaded."
    )

@socketio.on('override')
def override():
    global streamRaid
    global stop_threads
    global countdown
    global c

    c.terminate()    # stop countdown
    c = CountdownTask() # start a new one

    streamRaid = None
    countdown = raidLength
    thisRaid = get_streamraid()
    print('overrided')
    emit('overrided', thisRaid, broadcast=True)

@socketio.on('raid started')
def broadcastRaid():
    emit('raid started', 'user started a raid', broadcast=True, include_self=False)

@socketio.on('voted')
def handleVote():
    emit('voted')


@socketio.on('connect')
def handleConnect():
    global connections 
    connections += 1
    emit('connection', str(connections), broadcast=True)

@socketio.on('disconnect')
def handleDisconnect():
    global connections
    connections -= 1
    emit('connection', str(connections), broadcast=True)



if __name__ == "__main__":
    socketio.run(app)
