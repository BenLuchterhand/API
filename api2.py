# {{ ansible_managed }}
import flask
from flask import request, jsonify, abort, json, flash, send_file
from werkzeug.utils import secure_filename
import uuid
from http import HTTPStatus
import os
from pathlib import Path
import filetype
import db
import os

# CHANGE: Eventually a disposable folder since this is temporary. 
#         Files will reside in database.
UPLOAD_FOLDER = "/Users/xaviermerino/Documents/VagrantEnvironments/REST/uploads"

# CHANGE: Modify this to accept audio recordings.
ALLOWED_EXTENSIONS = ['png', 'jpg']

app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 0.5 * 1024 * 1024

# Tested, works.
# Go to the browser localhost:5000

@app.route('/', methods=['GET'])
def server_check():
    string = "<h1>API Server Running</h1>"
    return string

# Tested, works.
# curl -i -H "Content-Type: application/json" 
#         -X GET localhost:5000/api/v1/incidents  

@app.route('/api/v1/incidents', methods=['GET'])
def get_all_incidents():
    return jsonify(incidents)


# Tested, works.
# curl -i -H "Content-Type: application/json" 
#         -X GET localhost:5000/api/v1/incidents/100

@app.route('/api/v1/incidents/<incident_id>', methods=['GET'])
def get_incident_by_id(incident_id):
    return db.get_incident_by_id(incident_id)


# Tested, works.
# curl -i -H "Content-Type: application/json" 
#         -X POST localhost:5000/api/v1/incidents 
#         -d '{"latitude":"123", "longitude":"1234"}'

# curl -i -H "Content-Type: application/json" 
#         -X POST localhost:5000/api/v1/incidents 
#         -d '{"latitude":"123", "longitude":"1234", "recording":"13d46b49f9f4"}'

@app.route('/api/v1/incidents', methods=['POST'])
def create_new_incident():
    recording = request.json.get('recording')
    latitude = request.json['latitude']
    longitude = request.json['longitude']

    report = {
        'latitude': latitude,
        'longitude': longitude
    }

    if recording:
        report['recording'] = recording

    incident_id = db.insert_new_incident(report)
    result = {
        'incident_id' : incident_id,
        'message' : "Incident Reported"
    }
    
    return jsonify(result), 201


# Tested, works.
# curl -i -X POST localhost:5000/api/v1/resources/recordings 
#         -F 'file=@/Users/xaviermerino/Pictures/graph.png'

@app.route('/api/v1/resources/recordings', methods=['POST'])
def upload_recording():
    if 'file' not in request.files:
        flash('No file!')
    
    # CHANGE: Once you know the exact content type
    # you will be able to put more details. Although
    # it seems like this will just suffice. Content-Type
    # should be audio/m4a

    target_random_filename = str(uuid.uuid4())[-12:]
    submitted_file = request.files['file']
    if submitted_file and allowed_filename(submitted_file.filename):
        filename = secure_filename(submitted_file.filename)
        extension = Path(filename).suffix
        upload_folder = Path(UPLOAD_FOLDER)
        upload_folder.mkdir(exist_ok=True, parents=True)
        submitted_file.save(upload_folder / target_random_filename)
        recording_id = str(db.insert_new_recording(str(upload_folder / target_random_filename)))
        os.remove(upload_folder / target_random_filename)

        out = {
            'status': HTTPStatus.OK,
            'recording_id': recording_id
        }

        return jsonify(out)


# Tested, works.
# Just paste this in a browser: 
# localhost:5000/api/v1/resources/recordings/<recording_id>

@app.route('/api/v1/resources/recordings/<recording_id>', methods=['GET'])
def get_recording_by_id(recording_id):
    recording_data = db.get_recording_by_id(recording_id)
    upload_folder = Path(UPLOAD_FOLDER)
    new_file = open(str(upload_folder / recording_id), 'wb')
    new_file.write(recording_data)
    new_file.close()
    kind = filetype.guess(str(upload_folder / recording_id))

    try:
        return send_file(str(upload_folder / recording_id), 
                as_attachment=True,
                attachment_filename=recording_id + "." + kind.extension)
    except FileNotFoundError:
        abort(404)


def allowed_filename(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# How to use it from a client's perspective?
# Goal: Report an incident
# Steps: 
#   1) Upload a recording.
#           curl -i -X POST localhost:5000/api/v1/resources/recordings 
#                   -F 'file=@/Users/xaviermerino/Pictures/graph.png'
#      This returns: 
#           {
#               "recording_id": "<recording_database_assigned_id>", 
#               "status": 200
#           }
#
#   2) Create a new incident. Use the `recording_id` to attach that recording to the incident.
#           curl -i -H "Content-Type: application/json" 
#                   -X POST localhost:5000/api/v1/incidents 
#                   -d '{"latitude":"123", "longitude":"1234", "<recording_database_assigned_id>"}'
#
#       The following incident was created:
#           {
#               "id": "0b2b23015180", 
#               "latitude": "123", 
#               "longitude": "1234", 
#               "recording": "<recording_database_assigned_id>"
#           }   
#
#   3) Get the incident. 
#           curl -i -H "Content-Type: application/json" 
#                   -X GET localhost:5000/api/v1/incidents/0b2b23015180
#
#   4) Download the recording by visiting this site: 
#           localhost:5000/api/v1/resources/recordings/13d46b49f9f4

app.run(host='0.0.0.0')