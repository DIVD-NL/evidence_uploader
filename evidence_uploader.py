#!/usr/bin/env python3
from __future__ import print_function
import pickle
import os
import os.path
import argparse
import sys
import re
import subprocess
import mimetypes
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload


# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/drive.metadata.readonly', 
    #'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
]

def login():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    print("AUthorizing to Google services.")
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

def find_folder(drive_service):
    response = drive_service.files().list(  q="mimeType='application/vnd.google-apps.folder' and name contains '{}*'  and trashed=False".format(args.case),
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

def create_target_folder(drive_service, root_folder, folder_name):
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

def create_sheet(services, target_folder):
    response = services['drive'].files().list(  q="mimeType='application/vnd.google-apps.spreadsheet' and parents in '{}' and name='{}' and trashed=False".format(target_folder,'scan_results'),
                                            spaces='drive',
                                            fields='files(id, name, parents)',
                                            supportsAllDrives=True, 
                                            includeItemsFromAllDrives=True,
                                          ).execute()
    sheets = response.get('files', [])
    if len(sheets) == 0 :
        metadata = {
            'name': 'scan_results',
            'parents': [ target_folder],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        sheet = services['drive'].files().create(   body=metadata,
                                                supportsAllDrives=True, 
                                            ).execute()
        print("Sheet 'scan_results' created")
    elif len(sheets) == 1 :
        print("Sheet 'scan_results' exisis, not creating it")
        sheet=sheets[0]
    else :
        sys.exit("I tried to create or open a sheet called '{}' in folder '{}*/{}' on the cases drive, but it already contains {} sheets with this name".format(
            "scan_results", args.case, args.folder, len(sheets)
        ))

    sheet_id=sheet.get('id') 
    ss = services['sheets'].spreadsheets()
    result = ss.values().get(    spreadsheetId=sheet_id,
                                 range='A1:E1').execute()

    if not 'values' in result :

        data = {
            'range': 'A1',
            'values' : [['IP', 'Timestamp', 'Match', 'txt_url', 'gif_url', 'file_url']],
        }
        result = ss.values().append(    spreadsheetId=sheet_id,
                                        range='A1',
                                        valueInputOption='RAW',
                                        body=data
                                    ).execute()
    return(sheet_id)

def scan_target(target, scanner, argument):
    # Prep commands
    parsed_arg=argument.format(target, target, target, target, target, target, target, target, target, target)
    if args.gif:
        cmd="({} rec /tmp/{}.{} --overwrite -c \"set -x;date;{} {};date\")2>&1".format(args.asciinema, args.case, os.getpid(), scanner, parsed_arg)
    else:
        cmd="(set -x;date;{} {};date)2>&1".format(scanner, parsed_arg)

    #log
    result=execute("date")
    timestamp=str(result[0],'utf-8').strip()
    result=execute(cmd)        
    out = open("{}.log".format(target), "w")
    out.write(str(result[0],'utf-8'))
    out.close()
    
    if args.gif:
        cmd="sed -i -e 's#\"+ #\"> #g' /tmp/{}.{}}".format(args.case, os.getpid())
        execute(cmd)
        cmd="{} /tmp/{}.{} {}.gif;rm /tmp/{}.{}".format(args.asciicast2gif, args.case,  os.getpid(), target, args.case,  os.getpid())
        execute(cmd)
    
    return(timestamp)

def upload_evidence(services,target_folder,sheet_id,target,timestamp,regex):
    drive_service=services['drive']
    data = {
        "ip"        : None,
        "timestamp" : None,
        'match'     : None,
        'txt'       : None,
        'gif'       : None,
        'other'     : None,
    }
    if file_exists(target):
        file = True
        ip = re.search('^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',target)
        if ip:
            ip = ip.group(0)
        else:
            print("File '{}' does not start with an IP address, using filename as systemname".format(target))
            data['ip'] = target

    else:
        ip = target

    if ip:
        print("IP = {}".format(ip))
        data['ip'] = ip
        name="{}.gif".format(ip)
        if file_exists(name):
            metadata = {
                'name': name,
                'parents': [ target_folder],
                'mimeType': 'image/gif',
            }
            media = MediaFileUpload(name,mimetype="image/gif")
            print("Uploading {}".format(name))
            gif = drive_service.files().create(   body=metadata,
                                                    media_body=media,
                                                    supportsAllDrives=True, 
                                                ).execute()
            data['gif']="https://drive.google.com/file/d/{}".format(gif['id'])

        name="{}.log".format(ip)
        if file_exists(name):
            metadata = {
                'name': name,
                'parents': [ target_folder],
                'mimeType': 'text/ascii',
            }
            media = MediaFileUpload(name,mimetype="text/ascii")
            print("Uploading {}".format(name))
            file = drive_service.files().create(    body=metadata,
                                                    media_body=media,
                                                    supportsAllDrives=True, 
                                               ).execute()
            data['txt']="https://drive.google.com/file/d/{}".format(file['id'])

            if regex:
                pattern = re.compile(regex)
                match = False
                for line in open(name, "r"):
                    if re.match(pattern, line):
                        match = True
                        break
                data['match'] = match

            if not timestamp:
                timestamp=time.ctime(os.path.getctime(name))


    if target != "{}.gif".format(ip) and target != "{}.gif".format(ip):
        name = target
        if file_exists(name):
            mimetype=mimetypes.guess_type(name)[0]
            metadata = {
                'name': name,
                'parents': [ target_folder],
                'mimeType': mimetype,
            }
            media = MediaFileUpload(name,mimetype=mimetype)
            print("Uploading {}".format(name))
            file = drive_service.files().create(    body=metadata,
                                                    media_body=media,
                                                    supportsAllDrives=True, 
                                               ).execute()
            data['other']="https://drive.google.com/file/d/{}".format(file['id'])

    print("Adding data to sheet.")
    ss = services['sheets'].spreadsheets()
    row = {
        'range': 'A1',
        'values' : [[ data["ip"], timestamp, data['match'], data['txt'], data['gif'], data['other'] ]],
    }
    result = ss.values().append(    spreadsheetId=sheet_id,
                                    range='A1',
                                    valueInputOption='RAW',
                                    body=row
                                ).execute()    
def done(services):
    result=execute("date")
    timestamp=str(result[0],'utf-8').strip()
    ss = services['sheets'].spreadsheets()
    row = {
        'range': 'A1',
        'values' : [[ "*** DONE ***", timestamp ]],
    }
    result = ss.values().append(    spreadsheetId=sheet_id,
                                    range='A1',
                                    valueInputOption='RAW',
                                    body=row
                                ).execute()    


def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def file_exists(fpath):
    return os.path.isfile(fpath)

def execute(command):
    process = subprocess.Popen(['/bin/bash'], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    print("Executing command: {}".format(command))
    result = process.communicate(bytes(command,'utf-8'))
    print("Output:\n{}".format(str(result[0],'utf-8').strip()))
    return(result)



if __name__ == '__main__':

    # Parse command line
    parser = argparse.ArgumentParser(description='Run a scanner, capture the evidence and upload to Google Drive', allow_abbrev=False)

    if not '--scan_only' in sys.argv : # We need Google
        google=True
    else:
        google=False

    if not '--auth_only' in sys.argv and not "--scan_only" in sys.argv: # If we need to upload to Google
        upload=True
    else:
        upload=False        

    if not '--auth_only' in sys.argv and not "--upload_only" in sys.argv: # If we need to scan    
        scan=True
    else:
        scan=False

    if '--gif' in sys.argv:
        gif=True
    else:
        gif=False

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auth_only', action="store_true", help="Run authentication only to create token.pickle for future use.")
    group.add_argument('--upload_only', action="store_true", help="Only upload results, do not scan")
    group.add_argument('--scan_only', action="store_true", help="Only scan targets, do not upload results")

    if upload:
        parser.add_argument('--case', '-c', type=str, required=True, metavar="YYYY-NNNNN", help="DIVD case number, without 'DIVD-' e.g. DIVD-2020-00001 is 2020-00001")
        parser.add_argument('--folder', '-f', type=str, required=True, metavar="FOLDER_NAME", help="Subfolder to put evidence in (will be craeted if it doesn't exisit)")

    if scan:
        parser.add_argument('--scanner', '-s', type=str, required=True, metavar="SCRIPT", help="File containing the scan script")
        parser.add_argument('--argument', '-a', type=str, required=False, metavar="PYTHON_STRING", default="{}", help="Argument string to the scan script \{\} will be replaced by the target")
        parser.add_argument('--gif', action="store_true", help="Record scanner as animated gif")
        
    parser.add_argument('--asciinema', type=str, metavar="PATH", default="/usr/bin/asciinema", help="Full path to asciinema")
    parser.add_argument('--asciicast2gif', type=str, metavar="PATH", default="/usr/local/bin/asciicast2gif", help="Full path to asciicast2gif")

    if upload:
        parser.add_argument('--regex', '-r', type=str, metavar="REGEX", help="Regular expression to apply to the result of the scan script")

    if google:
        parser.add_argument('--no-browser', '-n', action="store_true", help="System does not have a local browser to authenticate to google, use alternative flow")
        parser.add_argument('--pickle', '-p', type=str, default='./token.pickle', metavar="PATH", help="Location of the token.pickle file, willb e created if not exisit")

    if scan or upload:
        parser.add_argument('--targets', '-t', type=str, required=False, metavar="TARGETS_FILE", help="File containing the targets to scan")
        parser.add_argument('files', metavar="FILE", type=str, nargs="*", help="Evidence files to be uploaded, used when --targets is not specified but we are uploading")

    args = parser.parse_args()

    # Check arguments
    if 'case' in args:
        if not re.search('^\\d\\d\\d\\d\\-\\d\\d\\d\\d\\d$',args.case) :
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: Case number '{}'' is not a valid case number, sytax is YYYY-NNNNN".format(args.case))

    if "targets" in args and args.targets:
        if not file_exists(args.targets):
            sys.exit("\nevidence_uploader.py: error: The file with scan targets '{}' does not exist".format(args.targets))

    if "scanner" in args and args.scanner:
        if not is_exe(args.scanner):
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: The scanner script '{}' does not exist or is not executable".format(args.scanner))

    if "gif" in args and args.gif:
        if not is_exe(args.asciinema):
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: asciinema binary '{}' does not exist or is not executable".format(args.asciinema))
        if not is_exe(args.asciicast2gif):
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: asciicast2gif binary '{}' does not exist or is not executable".format(args.asciicast2gif))

    if scan:
        if not "targets" in args or not args.targets:
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: --targets is mandatory when scanning")

    if upload:
        if (not "targets" in args or not args.targets) and (not "files" in args or len(args.files) == 0):
            parser.print_help()
            sys.exit("\nevidence_uploader.py: error: when uploading you must specify --targets or specific files to upload")

    if "target" in args and "files" in args and len(args.files) > 0:
        parser.print_help()
        sys.exit("\nevidence_uploader.py: error: you cannot use the --targets and specify specific files to upload at the same time")


    if "files" in args:
        for file in args.files:
            if not file_exists(file):
                sys.exit("You specified that file '{}' should be uploaded, but it does not exist".format(file))

    if google :
        services = login()
    
    if upload:
        # Open/create folder and create spreadsheet 
        root_folder=find_folder(services.get('drive'))
        target_folder=create_target_folder(services.get('drive'),root_folder,args.folder)
        sheet_id=create_sheet(services,target_folder)


    if upload or scan:
        #Building target list
        if "targets" in args and args.targets:
            targetf = open(args.targets, 'r')
            targets=targetf.readlines()
            targetf.close
        else:
            targets=args.files

        # Scan and/or upload each target
        for target in targets:
            target = target.strip()

            if scan:
                timestamp = scan_target(target, args.scanner, args.argument)
            else:
                timestamp=None

            if upload:
                upload_evidence(services,target_folder,sheet_id,target,timestamp,args.regex)

    if upload:
        done(services)