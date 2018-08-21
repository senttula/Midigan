import mido
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
from Args import Args
import random
from utils import update_quantization_values, postprocess
from utils import log as log

class preprocess_track:
    def __init__(self, track):
        self.track = track
        self.samples = []
        self.channels = []
        self.midi_time_interval = []

        self.pitches = set()
        self.chords = set()
        self.note_lengths = set()
        self.note_count = 0
        self.sample_count = 0

        self.time_point = 0
        self.start_time = 0
        self.chord_start_time = 0
        self.end_time = 0

        self.extra_time = 0
        self.ticks_per_beat = 96

        self.tt = 0

    def clean_track(self):
        # clean track for easier process
        self.channels = set()
        self.midi_time_interval = update_quantization_values()
        i = 0
        time_to_add = 0
        while i < len(self.track):
            msg = self.track[i]
            if msg.type == 'note_on':
                msg.time += time_to_add
                time_to_add = 0
                i += 1

                self.channels.add(msg.channel)
                if len(self.channels) > 1:
                    log('TODO multiple channels')  # TODO
                    return False
                continue
            # elif msg.type == 'note_off':
            if msg.time:
                time_to_add += msg.time


                if msg.type == 'time_signature':
                    self.midi_time_interval = update_quantization_values(msg.clocks_per_click, force_update=False)
                    self.ticks_per_beat = msg.clocks_per_click * 4
                elif msg.type == 'program_change': # TODO doesn't catch all bad programs
                    print(msg.program)
                    if msg.program + 1 in Args.instruments_to_ignore:  # +1 to get 1 indexed
                        log('bad instrument')
                        return False
            self.track.remove(msg)
        if len(self.track) < Args.min_note_count:
            log('Not enough notes on track: %d < %d ' %  (len(self.track) , Args.min_note_count))
            return False
        return True

    def loop_track(self):
        if not self.clean_track():
            return

        self.sample_length = Args.beats_per_sample * len(self.midi_time_interval)


        # process first note separately
        first = self.track.pop(0)
        self.time_point = self.add_times(self.time_point, first.time)
        self.new_sample()
        self.add_note(first.note)

        for msg in self.track:
            self.time_point = self.add_times(self.time_point, msg.time)
            if self.time_point >= self.sample_length:
                self.end_sample()
                self.new_sample()
            if msg.type == 'note_on':
                self.add_note(msg.note)
        self.end_sample()
        return self.samples

    def add_note(self, pitch):
        assert self.time_point >=0 and self.time_point <= self.sample_length

        #if self.sample[pitch, self.time_point] == 1: # if there is already a note? bug but shouldn't matter
        self.sample[pitch, self.time_point] = 1

        chord = np.argwhere(self.sample[:, self.time_point] == 1).squeeze(axis=1) # indices of notes at this timepoint
        self.pitches.add(pitch)
        if len(chord) > 1:  # chord has >1 notes
            self.chord_candidate = chord
        else:  # this is the first note
            if self.chord_candidate is not None:  # save previous chord
                self.chord_candidate = list(self.chord_candidate)
                self.chord_candidate.sort()
                tp = tuple(self.chord_candidate)
                self.chords.add(tp)
                self.chord_candidate = []
            self.note_count += 1

    def end_sample(self):
        if self.pitches:
            if len(self.chords) >= Args.min_pitch_count and self.note_count >= Args.min_note_count:
                split_point = min(self.pitches) // 12 * 12  # normalize octave start
                octave_range = Args.max_octave_range * 12
                if max(self.pitches) < split_point + octave_range:  # skip those with high octave range
                    self.sample = self.sample[split_point:split_point + octave_range, :]  # crop
                    self.samples.append(self.sample)
            else:
                log('low quality sample, pitches: %s notecount: %s' % (len(self.pitches), self.note_count))

    def new_sample(self):
        self.pitches.clear()
        self.chords.clear()
        self.note_count = 0
        self.chord_candidate = []
        self.sample = np.zeros((128, self.sample_length))
        self.time_point %= len(self.midi_time_interval)  # normalize start time

    def quantize(self, time):
        remainder = time % self.ticks_per_beat
        beat_number = time // self.ticks_per_beat
        delta = 0
        if remainder not in self.midi_time_interval:
            if remainder > self.ticks_per_beat:
                return (beat_number+1) * len(self.midi_time_interval)
            else:
                delta = self.ticks_per_beat
                orig_remainder = remainder
                for index, interval in enumerate(self.midi_time_interval):

                    new_delta = interval-orig_remainder
                    if abs(new_delta) < abs(delta):
                        remainder = self.midi_time_interval[index]
                    else:
                        break
                    delta = new_delta
        self.extra_time = - delta
        remainder = self.midi_time_interval.index(remainder)
        assert abs(self.extra_time) < self.midi_time_interval[1] # TODO shouldn't be needed
        quantized = beat_number * len(self.midi_time_interval) + remainder
        return quantized

    def add_times(self, time_point, time_to_add):
        remainder = time_point % len(self.midi_time_interval)
        beat_number = time_point // len(self.midi_time_interval)

        time = self.midi_time_interval[remainder] + time_to_add + self.extra_time
        quantized = beat_number * len(self.midi_time_interval) + self.quantize(time)

        return quantized


def read_midis():
    midipaths = glob(Args.path_to_midifolder)
    log('Total count of midifiles: %d' % len(midipaths))
    output_samples = []
    for i, path in enumerate(midipaths):
        if i < 116: # 6 85
            continue
        #if i > 10:  # 6 85
        #    break
        filename = path.split("\\")[-1]
        try:
            mid = mido.MidiFile(path)
        except (IndexError, OSError, EOFError) as e:
            log(e, '\t', filename)
            continue
        for track in mid.tracks:
            if not confirm_track(track):
                continue
            log(track, filename)
            print(track, filename)

            preprocess_class = preprocess_track(track)
            samples = preprocess_class.loop_track()

            if samples:
                output_samples = output_samples+samples
                plt.imshow(np.flip(samples[0], 0))
                plt.show()

    index_list = np.random.randint(len(output_samples), size=10) # show few random samples
    for i in index_list:
        plt.imshow(np.flip(output_samples[i], 0))
        plt.show()

    #log('saving dataset...')
    #np.savez_compressed(Args.dataset_file, output_samples)
    #log('dataset done', Args.dataset_file)

def confirm_track(track):
    if len(track) < Args.min_note_count:
        return False
    track_name = track.name.lower()
    for bad_track_name in Args.track_names_to_ignore:
        if bad_track_name in track_name:
            return False
    return True

if __name__ == "__main__":
    read_midis()