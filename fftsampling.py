# Fourier transform EKG files
from flask import jsonify
import numpy as np
import matplotlib.pyplot as plotter
from matplotlib.transforms import Bbox
import matplotlib as mpl
import peakdetection
from peakdetection import peakdet
from numpy import NaN, Inf, arange, isscalar, asarray, array, trapz, interp
from datetime import datetime
from pathlib import Path

#default sampling frequency
SAMPLING_FREQUENCY = 125

def _FFTplot(filename: str, start_second=0.0, end_second=4.0, samplingFrequency=SAMPLING_FREQUENCY,\
    EKG_sequence_type='', test_freq=0, DRAW_PLOT=False, WRITE_TO_FILE=True, path_write="",Upsampling=False,Upsamplingx2=False,webservice=False):

    #region CONFIGURATION
    SAVE_FOLDER = "static/plot_pics"   
    UPSAMPLING = Upsampling
    MAX_AMPLITUDE_EKG = 1023
    MIN_L1_FREQUENCY = 1.5
    MAX_L1_FREQUENCY = 8
    SHIFT_LEFT_FREQUENCY = 0
    WIDTH_FFT_FREQUENCY = 10
    AREA_INTEGRATION_MAGNITUDE = 1    
    #endregion
    
    SHOW_PLOT = True
    
    if not path_write:
        now = datetime.now()
   
    file_EKG = open(filename, 'r')
    Voltages_EKG_samples = []
    

    count1023s = 0
    line = 0
    # Read and normalize EKG file
    for sample_line in file_EKG:
        line += 1
        if (start_second * samplingFrequency) < line <= (end_second * samplingFrequency):
            # normalize it from -1 to +1
            value = ((float(sample_line) / (MAX_AMPLITUDE_EKG)) * 2) - 1       
            Voltages_EKG_samples.append(value)
            
            if float(sample_line)==1023:
                count1023s+=1
    file_EKG.close()

    flagAT = False
    limit1023s = 0.5
    
    if (limit1023s*samplingFrequency)<=count1023s:
        flagAT = True
        EKG_sequence_type = "Noise"    
 
    #fft 
    divider = 1
    #region UPSAMPLING
    UPSAMPLINGX2 = Upsamplingx2
    upsampled_EKGs = []
    if UPSAMPLING:
        divider = 2
        samplingFrequency *= 2
        SHIFT_LEFT_FREQUENCY *= 1
        WIDTH_FFT_FREQUENCY *= 1
        for index, v_ekg in enumerate(Voltages_EKG_samples):
            upsampled_EKGs.append(v_ekg)
            if index+1<len(Voltages_EKG_samples):
                upsampled_EKGs.append((v_ekg+Voltages_EKG_samples[index+1])/2)
                
        upsampled_EKGs.append(Voltages_EKG_samples[-1])
        Voltages_EKG_samples = upsampled_EKGs
        
        upsampled_EKGs = []
        if UPSAMPLINGX2:
            divider = 4
            samplingFrequency *= 2
            
            for index, v_ekg in enumerate(Voltages_EKG_samples):
                upsampled_EKGs.append(v_ekg)
                if index+1<len(Voltages_EKG_samples):
                    upsampled_EKGs.append((v_ekg+Voltages_EKG_samples[index+1])/2)
                    
                upsampled_EKGs.append(Voltages_EKG_samples[-1])
                Voltages_EKG_samples = upsampled_EKGs
    #endregion
           
    samplingInterval = float(1 / samplingFrequency)

    # Time points
    time = np.linspace(start_second, end_second, len(Voltages_EKG_samples))

    # Testing with sinusioid pure frequencies
    if test_freq > 0:
        test_freq = 5
        # Create sine waves for testing
        test_wave1 = np.sin(2 * np.pi * test_freq * time)
        Voltages_EKG_samples = test_wave1

    # Frequency domain representation
    fourierTransformECG = np.fft.fft(Voltages_EKG_samples,len(Voltages_EKG_samples)*divider) / len(Voltages_EKG_samples)

    tpCount = len(Voltages_EKG_samples)             # eg 2500 EKG data points for 10 sec.
    values = np.arange(int(tpCount)*20)         # eg *10, max 2500 value points
    timePeriod = tpCount / samplingFrequency  # eg 2500/250 = 10 (sec)
    frequencies = (values / timePeriod)/divider       # 2500/10(s) = 250 freq. points

    diff = (end_second - start_second) * WIDTH_FFT_FREQUENCY  # (originally 250 frequencies)

    shift_freq = SHIFT_LEFT_FREQUENCY * (end_second - start_second )
    frequencies_plot = frequencies[0:len(abs(fourierTransformECG))]

    values_plot = abs(fourierTransformECG)

    # Peaks detection
    sensitivity = 0.001
    maxtab, mintab = peakdet(array(abs(fourierTransformECG[int(shift_freq):int(shift_freq) + int(diff)*int(divider)])), sensitivity)

    L1 = [0+SHIFT_LEFT_FREQUENCY, 0]
    L2 = [0+SHIFT_LEFT_FREQUENCY, 0]
    L3 = [0+SHIFT_LEFT_FREQUENCY, 0]

    all_peaks = (array(maxtab))
    limitpeaks = []
    
    LN_peaks = []
    LM_peaks = []

    for timevaluepair in all_peaks:
        t = (timevaluepair[0]/((end_second-start_second)*divider))
        v = timevaluepair[1]
        if 0.675 <= t <= 2:
            LN_peaks.append([t,v])
            
        if 0.625 <= t <= 1.375:
            LM_peaks.append([t,v])

        if MIN_L1_FREQUENCY <= t <= MAX_L1_FREQUENCY:
            limitpeaks.append([t,v])
            if v > L3[1]:
                L3[1] = v
                L3[0] = t

            if L3[1] > L2[1]:
                temp = L2
                L2 = L3
                L3 = temp

            if L2[1] > L1[1]:
                temp = L1
                L1 = L2
                L2 = temp

    def Sort(sub_li): 
        sub_li.sort(key = lambda x: x[1], reverse=True)
        return sub_li 


    LN_peak = [0,0] if  len(LN_peaks)==0 else Sort(LN_peaks)[0]
    LM_peak = [0,0] if  len(LM_peaks)==0 else Sort(LM_peaks)[0]

    #INTEGRATION
    L1_INTEGRATIONRANGE: float = 0.2
    L_NEIGHBOURGH_POINTS: float = 0.25
    integrationX, integrationY = [], []
    Area_integrationL1 = 0
    Area_integrationL2 = 0
    Area_integrationL3 = 0

    def Integration_for_point(P:array):
        if(P[0]>0):
            c=0                
            for v in values_plot:
                if v==P[1]:
                    print(c)
                    break
                c+=1
            slice_x = c
            
            print(values_plot[slice_x])
            left_value = values_plot[int(slice_x)-1]
            right_value = values_plot[int(slice_x)+1]
            sum = left_value + P[1] + right_value
            return sum
        else:
            return 0
            
    def Integration_between_points(min_fq,max_fq):
        freq_spacing = len(frequencies_plot)/samplingFrequency
        min = int((freq_spacing*min_fq)//1)
        max = int((freq_spacing*max_fq)//1)
        
        xvals = frequencies_plot[min:max+1]
        yvals = values_plot[min:max+1]
        area = abs(trapz(yvals,xvals))
        return area
    
    Area_integrationL1 = Integration_for_point(L1)
    Area_integrationL2 = Integration_for_point(L2)
    Area_integrationL3 = Integration_for_point(L3)
    Area_integrationLN = Integration_for_point(LN_peak)
    Area_integrationLM = Integration_for_point(LM_peak)
    
    if flagAT:
        #manual values
        Area_integrationAL = 0.2
        Area_integrationAH = 0.8
    else:
        Area_integrationAL = Integration_between_points(0.5,2)
        Area_integrationAH = Integration_between_points(2,8)
    AreaAT = Area_integrationAL+Area_integrationAH


    Area_integrationL1 *= AREA_INTEGRATION_MAGNITUDE
    Area_integrationL2 *= AREA_INTEGRATION_MAGNITUDE
    Area_integrationL3 *= AREA_INTEGRATION_MAGNITUDE
    Area_integrationLN *= AREA_INTEGRATION_MAGNITUDE

    def isHarmonic(val1,val2):
        tolerance = 0.0
        l1, l2 = val1, val2
        if(val2>val1):
            l1, l2 = val2, val1

        n:float=l1/l2
        if abs(n-round(n,0)) < tolerance:
            return "YES"
        else:
            return "NO"


    if EKG_sequence_type:
        EKG_sequence_type = EKG_sequence_type.strip('(')

    def seconds_to_string(secint):
        minutes = int(secint / 60)
        seconds = secint - (minutes * 60)
        return str(minutes).zfill(2) + ":" + str(seconds).zfill(2)
    def timestring(dt_time):
        return str(dt_time.year) + str(dt_time.month) + str(dt_time.hour) + str(dt_time.minute) + str(dt_time.second) 
    
    def full_extent(ax, pad=0.0):
        # For text objects, we need to draw the figure first, otherwise the extents
        # are undefined.
        ax.figure.canvas.draw()
        items = ax.get_xticklabels() + ax.get_yticklabels() 
         #    items += [ax, ax.title, ax.xaxis.label, ax.yaxis.label]
        items += [ax, ax.title]
        bbox = Bbox.union([item.get_window_extent() for item in items])

        return bbox.expanded(1.0 + pad, 1.0 + pad)

    if (EKG_sequence_type != "" or SHOW_PLOT):
        sec_str = str(end_second - start_second)
        if len(sec_str) == 1:
            sec_str = "0" + sec_str

        now = datetime.now()
        
##################################
    
    #region Standard response
    response_dict = {
        "file": Path(filename).name,
        "start_time": str(round(start_second,2)),
        "end_time": str(round(end_second,2)),
        "duration_time": str(round(end_second-start_second,2)),
        "timeDataPoints": time.tolist(),
        "timeValuePoints": Voltages_EKG_samples,
        "freqDataPoints" : frequencies_plot.tolist(),
        "freqValuePoints": values_plot.tolist(),
        "L1" : L1[0],
        "V1" : L1[1],
        "L2" : L2[0],
        "V2" : L2[1],
        "L3" : L3[0],
        "V3" : L3[1],
        "LM" : LM_peak[0],
        "VM" : LM_peak[1],
        "LN" : LN_peak[0],
        "VN" : LN_peak[1],
        "A1" : Area_integrationL1,
        "A2" : Area_integrationL2,
        "A3" : Area_integrationL2,
        "AM" : Area_integrationLM,
        "AN" : Area_integrationLN,
        "AL": Area_integrationAL,
        "AH": Area_integrationAH,
        "AT": AreaAT
    }
    #endregion
    
    response_webservice = {}
    if webservice:
        response_webservice = {
            "starting_Frequency": frequencies_plot[0],
            # "freqDataPoints" : frequencies_plot.tolist(),
            "freqValuePoints": values_plot.tolist(),
            "frequencyResoltion": 1/timePeriod,
            "L1" : L1[0],
            "V1" : L1[1],
            "L2" : L2[0],
            "V2" : L2[1],
            "L3" : L3[0],
            "V3" : L3[1],
            "LM" : LM_peak[0],
            "VM" : LM_peak[1],
            "LN" : LN_peak[0],
            "VN" : LN_peak[1],
            "A1" : Area_integrationL1,
            "A2" : Area_integrationL2,
            "A3" : Area_integrationL2,
            "AM" : Area_integrationLM,
            "AN" : Area_integrationLN,
            "AL": Area_integrationAL,
            "AH": Area_integrationAH,
            "AT": AreaAT
        }
    
    response_json = jsonify(response_dict) if not webservice else jsonify(response_webservice)
   
    return response_json