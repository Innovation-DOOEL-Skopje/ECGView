import os
import sys
import os.path

dir_path = os.path.dirname(os.path.realpath(__file__))

def write_file_ecg_len(filepath):
    l=0
    fopen = open(filepath)
    print(fopen.name)
    for line in fopen:
        l+=1
    print(l)
    fw = open(filepath+".len",'w+')
    fw.write(str(l))
    fopen.close()
    fw.close()
    
    return l

def write_folder_len(folder=dir_path):
    for path, subdirs, files in os.walk(folder):
        
        for filename in files:
            if filename[-4:] != ".ecg":
                continue
            write_file_ecg_len(path+"\\"+filename)

def file_ecg_samples_len(file)->int:
    size = -1
    lenfile = file+".len"
    if os.path.exists(lenfile):
        lenfileopen = open(lenfile,'r')
        for line in lenfileopen:
            size = int(line)
            break
    else:
        size = write_file_ecg_len(file)
         
    return size

def file_ecg_freq(file)->int:
    freq = -1
    freqfile = file+".freq"
    if os.path.exists(freqfile):
        freqfileopen = open(freqfile,'r')
        for line in freqfileopen:
            try:
                freq = int(line)
            except:
                freq = -1
                
            break
    else:
        return -1
        
    return freq