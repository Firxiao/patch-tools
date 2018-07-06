# Patching tools

This is a tool to patching linux or windows system via salt python client.

## Requestments

- saltstack
- python

## Feature

- friendly report of patching and summary.
- reboot minion with checking services and ports

## Before running

you need specified the [Node Group](https://docs.saltstack.com/en/latest/topics/targeting/nodegroups.html) in salt master.

and nodegroup's name must cotain win or linux

Example:

```
win-noprod
linux-prod
```

## How to use

```bash
git clone git@github.com:Firxiao/patching-tools.git
cd patching-tools
pip install -r requirements.txt
python get_summary.py nodegroup
```

### reboot policy

Please refer file in *reboot.d/demo/* , then copy it to *reboot.d/*

Example:

```yaml
linux:
    keyword: u
    ports:
      - 22
    services:
      - sshd
```
