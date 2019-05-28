# ---------------------------------------------------------------------------------------------------------------------
# Name:        DetectEdits.py
# Purpose:      detect and report Edits in feature service layers
#
# Notes:        Uses python 3.x but should work with 2.x (not tested) *IF* requests module is installed
#
# Author:       ESRI Applications Prototype Lab
#
# Created:      12/14/2017
#               Send an email (option - 1 email for many changes or 1 for each change
#               The assumption is made that lastEdited date is UTC time. (default for AGOL feature services)
#    01/02/18   Show UTC time values in email
#               Use micro seconds in feature/row query
# ---------------------------------------------------------------------------------------------------------------------
import os
import socket
import datetime
import smtplib
from email.message import EmailMessage
import requests
import json
import sys

def main(cfile):
    starttime = gettime()
    dateformat = "%m/%d/%Y %I:%M:%S.%f %p"

    # Build some paths
    scriptpath = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    messagepath = os.path.join(scriptpath, 'DetectEdits')

    # check for the configuration file
    if not os.path.exists(cfile):
        errlogname = generrlogname()
        emsg = '\nConfiguration file({}) does not exist . . . Returning'.format(cfile)
        print(emsg)
        writeerror(errlogname, emsg)
        return

    # Get the configuration information
    cfg = json.load(open(cfile))

    # check for existence of 'DetectEdits' folder - create it if needed
    if not os.path.exists(messagepath):
        os.mkdir(messagepath)

    # URLs - service, viewer, and token
    fsurl = cfg['service']['fsURL']
    if fsurl[-1] == '/':
        urlLyr = '{}{}'.format(fsurl, cfg['service']['fsLayerNum'])
    else:
        urlLyr = '{}/{}'.format(fsurl, cfg['service']['fsLayerNum'])

    portalURL = cfg['service']['portalURL']
    if portalURL[4] == ':':
        portalURL = portalURL.replace(':', 's:')

    viewerurl = '{}/home/webmap/viewer.html'.format(portalURL)
    sharingurl = '{}/sharing'.format(portalURL)

    # Get a token
    referingclient = socket.gethostbyname(socket.gethostname())
    servicetoken = getToken(sharingurl, cfg['service']['serviceuser'],
                            cfg['service']['servicepw'], referingclient)

    # Get service info (sinfo)
    siresult = requests.request('GET', '{}?f=pjson&token={}'.format(urlLyr, servicetoken))
    sinfo = siresult.json()

    try:
        # if edtifieldInfo is not there - editor tracking is NOT enabled
        editfieldsDict = sinfo['editFieldsInfo']
    except:
        errlogname = generrlogname()
        emsg = '\nEditor tracking is not enabled . . . Returning'
        print(emsg)
        writeerror(errlogname, emsg)
        return

    # Get the maximum date & time from the service.  This is UTC time
    maxeditdate = getMaxDate(urlLyr,  editfieldsDict['creationDateField'], 'lasteditdate', servicetoken) / 1000. + 0.001
    maxeditdatestring = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(maxeditdate), dateformat)

    # Read the previous edit date file if it exists, in not then make it and exit
    lasteditfilename = cfg['filenames']['lasteditfile']

    if not os.path.exists(os.path.join(messagepath, lasteditfilename)):
        lastDict = {"lasteditdate": [{"id": cfg['service']['fsLayerNum'], "lasteditdate": maxeditdate,
                                      "lasteditstring": maxeditdatestring}]}
        writecachefile(lastDict, os.path.join(messagepath, lasteditfilename))
        print('Initial Editor Tracking File written . . . returning')
        return

    # read the file to get the previous last edit date stored (both timestamp and string - use the string)
    lastedited = readcachefile(os.path.join(messagepath, lasteditfilename))
    lasteditdatestring = lastedited['lasteditdate'][0]['lasteditstring']

    # Get the fields to report and all fields
    requestedfields = cfg['service']['fieldstoreport']
    fieldsList = sinfo['fields']
    fieldsDict = {}
    for f in fieldsList:
        fieldsDict[f['name'].upper()] = f

    # be sure requested fields are in the table
    outfieldslist = []
    bfields = []

    if requestedfields[0] == '*':
        outfields = '*'
    else:
        for fname in requestedfields:
            if fname.upper() in fieldsDict.keys():
                outfieldslist.append(fname)
            else:
                bfields.append(fname)
        outfieldslist.append(editfieldsDict['creationDateField'])
        outfieldslist.append(editfieldsDict['creatorField'])
        outfields = ",".join(outfieldslist)
    if len(bfields) > 0:
        errlogname = generrlogname()
        emsg = 'The following requested field(s) are not in the service: {}' \
               '\nPlease check the fieldstoreport key in the configuration file'.format(bfields)
        print('Requested fields: {}'.format(emsg))
        writeerror(errlogname, emsg)
        return

    # set up a query to select rows with a time string > lastedited time string
    params = {'where': "{}>'{}'".format(editfieldsDict['creationDateField'], lasteditdatestring), 'token': servicetoken,
              'outFields': outfields, 'f': 'json'}
    print(''"{}>'{}'".format(editfieldsDict['creationDateField'], lasteditdatestring))
    print('Outfields = {}'.format(outfields))
    exturl = '{}/query'.format(urlLyr)
    result = requests.get(exturl, params=params)
    resultjs = result.json()

    code = result.status_code
    if code != 200:
        errlogname = generrlogname()
        emsg = result.reason
        print('Edit tracking request failed: {}'.format(emsg))
        writeerror(errlogname, emsg)
        return

    features = resultjs['features']

    # Send an email for each add or update
    if len(features) > 0:
        mapViewerLevel = cfg['service']['viewerMapLevel']
        mapurl = '{}?url={}&level={}&center='.format(viewerurl, urlLyr, mapViewerLevel)
        writemessages(features, cfg, mapurl, fieldsDict, lasteditdatestring)
    else:
        print('There are no additions to the service')

    # Write the edit tracking object to disk in the tools folder -
    lastDict = {"lasteditdate": [{"id": cfg['service']['fsLayerNum'], "lasteditdate": maxeditdate,
                                  "lasteditstring": maxeditdatestring}]}
    writecachefile(lastDict, os.path.join(messagepath, lasteditfilename))
    printelapsedtime(starttime, gettime())

    return


def writemessages(feats, cfg, msgurl, fDict, since):
    # remove the fractional seconds for display
    since = '{} {} UTC'.format(since[:-10], since[-2:])

    # send 1 email with all additions or 1 email per addition?
    if cfg['email']['onemailflag'] == 1:    # One email for all changes
        mailflag = True
        firstpass = True
    else:
        mailflag = False
        firstpass = False


    for i in feats:

        if firstpass and mailflag:
            # Get a new message
            msg = returnmessage(cfg)
            msg = '{}\nFeature(s) added since {}:\n'.format(msg, since)
            firstpass = False
        elif not mailflag:
            # Get a new message
            msg = returnmessage(cfg)
            msg = '{}\nFeature added since {}:\n'.format(msg, since)

        atts = i['attributes']
        geomflag = False
        if 'geometry' in i.keys():
            geom = i['geometry']
            newx = geom['x']
            newy = geom['y']
            geomflag = True

        # write features/rows
        for f in atts.keys():
            if f.upper() not in ['OBJECTID', 'GLOBALID']:
                falias = fDict[f.upper()]['alias']
                val = ''
                if fDict[f.upper()]['type'] == 'esriFieldTypeDate':
                    if atts[f]:
                        try:
                            val = datetime.datetime.utcfromtimestamp(atts[f] / 1000.).strftime(
                                '%Y-%m-%d %I:%M:%S %p UTC')
                        except:
                            val = ' '
                else:
                    val = atts[f]
                msg = msg + '\t{}: {}\n'.format(falias, val)
        # If it has geometry - write the URL
        if geomflag:
            msg = msg + '\tIncident Location: {}{},{}\n'.format(msgurl, newx, newy)

        msg = msg + '\n'
        if not mailflag:
            sendMail(cfg['email']['server'], msg, cfg['email']['recipients'], cfg['email']['from'],
                     cfg['email']['subject'])

    if mailflag:
        sendMail(cfg['email']['server'], msg, cfg['email']['recipients'], cfg['email']['from'],
                 cfg['email']['subject'])
    return msg


def getMaxDate(url, statfield, outfield, token):
    stats = [{"onStatisticField": statfield, "statisticType": "max", "outStatisticFieldName": outfield}]
    pstr = 'f=pjson&where=1=1&outFields={}&outStatistics={}&token={}'.format('*', stats, token)
    theurl = '{}/query?{}'.format(url, pstr)
    result = requests.get(theurl)
    resultjs = result.json()
    if 'error' in resultjs.keys():
        errlogname = generrlogname()
        emsg = '{}\n{}\n\n(in getToken)'.format(resultjs['error']['message'], resultjs['error']['details'][0])
        writeerror(errlogname, emsg)
        sys.exit('1 {}'.format(resultjs['error']['message']))
    lasteditdate = resultjs['features'][0]['attributes'][outfield]
    return lasteditdate


def getToken(baseURL, username, password, referrer):

    if baseURL.lower().find('www.arcgis.com')>0:
        url = baseURL + '/generateToken'
    else:
        url = baseURL + '/rest/generateToken'
              
    postData = {
        'username': username,
        'password': password,
        'client': 'referer',
        'referer': referrer,
        'expiration': 60,
        'f': 'pjson'}
    r = requests.post(url, verify=True, data=postData)
    rjson = r.json()
    if 'token' in rjson:
        return rjson['token']
    elif 'error' in rjson:
        errlogname = generrlogname()
        emsg = '{}\n{}\n\n(in getToken)'.format(rjson['error']['message'], rjson['error']['details'][0])
        writeerror(errlogname, emsg)
        sys.exit('1 {}'.format(rjson['error']['message']))


def sendMail(srvrInfo, messagetext, eMailTo, eMailFrom, eMailSubject):
    servername = srvrInfo[0].lower()
    try:

        if eMailTo[0].index("@") > 0:

            msg = EmailMessage()
            server = smtplib.SMTP(servername, srvrInfo[1])
            server.ehlo()
            server.starttls()
            if servername == "smtp.gmail.com":
                server.login(srvrInfo[2], srvrInfo[3])

            msg['From'] = eMailFrom
            msg['To'] = eMailTo
            msg['Subject'] = eMailSubject

            msg.set_content(messagetext)

            # send it
            server.sendmail(eMailFrom, eMailTo, msg.as_string())
            server.close()
    except:
        errlogname = generrlogname()
        emsg = 'An email error occurred (in sendMail) while attempting to connect to: {} \n' \
               'Please ensure your Mail Server Host and port are set correctly in your Init.json file'.format(servername)
        writeerror(errlogname, emsg)
        pass


def generrlogname ():
    errlogname = os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__))),
                              'Error{}.txt'.format(datetime.datetime.strftime(datetime.datetime.now(),
                                                                              '%Y%m%d_%H_%M_%S')))
    return errlogname


def returnmessage(thecfg):
    msg = thecfg['email']['text']
    msg = msg + '\t{}{}\n'.format(thecfg['service']['fsURL'], thecfg['service']['fsLayerNum'])
    msg = msg + '\n'
    return msg


def writecachefile(data, filename):
    with open(filename, 'w') as out:
        json.dump(data, out)


def readcachefile(filename):
    with open(filename, 'r') as out:
        lines = json.load(out)
    return lines


def printelapsedtime(stime, etime):
    print('\n\nElapsed time: {}'.format(etime - stime))


def writeerror(errfile, msg):
    with open(errfile, 'w') as outfile:
        outfile.write(msg)
    return


def gettime():
    return datetime.datetime.now()


if __name__ == '__main__':

    configfilename = 'initDetectEdits.json'

    main(configfilename)
    print('\nProcess Complete')
