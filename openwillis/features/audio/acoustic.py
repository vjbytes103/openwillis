# author:    Vijay Yadav
# website:   http://www.bklynhlth.com

# import the required packages

import numpy as np
import pandas as pd

import parselmouth
from parselmouth.praat import call
from pydub import AudioSegment,silence

import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger()

def common_summary(df, col_name):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates common summary statistics for a given column of a dataframe.

    Parameters:
    ...........
    df : pandas dataframe
        the dataframe to summarize.
    col_name : str
        the name of the column to summarize.

    Returns:
    ...........
    df_summ : pandas dataframe
        a dataframe containing the summary statistics of the given column.

    ------------------------------------------------------------------------------------------------------
    """
    mean = df.mean()
    std = df.std()
    min_val = df.min()
    max_val = df.max()
    range_val = max_val - min_val

    values = [mean, std, min_val, max_val, range_val]
    cols = [col_name + '_mean', col_name + '_stddev', col_name + '_min', col_name + '_max',
            col_name + '_range']

    df_summ = pd.DataFrame([values], columns= cols)
    return df_summ

def silence_summary(sound, df, measure):
    """
    ------------------------------------------------------------------------------------------------------
    Calculates silence summary statistics for a given audio file.

    Parameters:
    ...........
    sound : Praat sound object;
        the audio file to analyze.
    df : pandas dataframe
        the dataframe containing the silence intervals in the audio file.
    measure : dict
        a dictionary containing the measure names for the calculated statistics.

    Returns:
    ...........
    silence_summ : pandas dataframe
        a dataframe containing the summary statistics of the silence intervals.

    ------------------------------------------------------------------------------------------------------
    """
    duration = call(sound, "Get total duration")

    df_silence = df[measure['voicesilence']]
    mean = df_silence.mean()

    num_pause = (len(df_silence)/duration)*60
    cols = [measure['pause_meandur'], measure['pause_rate']]

    silence_summ = pd.DataFrame([[mean, num_pause]], columns = cols)
    return silence_summ

def get_summary(sound, framewise, sig_df, df_silence, measure):
    """
    ------------------------------------------------------------------------------------------------------
    Calculates the summary statistics for a given audio file.

    Parameters:
    ...........
    sound : Praat sound object
        the audio file to analyze.
    framewise : pandas dataframe
        a dataframe containing the fundamental frequency, loudness, HNR, and formant frequency values for
        each frame in the audio file.
    sig_df : pandas dataframe
        a dataframe containing the jitter, shimmer, and GNE values for the audio file.
    df_silence :pandas dataframe
        a dataframe containing the silence intervals in the audio file.
    measure : dict
        a dictionary containing the measure names for the calculated statistics.

    Returns:
    ...........
    df_concat : pandas dataframe
        a dataframe containing all the summary statistics for the audio file.

    ------------------------------------------------------------------------------------------------------
    """
    df_list = []
    col_list = list(framewise.columns)

    for col in col_list:
        com_summ = common_summary(framewise[col], col)
        df_list.append(com_summ)

    summ_silence = silence_summary(sound, df_silence, measure)
    voice_pct = voice_frame(sound, measure)

    df_concat = pd.concat(df_list+ [sig_df, summ_silence, voice_pct], axis=1)
    return df_concat

def voice_frame(sound, measure):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the percentage of frames in the given audio file that contain voice.

    Parameters:
    ...........
    sound : Praat sound object
        the audio file to analyze.
    measure : dict
        a dictionary containing the measure names for the calculated statistics.

    Returns:
    ...........
    df : pandas dataframe;
        a dataframe containing the percentage of frames in the audio file that contain voice.

    ------------------------------------------------------------------------------------------------------
    """
    pitch = call(sound, "To Pitch", 0.0, 75, 500)

    total_frames = pitch.get_number_of_frames()
    voice = pitch.count_voiced_frames()
    voice_pct = 100 - (voice/total_frames)*100

    df = pd.DataFrame([voice_pct], columns=[measure['silence_ratio']])
    return df

def read_audio(path):
    """
    ------------------------------------------------------------------------------------------------------

    Reads an audio file and returns the Praat sound object and a dictionary of measure names.

    Parameters:
    ...........
    path : str
        The path to the audio file.

    Returns:
    ...........
    sound : praat sound object
        the Praat sound object for the given audio file.
    measures : dict
        a dictionary containing the measure names for the calculated statistics.

    ------------------------------------------------------------------------------------------------------
    """
    #Loading json config
    dir_name = os.path.dirname(os.path.abspath(__file__))
    measure_path = os.path.abspath(os.path.join(dir_name, 'config/acoustic.json'))

    file = open(measure_path)
    measures = json.load(file)
    sound = parselmouth.Sound(path)

    return sound, measures

def pitchfreq(sound, measures, f0min, f0max):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the fundamental frequency values for each frame in the given audio file.

    Parameters:
    ...........
    sound : sound object
        a praat sound object
    measures : dict
        a dictionary containing the measure names for the calculated statistics.
    f0min : int
        the minimum pitch frequency value.
    f0max : int
        the maximum pitch frequency value.

    Returns:
    ...........
    df_pitch : pandas dataframe
        A dataframe containing the fundamental frequency values for each frame in the audio file.

    ------------------------------------------------------------------------------------------------------
    """
    pitch = call(sound, "To Pitch", 0.0, f0min, f0max)
    freq = pitch.selected_array['frequency']

    df_pitch = pd.DataFrame(list(freq), columns= [measures['fundfreq']])
    return df_pitch

def formfreq(sound, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the formant frequency of an audio file.

    Parameters:
    ...........
    sound : sound obj
        a Praat sound object
    measures : config obj
        measures config object

    Returns:
    ...........
    df_formant : pandas dataframe
        a dataframe containing formant frequency values

    ------------------------------------------------------------------------------------------------------
    """
    formant_dict = {}
    formant = sound.to_formant_burg(time_step=.01)

    for i in range(4):
        formant_values = call(formant, "To Matrix", i+1).values[0,:]
        formant_dict['form' + str(i+1) + 'freq'] = list(formant_values)

    cols = [measures['form1freq'], measures['form2freq'], measures['form3freq'], measures['form4freq']]
    df_formant = pd.DataFrame(formant_dict)
    
    df_formant.columns = cols
    return df_formant

def loudness(sound, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the audio intensity of an audio file.

    Parameters:
    ...........
    sound : sound obj
        a Praat sound object
    measures : config obj
        measures config object

    Returns:
    ...........
    df_loudness : dataframe;
        dataframe containing audio intensity values

    ------------------------------------------------------------------------------------------------------
    """
    intensity = sound.to_intensity(time_step=.01)
    df_loudness = pd.DataFrame(list(intensity.values[0]), columns= [measures['loudness']])
    return df_loudness

def jitter(sound, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the jitter of an audio file.

    Parameters:
    ...........
    sound : sound obj
        A Praat sound object
    measures : config obj
        measures config object

    Returns:
    ...........
    df_jitter : pandas dataframe
        A dataframe containing jitter values

    ------------------------------------------------------------------------------------------------------
    """
    pulse = call(sound, "To PointProcess (periodic, cc)...", 75, 500)
    localJitter = call(pulse, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3)
    localabsJitter = call(pulse, "Get jitter (local, absolute)", 0, 0, 0.0001, 0.02, 1.3)

    rapJitter = call(pulse, "Get jitter (rap)", 0, 0, 0.0001, 0.02, 1.3)
    ppq5Jitter = call(pulse, "Get jitter (ppq5)", 0, 0, 0.0001, 0.02, 1.3)
    ddpJitter = call(pulse, "Get jitter (ddp)", 0, 0, 0.0001, 0.02, 1.3)

    cols = [measures['jitter'], measures['jitterabs'], measures['jitterrap'], measures['jitterppq5'],
           measures['jitterddp']]
    vals = [localJitter, localabsJitter, rapJitter, ppq5Jitter, ddpJitter]

    df_jitter = pd.DataFrame([vals], columns= cols)
    return df_jitter

def shimmer(sound, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the shimmer of an audio file.

    Parameters:
    ...........
    sound : sound obj
        a Praat sound object
    measures : obj
        measures config object

    Returns:
    ...........
    df_shimmer : pandas dataframe
        dataframe containing shimmer values

    ------------------------------------------------------------------------------------------------------
    """
    pulse = call(sound, "To PointProcess (periodic, cc)...", 80, 500)
    localshimmer = call([sound, pulse], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    localdbShimmer = call([sound, pulse], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

    apq3Shimmer = call([sound, pulse], "Get shimmer (apq3)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    apq5Shimmer = call([sound, pulse], "Get shimmer (apq5)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    apq11Shimmer =  call([sound, pulse], "Get shimmer (apq11)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    ddaShimmer = call([sound, pulse], "Get shimmer (dda)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

    cols = [measures['shimmer'], measures['shimmerdb'], measures['shimmerapq3'], measures['shimmerapq5'],
           measures['shimmerapq11'], measures['shimmerdda']]
    vals = [localshimmer, localdbShimmer, apq3Shimmer, apq5Shimmer, apq11Shimmer, ddaShimmer]

    df_shimmer = pd.DataFrame([vals], columns= cols)
    return df_shimmer

def harmonic_ratio(sound, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the harmonic noise ratio of an audio file.

    Parameters:
    ...........
    sound : sound obj
        Praat sound object
    measures : config obj
        measures config object

    Returns
    ...........
    df_hnr : dataframe
        dataframe containing harmonic noise ratio values


    ------------------------------------------------------------------------------------------------------
    """
    hnr = sound.to_harmonicity_cc(time_step=.01)
    hnr_values = hnr.values[0]

    hnr_values = np.where(hnr_values==-200, np.NaN, hnr_values)
    df_hnr = pd.DataFrame(hnr_values, columns= [measures['hnratio']])
    return df_hnr

def glottal_ratio(sound, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the glottal noise ratio of an audio file.

    Parameters:
    ...........
    sound : sound obj
        a Praat sound object
    measures : config obj
        measures config object

    Returns:
    ...........
    df_gne : pandas dataframe
        dataframe containing glottal noise ratio values

    ------------------------------------------------------------------------------------------------------
    """
    gne = sound.to_harmonicity_gne()
    gne_values = gne.values

    gne_values = np.where(gne_values==-200, np.NaN, gne_values)
    gne_max = np.nanmax(gne_values)

    df_gne = pd.DataFrame([gne_max], columns= [measures['gneratio']])
    return df_gne

def get_voice_silence(sound, min_silence, measures):
    """
    ------------------------------------------------------------------------------------------------------

    Extracts the silence window of an audio file.

    Parameters:
    ...........
    sound : str
        path to the audio file
    min_silence : int
        minimum silence window length
    measures : obj
        measures config object

    Returns:
    ...........
    df_silence : pandas dataframe
        A dataframe containing the silence window values

    ------------------------------------------------------------------------------------------------------
    """
    audio = AudioSegment.from_wav(sound)
    dBFS = audio.dBFS

    thresh = dBFS-16
    slnc_val = silence.detect_silence(audio, min_silence_len = min_silence, silence_thresh = thresh)
    slnc_interval = [((start/1000),(stop/1000)) for start,stop in slnc_val] #in sec

    cols = [measures['silence_start'], measures['silence_end']]
    df_silence = pd.DataFrame(slnc_interval, columns=cols)

    df_silence[measures['voicesilence']] = df_silence[cols[1]] - df_silence[cols[0]]
    return df_silence

def vocal_acoustics(audio_path):
    """
    ------------------------------------------------------------------------------------------------------

    Calculates the vocal acoustic variables of an audio file.

    Parameters:
    ...........
    audio_path : str
        path to the audio file

    Returns:
    ...........
    framewise : pandas dataframe
        dataframe containing pitch, loudness, HNR, and formant frequency values
    df_silence : pandas dataframe
        dataframe containing the silence window values
    df_summary : pandas dataframe
        dataframe containing the summary of all acoustic variables

    ------------------------------------------------------------------------------------------------------
    """
    try:
        sound, measures = read_audio(audio_path)
        df_pitch = pitchfreq(sound, measures, 75, 500)
        df_loudness = loudness(sound, measures)

        df_jitter = jitter(sound, measures)
        df_shimmer = shimmer(sound, measures)

        df_hnr = harmonic_ratio(sound, measures)
        df_gne = glottal_ratio(sound, measures)
        df_formant = formfreq(sound, measures)
        df_silence = get_voice_silence(audio_path, 500, measures)

        framewise = pd.concat([df_pitch, df_formant, df_loudness, df_hnr], axis=1)
        sig_df = pd.concat([df_jitter, df_shimmer, df_gne], axis=1)

        df_summary = get_summary(sound, framewise, sig_df, df_silence, measures)
        return framewise, df_silence, df_summary

    except Exception as e:
        logger.error(f'Error in acoustic calculation- file: {audio_path} & Error: {e}')
