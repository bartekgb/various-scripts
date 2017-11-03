#!/usr/bin/python

from platform import node
from subprocess import Popen,PIPE
from json import loads,dumps
from time import time
from os import listdir

#cfg
CPCMD='/usr/local/cpanel/cpanel -V'
#UAPI
UAPICMD='uapi --output=json --user={0} StatsBar get_stats display={1} warnings=0 warninglevel=high warnout=0 infinityimg=%2Fhome%2Fexample%2Finfinity.pnginfinitylang="infinity" rowcounter=even'
UAPIVALUES=['addondomains emailaccounts ftpaccounts sqldatabases diskusage mysqldiskusage bandwidthusage']
#API2
LVEUSERVALUES=['aCPU aVMem mVMem']
LVEINFOCMD='lveinfo --period 1h --show-columns {0} -d -l 0 -j'

def getLveList():
  '''
  Returns a list of existing lves
  '''
  return listdir('/var/cpanel/users')

def getUapi(lveName,uapiCmd,uapi):
  '''
  Returns a dict of UAPIVALUES read via UAPI for a given lve
  '''
  cmd=uapiCmd.format(lveName,'|'.join(uapi[0].split()))
  res=Popen(cmd.split(),stdout=PIPE,stderr=PIPE)
  (out, err)=res.communicate()
  if (res.returncode == 0):
    dic=dict([[data['id'],data['_count']] for data in loads(out)['result']['data'] for val in UAPIVALUES[0].split() if data['name']==val])
    #cast counters from unicode to int or float
    for key in dic.keys():
      try:
        dic[key]=int(dic[key])
      except ValueError:
        dic[key]=float(dic[key])
    return dic
  else:
    return {}

def getLveValues(LVEINFOCMD,LVEUSERVALUES):
  '''
  Returns a dict of values read via lve tools for all accounts
  '''
  cmd=LVEINFOCMD.format('id '+LVEUSERVALUES[0])
  lve=Popen(cmd.split(),stderr=PIPE,stdout=PIPE)
  (out, err)=lve.communicate()
  dic={}
  if (lve.returncode == 0):
    #turn list of dicts into dict with lists as values
    for elem in loads(out)['data']:
      id=elem.pop('ID')
      res=[]
      [res.append({key:elem[key]}) for key in elem.keys()]
      dic.update({id:res})
  return dic

def cpanelReleaseOk(cpCmd):
  '''
  Checks if cPanel version is sufficient;
  Returns: 1 -> yes, 0 -> no
  '''
  #Read cPanel release
  cmd=Popen(cpCmd.split(),stderr=PIPE,stdout=PIPE)
  (out,err)=cmd.communicate()
  if (cmd.returncode == 0):
    if (int(out.split('.')[0])>=56):
      return 1
    else:
      return 0

if cpanelReleaseOk(CPCMD):

  metrics={}
  #Get list of LVEs
  lveList=getLveList()

  #Get data available via API
  for name in lveList:
    metrics.update({name:getUapi(name,UAPICMD,UAPIVALUES)})

  #Get data available via lve tools directly
  lveMetrics=getLveValues(LVEINFOCMD,LVEUSERVALUES)

  #Glue API and lve tools data into single hash
  for key in metrics.keys():
    try:
      for elemCnt in range(len(lveMetrics[key])):
        for elem in lveMetrics[key]:
          if (len(elem) !=0):
            pop=elem.popitem()
            metrics[key].update({pop[0]:pop[1]})
    except KeyError:
      for elem in LVEUSERVALUES[0].split():
        metrics[key].update({elem:0})

  print(dumps(metrics,indent=4))
else:
  print 'Error: Insufficient cPanel release'
