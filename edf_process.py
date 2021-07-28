import os
import pandas as pd
from scipy import  signal
from pyedflib import highlevel


def process_edf(filepath,savefolderpath,filename):
    RESAMPLE_RATE = 125
    MV_EQUIVALENT_SAMPLES = 170.5
    
    bpm = 0
    bpmstr = ""
    no_samples = 0
    (signals, signal_headers, header) = (None,None,None)
    
    try:
        signals, signal_headers, header = highlevel.read_edf(filepath)
        bpm = signal_headers[0]['sample_rate']
        bpmstr = str(round(signal_headers[0]['sample_rate'],3))
        no_samples=len(signals[0])
        new_samples = int(no_samples/bpm)*RESAMPLE_RATE
    except:
        return False
    
    filenameecgplus = filename+"["+bpmstr+"Hz].ecgplus"
    savefilepath = os.path.join(savefolderpath,filenameecgplus)
    # resampled = signal.resample(signals[0],new_samples)
    resampled = signals[0]
    pd.to_numeric(round(pd.Series(resampled*MV_EQUIVALENT_SAMPLES)),downcast="integer").to_csv(savefilepath,header=None,index=None)
    
    return savefilepath