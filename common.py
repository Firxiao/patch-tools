#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import salt.client
import salt.version
from tabulate import tabulate
from termcolor import colored
from operator import itemgetter, attrgetter

## init salt client
local = salt.client.LocalClient()
salt_version = salt.version.salt_information().next()[1]

def check_ng(nodegroup):
    # get inventory
    #Changed in version 2017.7.0: Renamed from expr_form to tgt_type
    if salt_version < "2017.7.0":
      inventory = local.cmd(nodegroup,'grains.item',['ipv4','kernel'],expr_form= "nodegroup")
    else:
      inventory = local.cmd(nodegroup,'grains.item',['ipv4','kernel'],tgt_type = "nodegroup")
    #print(inventory)
    #init empty list
    good_minions = {}
    bad_minions = []
    for minion in inventory:
      if inventory[minion] == False:
        bad_minions.append((minion,"False"))
      else:
        ip_list = inventory[minion]["ipv4"]
        kernel = inventory[minion]["kernel"]
        try:
            ip_list.remove("127.0.0.1")
        except:
           pass
        good_minions.update({minion:{'ip': ip_list[0],'kernel':kernel}})
    if len(good_minions) == 0:
       sys.exit(1)
    print("There are %d salt minions in toltal. %d good minions,"%(len(inventory),len(good_minions))),colored("%d bad minions"%len(bad_minions),'red')
    if len(bad_minions) > 0:
          print colored(tabulate(bad_minions,headers=['minion id','status'],tablefmt="grid"),'red')
    #print(tabulate(inventory_list,headers=['minion id','ip','status'],tablefmt="fancy_grid"))
    return (good_minions,bad_minions)

