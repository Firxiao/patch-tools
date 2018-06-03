#!/usr/bin/python
# -*- coding: UTf-8 -*-
import sys,os,re,time
import salt.client, salt.runner, salt.version, salt.config, salt.utils.event
import fnmatch
import yaml
from progress.bar import Bar
from common import check_ng
from tabulate import tabulate
from termcolor import colored
from operator import itemgetter, attrgetter
location = os.getcwd() # get present working directory location here
confdir = "/reboot.d/"

nodegroup = sys.argv[1]
confirm_reboot = sys.argv[2]
check_timeout = 10
reboot_timeout = 120
reboot_time = time.strftime("%Y%m%d%H%m", time.localtime())

# salt client
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

# read configration from yaml
ymlfiles = [] #list to store all csv files found at location
reboot_rules={}
for file in os.listdir(location+confdir):
    try:
        if file.endswith(".yml"):
            print("load:%s"%file)
            ymlfiles.append(str(file))
            with open(location+confdir+file,'r') as conf:
                reboot_rules.update(yaml.load(conf))
    except Exception as e:
        raise e
        print("No yml file found here!")
#print(reboot_rules)


def reboot_minion(minion,os_type):
    '''
    reboot minion
    return bool
    '''
    i = 0
    _pass = False
    _need_reboot = True
    if 'Linux' in os_type:
        need_reboot = (local.cmd(minion,'cmd.script',['salt://scripts/linux_needs_restarting.sh'])[minion]['stdout'] == 'True')
        if need_reboot:
          local.cmd(minion,'system.reboot')
          while True:
              ret = sevent.get_event(full=True)
              if i == reboot_timeout:
                 break
              if ret is None:
                i += 1
               # print(i)
                continue
              if fnmatch.fnmatch(ret['tag'], 'salt/minion/'+ minion + '/start'):
                 #print("%s: reboot:"%(ctime(),minion) + colored("succeeded",'green'))
                 _pass = True
                 break
        else:
           _need_reboot = False
    elif 'Windows' in os_type:
       need_reboot = local.cmd(minion,'win_wua.get_needs_reboot')[minion]
       if need_reboot:
           local.cmd(minion,'system.reboot',[0])
           while True:
            ret = sevent.get_event(full=True)
            if i == reboot_timeout:
               #print("%s: reboot:"%(ctime(),minion) + colored("failed",'red'))
               break
            if ret is None:
                i += 1
                continue
            if fnmatch.fnmatch(ret['tag'], 'salt/minion/'+ minion + '/start'):
               #print("%s: reboot:"%(ctime(),minion) + colored("successed",'green'))
               _pass = True
               break
       else:
           _need_reboot = False
    else:
       print('Only support Linux and Windows')
    return _pass,_need_reboot

def ctime():
    return(time.strftime("%Y-%m-%d [%H:%M:%S]", time.localtime()))

def check_ports(minion,local_ip,ports):
    ports_result=[]
    _pass = True
    for port in ports:
        i = 0
        while True:
          port_status = local.cmd(minion,'network.connect',[local_ip,port])
          time.sleep(1)
          i += 1
          #print(type(port_status[minion]['result']))
          if i == check_timeout:
          #    print(minion,port,port_status)
              ports_result.append([minion,port,port_status[minion]['result']])
              _pass = False
              break
          elif port_status[minion]['result']:
          #    print(minion,port,port_status)
              ports_result.append([minion,port,port_status[minion]['result']])
              break
          else:
              continue
    return _pass



def check_services(minion,services):
    services_result=[]
    _pass = True
    for service in services:
        i = 0
        while True:
          i += 1
          service_status = local.cmd(minion,'service.status',[service])
          if i == check_timeout:
              #print(minion,service,service_status)
              _pass = False
              services_result.append([minion,service,service_status[minion]])
              break
          elif service_status[minion]:
              #print(minion,service,service_status)
              services_result.append([minion,service,service_status[minion]])
              break
          else:
              continue
    return _pass

def reboot_plan(minions,reboot_rules):
    all_minions = minions.keys()
    minions_without_rule = minions.keys()
    reboot_plan = {}
    for service in reboot_rules:
        minions_with_rule = []
        keyword = reboot_rules[service]['keyword']
        for minion in all_minions:
    #        print(all_minions)
            if keyword in str(minion):
                minions_with_rule.append(minion)
                minions_without_rule.remove(minion)
        reboot_plan.update({service:minions_with_rule})
    reboot_plan.update({'noplan':minions_without_rule})
    return reboot_plan

print colored("=================================nodegroup: %s================================================================="%(nodegroup),'blue')
print colored("*********************************reboot job start*************************************************************",'blue')
print colored("----------------------------Checking Minion Status---------------------------------------------------------",'green')
good_minions,bad_minions= check_ng(nodegroup)
print colored("--------------------------------------------------------------------------------------------------------",'green')
reboot_plan = reboot_plan(good_minions,reboot_rules)
#print(reboot_plan)
for plan in reboot_plan:
    if bool(reboot_plan[plan]):
        if plan == "noplan":
            print("===========================%s======================================"%plan)
            print("--below minions will reboot without checking services and ports--")
            print("**************************************************************")
            print('\n'.join(reboot_plan[plan]))
            print("==================================================================")
        else:
            ports = reboot_rules[plan]['ports']
            services = reboot_rules[plan]['services']
            print("================%s================================================="%plan)
            print("******************************************************************")
            print("service: %s  ports: %s"%(services,ports))
            print("******************************************************************")
            print('\n'.join(reboot_plan[plan]))
            print("==================================================================")
            #print(tabulate(reboot_plan[plan], headers="keys",tablefmt="grid"))
            #print(tabulate(reboot_plan[plan], headers=plan,tablefmt="plain"))

if confirm_reboot == 'yes':
    rebooted_minion = []
    for service in reboot_plan:
        if bool(reboot_plan[service]):
            print("-------------%s-------------"%service)
            if service == 'noplan':
                for minion in reboot_plan[service]:
                    print("%s %s: checking reboot status ..."%(ctime(),minion))
                    reboot_pass,need_reboot = reboot_minion(minion,good_minions[minion]["kernel"])
                    if need_reboot:
                        if reboot_pass:
                            print("%s %s: "%(ctime(),minion) + colored("rebooot successfully",'green'))
                            local.cmd(minion,'grains.append',['reboot_time',reboot_time])
                            rebooted_minion.append(minion)
                        else:
                            print("%s %s: "%(ctime(),minion) + colored("reboot failed",'red'))
                            break
                    else:
                        print("%s %s: "%(ctime(),minion) + colored("no need to reboot",'green'))
                        rebooted_minion.append(minion)
    
            else:
                for minion in reboot_plan[service]:
                    #print(reboot_plan[service])
                    #print(reboot_rules)
                    ports = reboot_rules[service]['ports']
                    services = reboot_rules[service]['services']
                    ports_status = check_ports(minion,good_minions[minion]['ip'],ports)
                    if not ports_status:
                        print("%s %s: checking ports status: "%(ctime(),minion) + colored("failed",'red'))
                        break
                    else:
                        print("%s %s: checking ports status: "%(ctime(),minion) + colored("pass",'green'))
                    services_status=check_services(minion,services)
                    if not services_status:
                        print("%s %s: checking services status: "%(ctime(),minion) + colored("failed",'red'))
                        break
                    else:
                        print("%s %s: checking services status: "%(ctime(),minion) + colored("pass",'green'))
                    print("%s %s: checking reboot status..."%(ctime(),minion))
                    reboot_pass,need_reboot = reboot_minion(minion,good_minions[minion]["kernel"])
                    if need_reboot:
                        if reboot_pass:
                            print("%s %s: "%(ctime(),minion) + colored("reboot successfully",'green'))
                            local.cmd(minion,'grains.append',['reboot_time',reboot_time])
                            rebooted_minion.append(minion)
                            services = reboot_rules[service]['services']
                            ports_status = check_ports(minion,good_minions[minion]['ip'],ports)
                            if not ports_status:
                                print("%s %s: checking ports status: "%(ctime(),minion) + colored("failed",'red'))
                                break
                            else:
                                print("%s %s: checking ports status: "%(ctime(),minion) + colored("pass",'green'))
                            services_status=check_services(minion,services)
                            if not services_status:
                                print("%s %s: checking services status: "%(ctime(),minion) + colored("failed",'red'))
                                break
                            else:
                                print("%s %s: checking services status: "%(ctime(),minion) + colored("pass",'green'))
                        else:
                            print("%s %s:"%(ctime(),minion) + colored("reboot failed",'red'))
                            break
                    else:
                        print("%s %s: "%(ctime(),minion) + colored("no need to reboot",'green'))
                        rebooted_minion.append(minion)
            print("-----------------------------")
    
    print("--------------------------------------------------------------------------------------------------------")
    
    report = []
    for minion in good_minions:
        if minion in rebooted_minion:
            report.append((minion,good_minions[minion]['ip'],"succeeded"))
        else:
            report.append((minion,good_minions[minion]['ip'],"failed"))
    
    print colored("-------------------------Reports---------------------------------------------------------",'green')
    print(tabulate(sorted(report, key=itemgetter(2)), headers=["minionid","ip","reboot status"],tablefmt="grid"))
    print colored("-----------------------------------------------------------------------------------------",'green')
else:
    print colored("do not reboot, if you want to reboot, please run with reboot yes",'blue')
