
from Args import Args
from mido import Message, MidiFile, MidiTrack
import time
import random
import datetime
import matplotlib.pyplot as plt
import numpy as np
import mido


def update_quantization_values(clocks_per_click = Args.clocks_per_click, force_update=True):

    #if not force_update:
    #    if clocks_per_click == Args.clocks_per_click:
    #        return
    #    print('clocks_per_click updated to:', clocks_per_click)

    midi_time_interval = []
    for x in Args.xth_beats:
        for i in range(x):
            midi_time_interval.append(4 * i * clocks_per_click // x)
    midi_time_interval = list(set(midi_time_interval))  # remove duplicates
    midi_time_interval.sort()
    return midi_time_interval
    # [0, 12, 24, 32, 36, 48, 60, 64, 72, 84]


def postprocess(numpy_array):
    log("Creating midi")
    multiplier = 5
    length = int(Args.clocks_per_click * multiplier) * 2
    midi_time_interval = update_quantization_values()
    assert numpy_array.shape == (Args.max_octave_range * 12, Args.beats_per_sample * len(midi_time_interval))

    track = []
    column_times = []
    for beat_number in range(Args.beats_per_sample):
        for a in midi_time_interval:
            column_times.append(int((a+beat_number*Args.clocks_per_click*4)*multiplier))

    prev_column_time = 0
    for column_number in range(numpy_array.shape[1]):
        for row_number in range(numpy_array.shape[0]):
            if numpy_array[row_number, column_number]:
                start_point = column_times[column_number] - prev_column_time
                track.append(['note_on', row_number, start_point])
                prev_column_time = column_times[column_number]

    i = 0
    while True:
        message = track[i]
        if message[0] == 'note_on':
            extra_time = length
            for second_index in range(i+1, len(track)):
                msg2 = track[second_index]
                if extra_time > msg2[2]:  # =?
                    extra_time -= msg2[2]
                else:
                    track[second_index][2] -= extra_time
                    track.insert(second_index, ['note_off', message[1], extra_time])
                    break
                track.append(['note_off', message[1], extra_time])
        i += 1
        if i >= len(track):
            break

    mid = MidiFile()
    miditrack = MidiTrack()
    mid.tracks.append(miditrack)
    for message in track:
        assert message[1] >= 0 and message[2] >= 0
        miditrack.append(Message(message[0], note=60 + message[1], velocity=99, time=message[2]))

    mid.save(datetime.datetime.now().strftime(Args.output_file)+'_'+str(random.randint(0, 1000))+'.mid')


def log(*args):
    full_string = ''
    for string in args:
        full_string += str(string) + ' '

    if Args.verbose:
        print(full_string)

    # full_string += '\n' TODO logfile