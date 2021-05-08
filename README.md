DIVD Evidence uploader
======================

Tool to do do a distributed scan and upload the results to Google drive

```
usage: evidence_uploader.py [-h] [--auth_only | --setup_only] [--config PATH] [--no-browser]
                            [--pickle PATH] --folder FOLDER_NAME

Run a scanner, capture the evidence and upload to Google Drive

optional arguments:
  -h, --help            show this help message and exit
  --auth_only           Run authentication only to create token.pickle for future use.
  --setup_only          Only set up the C&C Google sheet, do not scan.
  --config PATH, -c PATH
                        Location of the JSON configuration file
  --no-browser, -n      System does not have a local browser to authenticate to google, use
                        alternative flow
  --pickle PATH, -p PATH
                        Location of the token.pickle file, willb e created if not exisit
  --folder FOLDER_NAME, -f FOLDER_NAME
                        Name of the subfolder to store results
```

In order to use this tool you need:
* A Google account in the DIVD organisation
* Create credentials.json using this page: https://developers.google.com/drive/api/v3/quickstart/python (make sure you are logged into you divd.nl account)
* Alternatively, ask Frank for credentials and a whitlisting
* Enable Google Sheets on your credentials, see: https://support.google.com/googleapi/answer/6158841?hl=en
* Certain os and Python packages, see prep-ubuntu.sh to give you an idea
