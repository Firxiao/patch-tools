#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, time
import salt.client, salt.runner, salt.version, salt.config, salt.utils.event
import fnmatch
from progress.bar import Bar
from common import check_ng
from tabulate import tabulate
from termcolor import colored
from operator import itemgetter, attrgetter


nodegroup = sys.argv[1]

opts = salt.config.master_config('/etc/salt/master')
opts['quiet'] = True

local = salt.client.LocalClient()
runner = salt.runner.RunnerClient(opts)
salt_version = salt.version.salt_information().next()[1]

sevent = salt.utils.event.get_event(
        'master',
        sock_dir=opts['sock_dir'],
        transport=opts['transport'],
        opts=opts)
print colored("=================================nodegroup: %s========================================================="%(nodegroup),'cyan')
print colored("*********************************patching job start*************************************************************",'blue')
#get minion ip and status
print colored("-------------------------Checking Minion Status---------------------------------------------------------",'green')
good_minions,bad_minions = check_ng(nodegroup)
print colored("--------------------------------------------------------------------------------------------------------",'green')
if 'linux' in nodegroup:
    #Changed in version 2017.7.0: Renamed from expr_form to tgt_type
    if salt_version < "2017.7.0":
      job_id = local.cmd_async(nodegroup,'pkg.upgrade',expr_form='nodegroup')
    else:
      job_id = local.cmd_async(nodegroup,'pkg.upgrade',tgt_type='nodegroup')
elif 'win' in nodegroup:
    if salt_version < "2017.7.0":
      job_id = local.cmd_async(nodegroup,'win_wua.list_updates',kwarg={'install':'true'},expr_form='nodegroup')
    else:
      job_id = local.cmd_async(nodegroup,'win_wua.list_updates',kwarg={'install':'true'},tgt_type='nodegroup')

#print(job_id)

def print_report(job_id):
  summary = runner.cmd('jobs.lookup_jid',arg=[job_id])
  report = []
  for minion in summary:
#      print(len(summary[minion]))
      if len(summary[minion]) > 300:
        if '-' in minion:
            s_minion = minion.split('-')[-2] + '-' + minion.split('-')[-1]
        elif '.' in minion:
            s_minion = minion.split('.')[0]
        else:
            s_minion = minion
      else:
          s_minion = minion
      if 'linux' in nodegroup:
        if not bool(summary[minion]):
          report.append((s_minion,good_minions[minion]['ip'],'Nothing to install'))
        else:
          patches = []
          for patch in summary[minion]:
              patches.append(patch)
          report.append((s_minion,good_minions[minion]['ip'],'\n'.join(patches)))
      elif 'win' in nodegroup:
        if 'Updates' in summary[minion]:
          patches = []
          for patch in summary[minion]['Updates'].keys():
            patches.append(summary[minion]['Updates'][patch]['Title'])
          report.append((s_minion,good_minions[minion]['ip'],'\n'.join(patches)))
        else:
          report.append((s_minion,good_minions[minion]['ip'],'Nothing to install'))
  #print(tabulate(report,headers=['minion id','info'],tablefmt="fancy_grid"))
  print colored("======================================patching summary===============================================",'green')
  print(tabulate(sorted(report, key=itemgetter(2)),headers=['minion id','ip','update info'],tablefmt="grid"))
  print colored("=====================================================================================================",'green')
#time.sleep(10)
#print_report(job_id)
print colored("Please waiting for processing...",'yellow')
i = 0
bar = Bar('Processing', max=len(good_minions))
while (i <= len(good_minions)):
    ret = sevent.get_event(full=True)
    if ret is None:
        continue
    #print(ret)
    for minion in good_minions:
        if fnmatch.fnmatch(ret['tag'], 'salt/job/'+job_id+'/ret/'+minion):
          bar.next()
          print colored("[%d/%d]%s"%(i+1,len(good_minions),minion),'yellow')
          i += 1

    if i == len(good_minions):
        bar.finish()
        print_report(job_id)
        break

print colored("*********************************patching job end**************************************************************",'blue')
