from flask import Flask, render_template, request, url_for, jsonify, Response, redirect
from werkzeug.utils import secure_filename
import os
from flask_bootstrap import Bootstrap
from fftsampling import _FFTplot
import json
from clearcache import clearcache, clearcache_all
import logging
from filelen import file_ecg_freq, file_ecg_samples_len 
from flask.helpers import flash, send_file, send_from_directory
import hashlib
import sys
from werkzeug.exceptions import RequestEntityTooLarge
from pathlib import Path
from flask_restful import Resource, Api
from random import randint
import datetime
import asyncio
from copy import deepcopy
from edf_process import process_edf

import pycaret
from pycaret.classification import *
from pycaret.datasets import get_data
from flask.json import tojson_filter
from sklearn import datasets
from sklearn.ensemble import RandomForestClassifier

app = Flask(__name__)

#region CONFIGURATION
ALLOWED_EXTENSIONS = set(['ecg', 'ekg', 'ecgplus'])
ALLOWED_EXTENSIONS_EDF = set(['edf'])
ALLOWED_EXTENSIONS_SETTINGS = set(['settings'])

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOAD_FOLDER'] = 'assets/DB/Uploads/'
app.config['UPLOAD_FOLDER_EDFprocess'] = 'assets/DB/UploadsEDF/'
app.config['UPLOAD_FOLDER_EDF'] = 'assets/DB/EDF/'
app.config['GENERATED'] = 'assets/DB/Generated/'
app.config['SAVED_SETTINGS'] = 'assets/settings/' 
app.config['MAX_CONTENT_LENGTH'] = 400 * 1024 * 1024


default_frequency = 125
db_frequencies = {
  "CUDB": 250,
  "EDF": 125,
  "Syn_generated": 250
}
#endregion

api = Api(app)

def randfloat(a,b):
    f = 100
    
    a = round(a*f)
    b = round(b*f)
    r = randint(a,b)
    
    res = r/f
    return res


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def app_handle_413(e):
    # return 'File Too Large', 413
    return render_template('upload.html', msg = "File is too large")

@app.route('/freq_for_db/<db>')
def freq_for_db(db):
    if str(db) in db_frequencies:
        return str(db_frequencies[db])
    else:
        return str(default_frequency)
    
@app.route('/freq_for_file/<db>/<file>')
def freq_for_file(db,file):  
    res_file_ecg = file_ecg_freq(file)
    
    if res_file_ecg != -1:
        return str(res_file_ecg)
    else:
        return freq_for_db(db)

@app.route('/maxSeconds_for_file/<db>/<file>')
def maxSeconds_for_file(db,file):
        file = os.getcwd()+"/assets/DB/"+db+"/"+file
        filelen = int(file_ecg_samples_len(file))
        
        # freq = int(freq_for_db(db))
        freq = int(freq_for_file(db,file))
        
        seconds = round(filelen/freq)
        return str(seconds)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setsettings',methods = ['GET', 'POST'])
def readsettings():
    if request.method == 'POST':
        print(request.form)
            # check if the post request has the file part
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file_settings(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['SAVED_SETTINGS'], filename))
            
            res = open(os.path.join(app.config['SAVED_SETTINGS'], filename))
            
            return (res.read())

    return "D"            
        
    pass

@app.route('/settings',methods = ['GET', 'POST'])
def settings():
    settings_location = 'assets/settings/'
    data = request.form
    if not data:
        return "",404
    
    respond = {}
    exclude = ['view','resolution','samplingrate','presetqrs', 'target_snr']
    for key, value in data.items():
        if key not in exclude:
            respond[key] = value
    
    return str(respond).replace("'","\"")
    
    pass

    
@app.route('/viewer')
def viewer():
    
    print(request.args)
    dbs = alldbs()
    arg_file = request.args.get('file')

    
    return render_template('viewer.html',dbs_list = dbs)    

@app.route('/fft')
def fft():
    upsampled_arg = True
    
    arg_file = request.args.get('file')
    arg_db = request.args.get('db')
    arg_start = request.args.get('start')
    arg_end = request.args.get('end')
    arg_upsampling = request.args.get('upsampled')
    
    start = 0 if not arg_start else float(arg_start)
    end = 4 if not arg_end else float(arg_end)
    upsampled = True if arg_upsampling else False
    
    filepath = os.getcwd()+"/assets/DB/"+arg_db+"/"+arg_file
    freq = int(freq_for_file(arg_db,filepath))
    
    response = _FFTplot(f"assets/DB/{arg_db}/{arg_file}",start,end,freq,"",DRAW_PLOT=False,WRITE_TO_FILE=False,Upsampling=upsampled_arg)

    
    #outputlist = [fig1,fig2]
    #jsonlist = print(json.dumps(outputlist))
    
    #return jsonify(outputlist = list)
    #return Response(json.dumps(out),  mimetype='application/json')
    return response
 
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_file_edf(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_EDF       
               
def allowed_file_settings(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_SETTINGS

@app.route('/api/fft/v1/<db>/<file>/<start_second>/<end_second>', methods = ['POST','GET'])
def fft_web(db,file,start_second,end_second):
    # int_freq = int(frequency)
    int_start_second = int(start_second)
    int_end_second = int(end_second)
    
    freq = int(freq_for_db(db))
    
    try :
        response = _FFTplot(f"assets/DB/{db}/{file}",int_start_second,int_end_second,freq,"",DRAW_PLOT=False,WRITE_TO_FILE=False,Upsampling=False,webservice=True)
        return response
    except:
        return "ERROR", 404
    
@app.route('/uploader', methods = ['GET', 'POST'])
def uploader():
    def_freq = "125"
    arg_freq = request.values["frequency"] if request.values["frequency"]  else def_freq
    
    if request.method == 'POST':
        # check if the post request has the file part
        print(request.files)
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            message = ('No file selected')
            return render_template('upload.html', msg = message)
        if file and allowed_file(file.filename):
            print("allowed")
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            freqfile = open(os.path.join(app.config['UPLOAD_FOLDER'], filename+".freq"),"w")
            freqfile.write(arg_freq)
            freqfile.close()
            
            
            # messages = json.dumps({"main":"Condition failed on page baz"})
            uploadedfile = filename
            return redirect(url_for('.viewer',fileup=uploadedfile))
            # return render_template('viewer.html')
        else:
            print("Not allowd")
            message = "Incorrect file type"
            return render_template('upload.html', msg = message)
            # return redirect(url_for('uploaded_file',
            #                 filename=filename))
    
    return redirect("/upload")

@app.route('/uploaderedf', methods = ['GET', 'POST'])
def uploaderedf():
    
    if request.method == 'POST':
        # check if the post request has the file part
        print(request.files)
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            message = ('No file selected')
            return render_template('uploadedf.html', msg = message)
        if file and allowed_file_edf(file.filename):
            #///////////////////////////
            print("allowed")
            filename = secure_filename(file.filename)
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER_EDFprocess'], filename)            
            file.save(filepath)
            savepathfolder= (app.config['UPLOAD_FOLDER_EDF'])
            
            process_result = process_edf(filepath,savepathfolder,filename)
            #///////////////////////////  
            # messages = json.dumps({"main":"Condition failed on page baz"})
            if process_result:
                return downloadFile(process_result)
                # return redirect(url_for('.viewer',fileup=uploadedfile))
            else:
                message = "Error processing the file"
                return render_template('uploadedf.html', msg = message)
            # return render_template('viewer.html')
        else:
            message = "Incorrect file type"
            return render_template('uploadedf.html', msg = message)
            # return redirect(url_for('uploaded_file',
            #                 filename=filename))
    
    return redirect("/uploadedf")

@app.route('/download')
def downloadFile (path):
    #For windows you need to use drive name [ex: F:/Example.pdf]
    return send_file(path, as_attachment=True)

@app.route('/upload')
def upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            print("allowed")
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # return redirect(url_for('uploaded_file',
            #                 filename=filename))
    
    return render_template('upload.html',msg="")

def alldbs():
    # exclude = ["Uploads"]
    exclude = ["_webservice","Custom","Generated"]
    
    folder = os.getcwd()+"/assets/DB/"
    subfolders = [ f.name for f in os.scandir(folder) if f.is_dir() and not f.name in exclude]
    
    
    return subfolders

@app.route('/all_ecgs/<db>')
def all_ecgs(db):
    path = os.getcwd()+"/assets/DB/"+db+"/"
    try:
        list_of_files = []
        for filename in os.listdir(path):
            if filename[-3:] in ["ecg","ekg"]:
                list_of_files.append((filename))
                
    except:
        return "", 404
        # return page_not_found("e")



    return json.dumps(list_of_files)