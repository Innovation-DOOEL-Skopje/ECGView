from Spans import *
import re

class Span_reader(object):
     def fill_values(self, sList:SpansList, file, end_sample:int=-1):
        pass


class Span_reader_normal(Span_reader):
    
    def fill_values(self, sList:SpansList, file, end_sample:int=-1):
            annfile = open(file)
            rem_note =""
            for line in annfile:
                params = line.strip().split(",")
                if len(params) == 3:
                    #print(params, len(params))
                    sample_no = int(params[0])            
                    sList.add(span(sample_no,span_info=rem_note))
                    rem_note = params[2].strip("(")
                
            if end_sample>0:
                sList.add(span(end_sample,span_info=rem_note))
                
            if sList.spans_collection[0].span_info == "":
                sList.spans_collection[0].span_info = sList.spans_collection[1].span_info
                
class Span_reader_AHADB(Span_reader):
    
    def fill_values(self, sList:SpansList, file, end_sample:int=-1):
            annfile = open(file)
            signal = ""
            for line in annfile:
                signal += line
            
            signalT = re.sub(r'(V\n\d+,N\n\d+,N)(\n\d+,V\n\d+,N\n\d+,N){1,}' ,'+,(B', signal)
            signalB = re.sub(r'(V\n\d+,N)(\n\d+,V\n\d+,N){2,}','+,(VF',signalT)
            signalVT = re.sub(r',[VF](\n\d+,[VF]){2,}',',+,(VT',signalB)
            signalVF = re.sub(r'\[(\n\d.+)+\]',r'+,(VF\1+,*',signalVT)
            signalVF = re.sub(r',\[',r',+,(VF',signalVF)
            signalN = re.sub(r',N(\n\d+,N){1}',',+,(N',signalVF)

            signal_re = ""
            note=""
            for line in signalN.split("\n"):
                params = line.split(",")
                if len(params) == 3:
                    if params[2] == "*":
                        signal_re += line.replace("*",note)+"\n"
                        continue
                    if params[2] != "(VF":
                        note = params[2]
                            
                signal_re += line+"\n"
            #
            splitSignal = signal_re.split("\n")
            
            rem_note =""
            for line in splitSignal:
                params = line.strip().split(",")
                if len(params) == 3:
                    #print(params, len(params))
                    sample_no = int(params[0])            
                    sList.add(span(sample_no,span_info=rem_note))
                    rem_note = params[2].strip("(")
                
            if end_sample>0:
                sList.add(span(end_sample,span_info=rem_note))
                
            if sList.spans_collection[0].span_info == "":
                sList.spans_collection[0].span_info = sList.spans_collection[1].span_info
