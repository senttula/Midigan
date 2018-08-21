

# Args are here for easier testing
class Args:



    ################################################################################################################
    # generic args
    ################################################################################################################

    # file which the preprocess.py generates and which gan uses
    # compressed since the data is sparse: ~1/400 space needed
    dataset_file = 'dataset\\midi_numpy_data.npz'

    verbose = False
    logfile = 'log.txt'  # TODO



    ################################################################################################################
    # arguments to generate dataset from midi files
    ################################################################################################################
    path_to_midifolder = r'C:\Users\tka\PycharmProjects\midi_analyse\midi\*.mid'

    clocks_per_click = 24  # default
    xth_beats = [8]  # utils.update_quantization_values: generates list values from clocks_per_click

    beats_per_sample = 16
    max_octave_range = 3  # 3 means 36 pitch range

    too_short_multiplier = 0.6  # skip samples that are too short TODO needed?

    # minimum note count and number of different pitches occured to append in dataset
    min_note_count = int(beats_per_sample+1)
    min_pitch_count = 4
    min_velocity = 20 # TODO needed?

    # some instruments don't usually have any melody
    # full instrument list https://www.midi.org/specifications-old/item/gm-level-1-sound-set
    def add(x1, x2):
        return list(range(x1, x2 + 1))
    instruments_to_ignore = add(9, 16) + add(25, 40) + add(89, 128)

    # also some track names can be ignored, not melodic
    track_names_to_ignore = ['drum', 'bassline', 'perc', 'kick']

    ################################################################################################################
    # MIDI output specific arguments
    ################################################################################################################

    output_file = 'results\\%m-%d_%H-%M_song'  # formatted to datetime
    # save every x