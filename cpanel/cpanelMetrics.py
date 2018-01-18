#!/usr/bin/env python2.6

from socket import socket,error
from time import time,sleep
from subprocess import Popen,PIPE
from platform import node
import json
import os

class CpanelMetrics:

  CARBONRETRY = 4
  CARBON_HOST = '<host>'
  CARBON_PORT = <port>
  GRAPHITEPREFIX = 'path'

  def __init__(self):
    '''
    self.uapiCmd - command to get values trough UAPI
    self.uapiValues - cpanel properties to get
    '''
    self.uapiValues = 'addondomains emailaccounts ftpaccounts sqldatabases diskusage mysqldiskusage bandwidthusage'
    self.uapiCmd = 'uapi --output=json --user={0} StatsBar get_stats display={1} warnings=0 warninglevel=high warnout=0 infinityimg=%2Fhome%2Fexample%2Finfinity.pnginfinitylang="infinity" rowcounter=even'
    self.cpanelVersionCmd = '/usr/local/cpanel/cpanel -V'
    self.minCpanelVersion = 56
    self.cpanelUserDir = '/var/cpanel/users'
    self.cpanelList = None
    self.metrics = {}
    self.msg = ''

  def getCpanelVersion(self):

    ver = Popen(self.cpanelVersionCmd.split(),stdout=PIPE,stderr=PIPE)
    (out, err) = ver.communicate()
    if (ver.returncode == 0) and (int(out.split('.')[0]) >= self.minCpanelVersion):
      return 1
    else:
      return 0

  def enumerateHostCpanels(self):
    '''
    Returns a set of cpanel names on current host
    '''

    if self.cpanelList is None:
      self.cpanelList = set(os.listdir(self.cpanelUserDir))

  def getUapiValues(self):
    '''
    Returns a dict of { '<cpanelName>': { '<prop>': <val>, ['<prop>': <val>,], ...}, ... }
    '''

    if self.metrics == {}:

      self.enumerateHostCpanels()

      for cpanel in self.cpanelList:
        cmd = self.uapiCmd.format(cpanel,'|'.join(self.uapiValues.split()))
        uapi = Popen(cmd.split(),stdout=PIPE,stderr=PIPE)
        (out, err) = uapi.communicate()
        try:
          if (uapi.returncode == 0):
            dic=dict([[res['id'],res['_count']] for res in json.loads(out)['result']['data'] for val in self.uapiValues.split() if res['name']==val])
            self.metrics.update({cpanel:dic})
            for key in self.metrics[cpanel].keys():
              try:
                self.metrics[cpanel][key]=int(self.metrics[cpanel][key])
              except ValueError:
                self.metrics[cpanel][key]=float(self.metrics[cpanel][key])
        except:
          continue

  def formatGraphiteMsg(self):
    '''
    Returns a string of graphite's plaintext protocol msg
    '''

    if self.metrics == {}:
      self.getUapiValues()

    tstamp=int(time())
    self.msg = ''

    for cpanel in self.metrics.keys():
      for key in self.metrics[cpanel].keys():
        self.msg+='{0} {1} {2}\n'.format(self.GRAPHITEPREFIX+'.'+cpanel+'.'+key,self.metrics[cpanel][key],tstamp)

  def feedGraphite(self):
    '''
    Send msg to graphite by plaintext protocol
    '''

    if self.msg == '':
      self.formatGraphiteMsg()

    for retr in range(0,self.CARBONRETRY):
      try:
        s=socket()
        s.connect((self.CARBON_HOST,self.CARBON_PORT))
        s.sendall(self.msg)
        s.close()
        break
      except error as e:
        if (retr != (self.CARBONRETRY-1)):
          sleep(1)
        else:
          raise(e)

if __name__ == '__main__':
  metrics=CpanelMetrics()
  metrics.feedGraphite()
