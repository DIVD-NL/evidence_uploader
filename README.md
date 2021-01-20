DIVD Evidence uploader
======================

Tool to upload evidence from a scan to the appropriate DIVD Google Drive and log the evidence in a Google Sheet

The tool can optionally:
* AUthenticate you to Google
* Run the scanner for you
* Grep for a pattern (indicating (in-)vulnerability)
* Record the session as a gif file and upload that too


```
usage: evidence_uploader.py [-h] [--auth_only | --upload_only | --scan_only]
                            --case YYYY-NNNNN --folder FOLDER_NAME
                            [--targets FILE | --glob *.gif] --scanner SCRIPT
                            [--argument PYTHON_STRING] [--gif]
                            [--asciinema PATH] [--asciicast2gif PATH]
                            [--regex REGEX] [--no-browser] [--pickle PATH]

Run a scanner, capture the evidence and upload to Google Drive

optional arguments:
  -h, --help            show this help message and exit
  --auth_only           Run authentication only to create token.pickle for
                        future use.
  --upload_only         Only upload results, do not scan
  --scan_only           Only scan targets, do not upload results
  --case YYYY-NNNNN, -c YYYY-NNNNN
                        DIVD case number, without 'DIVD-' e.g. DIVD-2020-00001
                        is 2020-00001
  --folder FOLDER_NAME, -f FOLDER_NAME
                        Subfolder to put evidence in (will be craeted if it
                        doesn't exisit)
  --targets FILE, -t FILE
                        File containing the targets to scan
  --glob *.gif, -g *.gif
                        Filesystem pattern for evidence files, used when
                        --targets is not specified and we are not scanning
  --scanner SCRIPT, -s SCRIPT
                        File containing the scan script
  --argument PYTHON_STRING, -a PYTHON_STRING
                        Argument string to the scan script \{\} will be
                        replaced by the target
  --gif                 Record scanner as animated gif
  --asciinema PATH      Full path to asciinema
  --asciicast2gif PATH  Full path to asciicast2gif
  --regex REGEX, -r REGEX
                        Regular expression to apply to the result of the scan
                        script
  --no-browser, -n      System does not have a local browser to authenticate
                        to google, use alternative flow
  --pickle PATH, -p PATH
                        Location of the token.pickle file, willb e created if
                        not exisit
```

In order to use this tool you need:
* A Google account in the DIVD organisation
* Create credentials.json using this page: https://developers.google.com/drive/api/v3/quickstart/python (make sure you are logged into you divd.nl account)
* Alternatively, ask Frank from credentials and a whitlisting
* Certain packages (a lot if you want gifs as well), see prep-ubuntu.sh to give you an idea