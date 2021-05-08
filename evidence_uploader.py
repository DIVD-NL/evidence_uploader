#!/usr/bin/env python3
import argparse
import json
import os
import os.path
import sys
import pickle
import socket
import subprocess
import glob
import random
import time
import shlex
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
]


def login():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    print("Authorizing to Google services.")
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(args.pickle):
        with open(args.pickle, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            if "no_browser" in args and args.no_browser:
                print("Authorizing without local browser and server")
                creds = flow.run_console()
            else:
                print("Authorizing with local browser and server")
                creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(args.pickle, 'wb') as token:
            pickle.dump(creds, token)

    print("Authorization complete.")
    drive  = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    return(
        {
            'drive' : drive,
            'sheets' : sheets,
        }
    )

def find_folder(services):
    drive_service = services['drive']
    response = drive_service.files().list(  q="mimeType='application/vnd.google-apps.folder' and name contains '{}*'  and trashed=False".format(config['case']),
                                            spaces='drive',
                                            fields='nextPageToken, files(id, name, parents)',
                                            supportsAllDrives=True,
                                            includeItemsFromAllDrives=True,
                                          ).execute()
    folders = response.get('files', [])
    if len(folders) == 1:
        print("Found parent folder '{}'".format(folders[0].get("name")))
        return folders[0].get("id")
    elif len(folders) == 0 :
        sys.exit("ERROR: Searching for a folder starting with '{}' returned 0 results".format(args.case))
    else:
        sys.exit("ERROR: Searching for a folder starting with '{}' returned {} results. First folder is {}".format(
            args.case, len(folders), folders[0].get('name'))
        )

def create_target_folder(services, root_folder, folder_name):
    drive_service=services['drive']
    response = drive_service.files().list(  q="mimeType='application/vnd.google-apps.folder' and parents in '{}' and name='{}' and trashed=False".format(root_folder,folder_name),
                                            spaces='drive',
                                            fields='nextPageToken, files(id, name, parents)',
                                            supportsAllDrives=True,
                                            includeItemsFromAllDrives=True,
                                          ).execute()
    folders = response.get('files', [])
    if len(folders) == 0 :
        metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents' : [ root_folder ],
        }
        folder = drive_service.files().create(  body=metadata,
                                                supportsAllDrives=True,
                                                fields='id').execute()
        return folder.get('id');
    else:
        print("The folder '{}' exisits, no need to create it".format(folder_name))
        return folders[0].get('id')

def split_files():
    print("Splitting {} in batches of {} line(s)".format(config['targets'], config['batch']))
    execute("split -l {} {} targets_".format(config['batch'], config['targets']))
    files = sorted(glob.glob("targets_*"))
    print("File split in {} batches".format(len(files)))
    return(files)


def create_sheet(services, target_folder, files):
    response = services['drive'].files().list(  q="mimeType='application/vnd.google-apps.spreadsheet' and parents in '{}' and name='{}' and trashed=False".format(target_folder,'scan_cnc'),
                                                spaces='drive',
                                                fields='files(id, name, parents)',
                                                supportsAllDrives=True,
                                                includeItemsFromAllDrives=True,
                                             ).execute()
    sheets = response.get('files', [])
    if len(sheets) == 0 :
        metadata = {
            'name': 'scan_cnc',
            'parents': [ target_folder],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        sheet = services['drive'].files().create(   body=metadata,
                                                    supportsAllDrives=True,
                                                ).execute()
        print("Sheet 'scan_cnc' created")
    elif len(sheets) == 1 :
        print("Sheet 'scan_cnc' exisis, not creating it, check if content is ok or delete it.")
        sheet=sheets[0]
    else :
        sys.exit("I tried to create or open a sheet called '{}' in folder '{}*/{}' on the cases drive, but it already contains {} sheets with this name".format(
            "scan_cnc", args.case, args.folder, len(sheets)
        ))

    sheet_id=sheet.get('id')
    ss = services['sheets'].spreadsheets()
    result = ss.values().get(    spreadsheetId=sheet_id,
                                 range='A1:E1').execute()

    if not 'values' in result :
        rows = [ ['File', 'Claimed', 'Running', 'Done'] ]
        for f in files:
            rows.append([f])

        data = {
            'range'     : 'A1',
            'values'    : rows
        }
        result = ss.values().append(    spreadsheetId=sheet_id,
                                        range='A1',
                                        valueInputOption='RAW',
                                        body=data
                                    ).execute()
    return(sheet_id)

def claim_file(services, sheet, my_id, filecount):
    response = services['drive'].files().list(  q="mimeType='application/vnd.google-apps.spreadsheet' and parents in '{}' and name='{}' and trashed=False".format(target_folder,'scan_cnc'),
                                                spaces='drive',
                                                fields='files(id, name, parents)',
                                                supportsAllDrives=True,
                                                includeItemsFromAllDrives=True,
                                             ).execute()
    sheets = response.get('files', [])
    if len(sheets) > 1 :
        sys.exit("\nevidence_uploader.py: error: Cannot claim file, there is more then one 'scan_cnc' sheet")

    sheet=sheets[0]
    sheet_id=sheet.get('id')
    data_range = "A1:D{}".format(filecount+1)
    ss = services['sheets'].spreadsheets()
    claimed=""
    while claimed == "" :
        result = ss.values().get(    spreadsheetId=sheet_id,
                                     range=data_range).execute()
        row = 1
        free = []
        for r in result['values']:
            if row > 1:
                if len(r) == 1 or r[1] == "":
                    # File is available
                    free.append(row)
            row=row+1

        if len(free) == 0 :
            # No more options availble
            return None

        claim = random.choice(free)
        print("Claiming file '{}'".format(result['values'][claim][0]))
        data = {
            'range' : "B{}".format(claim),
            'values' : [ [ my_id ] ]
        }
        ss.values().update( spreadsheetId=sheet_id,
                            range='B{}'.format(claim),
                            valueInputOption='RAW',
                            body=data
                          ).execute()

        print("Sleeping 2 seconds to validate claim")
        time.sleep(2)
        result = ss.values().get(    spreadsheetId=sheet_id,
                                     range='A{}:E{}'.format(claim,claim)).execute()
        if result['values'][0][1] == my_id:
            claimed = result['values'][0][0]
            print("Claimed file '{}'".format(claimed))
            data = {
                'range' : "C{}".format(claim),
                'values' : [ [ datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z") ] ]
            }
            ss.values().update( spreadsheetId=sheet_id,
                                range='C{}'.format(claim),
                                valueInputOption='RAW',
                                body=data
                              ).execute()
            return(claimed)
        else:
            print("File '{}' also claimed by '{}', trying to claim a new file...".format(result['values'][0][0], result['values'][0][1]))
            claimed = ""

def upload_files(services,target_folder,pattern):
    drive_service=services['drive']
    files = glob.glob(pattern)
#    mine = magic.Magic(mine=True)
    for file in files:
        metadata = {
            'name': file,
            'parents': [ target_folder],
#            'mimeType': mime.from_file(file)
        }
        media = MediaFileUpload(file) #,mimetype="text/ascii")
        print("Uploading {}".format(file))
        drive_service.files().create(   body=metadata,
                                        media_body=media,
                                        supportsAllDrives=True,
                                    ).execute()

def file_done(services, sheet, file, filecount):
    response = services['drive'].files().list(  q="mimeType='application/vnd.google-apps.spreadsheet' and parents in '{}' and name='{}' and trashed=False".format(target_folder,'scan_cnc'),
                                                spaces='drive',
                                                fields='files(id, name, parents)',
                                                supportsAllDrives=True,
                                                includeItemsFromAllDrives=True,
                                             ).execute()
    sheets = response.get('files', [])
    if len(sheets) > 1 :
        sys.exit("\nevidence_uploader.py: error: Cannot mark file as done, there is more then one 'scan_cnc' sheet")

    sheet=sheets[0]
    sheet_id=sheet.get('id')
    data_range = "A2:D{}".format(filecount+1)
    ss = services['sheets'].spreadsheets()
    result = ss.values().get(    spreadsheetId=sheet_id,
                                 range=data_range).execute()
    row_no = 0
    while result['values'][row_no][0] != file:
        row_no = row_no+1
    row_no = row_no + 2
    data = {
        'range' : "D{}".format(row_no),
        'values' : [ [ datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z") ] ]
    }
    ss.values().update( spreadsheetId=sheet_id,
                        range='D{}'.format(row_no),
                        valueInputOption='RAW',
                        body=data
                      ).execute()
    print("Marked file '{}' as done".format(file))

def execute(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            print(output.strip().decode('utf-8'))
    rc = process.poll()
    return rc


if __name__ == '__main__':

    # Parse command line
    parser = argparse.ArgumentParser(description='Run a scanner, capture the evidence and upload to Google Drive', allow_abbrev=False)

    if '--auth_only' in sys.argv :
        scan=False
        setup=False
    else:
        scan=True
        setup=True

    if '--setup_only' in sys.argv :
        setup=True
        scan=False
    else:
        setup=True
        scan=True

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auth_only', action="store_true", help="Run authentication only to create token.pickle for future use.")
    group.add_argument('--setup_only', action="store_true", help="Only set up the C&C Google sheet, do not scan.")

    parser.add_argument('--config', '-c', type=str, default='./config.json', metavar="PATH", help="Location of the JSON configuration file")
    parser.add_argument('--no-browser', '-n', action="store_true", help="System does not have a local browser to authenticate to google, use alternative flow")
    parser.add_argument('--pickle', '-p', type=str, default='./token.pickle', metavar="PATH", help="Location of the token.pickle file, willb e created if not exisit")

    if setup:
        parser.add_argument('--folder', '-f', type=str, required=True, metavar="FOLDER_NAME", help="Name of the subfolder to store results")

    args = parser.parse_args()

    # Check arguments
    if not os.path.exists(args.config):
        parser.print_help()
        sys.exit("\nevidence_uploader.py: error: Configuration file '{}' does not exist".format(args.config))

    try:
        with open(args.config) as cf:
            config = json.load(cf)
    except:
        sys.exit("\nevidence_uploader.py: error: unable to load JSON config file '{}'".format(args.config))

    if 'case' in args:
        config['case'] = args.case
        if not re.search('^\\d\\d\\d\\d\\-\\d\\d\\d\\d\\d$',config['case']):
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: Case number '{}' is not a valid case number, sytax is YYYY-NNNNN".format(config['case']))

    if scan:
        if not os.path.exists(config['scanner']):
            sys.exit("\nevidence_uploader.py: error: scanner '{}' is not executable".format(config['scanner']))

        if not os.access(config['scanner'], os.X_OK):
            sys.exit("\nevidence_uploader.py: error: scanner '{}' is not executable".format(config['scanner']))

        if not os.path.exists(config['targets']):
            sys.exit("\nevidence_uploader.py: error: targets file '{}' not found".format(config['targets']))

    # Log into google
    services = login()

    if setup:
        my_id = "{}-{}".format(socket.getfqdn(),os.getpid())
        print("This clients ID: {}".format(my_id))
        root_folder=find_folder(services)
        target_folder=create_target_folder(services,root_folder,args.folder)
        files = split_files()
        sheet_id = create_sheet(services,target_folder,files)

    if scan:
        input_file = claim_file(services,sheet_id,my_id, len(files))
        while input_file:
            print(input_file)
            output_file = input_file.replace("targets","output")
            execute("{} {} {}".format(config['scanner'], input_file, output_file))
            upload_files(services, target_folder, "{}{}".format(output_file,config['output_extension']))
            file_done(services, sheet_id, input_file, len(files))
            input_file = claim_file(services,sheet_id,my_id, len(files))
