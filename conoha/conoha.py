#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import datetime
import urllib.parse
import click
import requests
import json
import toml

class Config():
    CONFIG_DIR = "%s/.conoha" % os.environ['HOME']
    CONFIG_FILE = "config"

    def __init__(self):
        if os.path.exists("%s/%s" % (Config.CONFIG_DIR, Config.CONFIG_FILE)):
            config = toml.load(open("%s/%s" % (Config.CONFIG_DIR, Config.CONFIG_FILE))) 
            if datetime.datetime.strptime(config["default"]["expires"], '%Y-%m-%dT%H:%M:%SZ') <= datetime.datetime.now():
                self.init_config(config["default"]["username"], config["default"]["password"], config["default"]["tenant_id"])
            
        else:
            self.init_config()

        config = toml.load(open("%s/%s" % (Config.CONFIG_DIR, Config.CONFIG_FILE)))
        self.tenant_id = config["default"]["tenant_id"]
        self.access_token = config["default"]["access_token"]
        self.region = config["default"]["region"]
    
    def init_config(self, username=False, password=False, tenant_id=False):

        if (not username or not password or not tenant_id):
            username = input("username : ")
            password = input("password : ")
            tenant_id = input("tenant_id : ")
    
        payload = {
            "auth": {
                "passwordCredentials": {
                    "username": username,
                    "password": password
                },
                "tenantId": tenant_id
            }
        } 

        regions = ["tyo1", "tyo2"]
        authenticated = False

        for region in regions:
            r = requests.post("https://identity.%s.conoha.io/v2.0/tokens"%region, data=json.dumps(payload))

            if r.status_code != 200:
                continue

            rJson = json.loads(r.text)
            d = {
                "default": {
                    "username": username,
                    "password": password,
                    "tenant_id": tenant_id,
                    "region": region,
                    "access_token": rJson["access"]["token"]["id"],
                    "issued_at": rJson["access"]["token"]["issued_at"],
                    "expires": rJson["access"]["token"]["expires"]
                }
            }

            os.makedirs(Config.CONFIG_DIR, exist_ok=True)
            with open("%s/%s" % (Config.CONFIG_DIR, Config.CONFIG_FILE), 'w') as f:
                toml.dump(d, f)
        
            authenticated = True
            click.echo("Authentication success.")

        if not authenticated:
            click.echo("Authentication failed." % r.status_code)
            exit()

@click.group()
def cmd():
    pass

#########################################
# ACCOUT API
#########################################
@cmd.group()
def account():
    pass

@account.group()
def billing():
    pass

@billing.command()
@click.argument("item_id", default=False)
def order_items(item_id):
    headers = { "X-Auth-Token": config.access_token }

    if item_id:
        url = "https://account.%s.conoha.io/v1/%s/order-items/%s" % (config.region, config.tenant_id, item_id)
    else:
        url = "https://account.%s.conoha.io/v1/%s/order-items" % (config.region, config.tenant_id)

    r = requests.get(url, headers=headers)
    click.echo(r.text)

@billing.command()
def payment_history():
    headers = { "X-Auth-Token": config.access_token }

    url = "https://account.%s.conoha.io/v1/%s/payment-history" % (config.region, config.tenant_id)

    r = requests.get(url, headers=headers)
    click.echo(r.text)

@billing.command()
def payment_summary():
    headers = { "X-Auth-Token": config.access_token }

    url = "https://account.%s.conoha.io/v1/%s/payment-summary" % (config.region, config.tenant_id)

    r = requests.get(url, headers=headers)
    click.echo(r.text)

@billing.command()
@click.argument("invoice_id", default=False)
def invoices(invoice_id):
    headers = { "X-Auth-Token": config.access_token }

    if invoice_id:
        url = "https://account.%s.conoha.io/v1/%s/billing-invoices/%s" % (config.region, config.tenant_id, invoice_id)
    else:
        url = "https://account.%s.conoha.io/v1/%s/billing-invoices" % (config.region, config.tenant_id)

    r = requests.get(url, headers=headers)
    click.echo(r.text)

@billing.command()
@click.argument("notification_code", default=False)
def notifications(notification_code):
    headers = { "X-Auth-Token": config.access_token }

    if notification_code:
        url = "https://account.%s.conoha.io/v1/%s/notifications/%s" % (config.region, config.tenant_id, notification_code)
    else:
        url = "https://account.%s.conoha.io/v1/%s/notifications" % (config.region, config.tenant_id)

    r = requests.get(url, headers=headers)
    click.echo(r.text)

#########################################
# COMPUTE API
#########################################
@cmd.group()
def compute():
    pass

@compute.group()
def vm():
    pass

@vm.command()
@click.option('--outline', is_flag=True)
@click.option('--text', is_flag=True)
@click.option('-i', '--imageid', 'imageid', type=str, help='ImageID')
@click.option('-f', '--flavorid', 'flavorid', type=str, help='FlavorID')
@click.option('-n', '--name', 'name', type=str, help='VM Name')
@click.option('-s', '--status', 'status', type=str, help='VM Status')
def list(outline, text, imageid="", flavorid="", name="", status=""):
    headers = { "X-Auth-Token": config.access_token }

    if outline and not text:
        url = "https://compute.%s.conoha.io/v2/%s/servers" % (config.region, config.tenant_id)
    else:
        url = "https://compute.%s.conoha.io/v2/%s/servers/detail" % (config.region, config.tenant_id)

    query = {}
    if imageid: query["image"] = imageid
    if flavorid: query["flavor"] = flavorid
    if name: query["name"] = name
    if status: query["status"] = status

    r = requests.get("%s?%s"%(url, urllib.parse.urlencode(query)), headers=headers)

    if text:
        click.echo("STATUS\tVM_ID\tNAME\tINSTANCE_NAME_TAG");
        click.echo("-------------------------------------------------------------------------------");
        for server in json.loads(r.text)['servers']:
            click.echo("%s\t%s\t%s\t%s" % (server["status"], server["id"], server["name"].replace('-', '.'), server["metadata"]['instance_name_tag']))
    else:
        click.echo(r.text)

@vm.command()
@click.argument("vm_id")
def up(vm_id):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers/%s/action" % (config.region, config.tenant_id, vm_id)

    payload = {
        "os-start": "null"
    } 
    r = requests.post(url, headers=headers, data=json.dumps(payload))

    if r.status_code == 202:
        click.echo("[StatusCode: %s] Success." % r.status_code)
    else:
        click.echo("[StatusCode: %s] Failed." % r.status_code)

    click.echo(r.text)

@vm.command()
@click.argument("vm_id")
def reboot(vm_id):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers/%s/action" % (config.region, config.tenant_id, vm_id)

    payload = {
        "reboot": {
            "type": "SOFT"
        }
    } 
    r = requests.post(url, headers=headers, data=json.dumps(payload))

    if r.status_code == 202:
        click.echo("[StatusCode: %s] Success." % r.status_code)
    else:
        click.echo("[StatusCode: %s] Failed." % r.status_code)

    click.echo(r.text)

@vm.command()
@click.argument("vm_id")
@click.option('--force', is_flag=True)
def stop(vm_id, force):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers/%s/action" % (config.region, config.tenant_id, vm_id)

    payload = {
        "os-stop": "null"
    } 

    if force:
        payload["os-stop"] = {"force_shutdown": True}

    r = requests.post(url, headers=headers, data=json.dumps(payload))

    if r.status_code == 202:
        click.echo("[StatusCode: %s] Success." % r.status_code)
    else:
        click.echo("[StatusCode: %s] Failed." % r.status_code)

    click.echo(r.text)

@vm.command()
@click.argument("vm_id")
def remove(vm_id):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers/%s" % (config.region, config.tenant_id, vm_id)

    r = requests.delete(url, headers=headers)

    if r.status_code == 204:
        click.echo("[StatusCode: %s] Success." % r.status_code)
    else:
        click.echo("[StatusCode: %s] Failed." % r.status_code)

    click.echo(r.text)

@vm.command()
@click.argument("vm_id")
def ips(vm_id):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers/%s/ips" % (config.region, config.tenant_id, vm_id)

    r = requests.get(url, headers=headers)

    click.echo(r.text)

@vm.command()
@click.option('-i', '--imageid', 'imageid', type=str, help='IMAGE ID', required=True)
@click.option('-f', '--flavorid', 'flavorid', type=str, help='FLAVOR ID', required=True)
@click.option('--password', 'password', type=str, help='VM\'s root password', required=True)
@click.option('-n', '--name', 'name', type=str, help='VM name')
@click.option('-k', '--key', 'key', type=str, help='SSH key')
@click.option('-g', '--group-names', 'groupNames', type=str, help='Security group name')
def create(imageid, flavorid, password, name, key, groupNames):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers" % (config.region, config.tenant_id)

    payload = {
        "server": {
            "imageRef": imageid,
            "flavorRef": flavorid,
            "adminPass": password,
            "metadata": {}
        }
    } 

    if name: payload["server"]['metadata']['instance_name_tag'] = name
    if key: payload['server']['key_name'] = key

    if groupNames:
        payload['server']['security_groups'] = []
        for name in groupNames:
            payload['server']['security_groups'].append({ 'name': name, })

    r = requests.post(url, headers=headers, data=json.dumps(payload))

    click.echo(r.text)

@compute.group()
def flavor():
    pass

@flavor.command()
@click.option('--outline', is_flag=True)
@click.option('--text', is_flag=True)
@click.option('--mindisk', 'mindisk', type=str, help='最小 DISK サイズ(GB)でフィルター')
@click.option('--minram', 'minram', type=str, help='最小 RAM サイズ(MB)でフィルター')
def list(outline, text, mindisk=False, minram=False):
    headers = { "X-Auth-Token": config.access_token }

    if outline and not text:
        url = "https://compute.%s.conoha.io/v2/%s/flavors" % (config.region, config.tenant_id)
    else:
        url = "https://compute.%s.conoha.io/v2/%s/flavors/detail" % (config.region, config.tenant_id)

    query = {}
    if mindisk: query["minDisk"] = mindisk
    if minram: query["minRam"] = minram

    r = requests.get("%s?%s"%(url, urllib.parse.urlencode(query)), headers=headers)

    if text:
        click.echo("FLAVOR_ID\tFLOVOR_NAME");
        click.echo("-------------------------------------------------------------------------------");
        for flavor in json.loads(r.text)['flavors']:
            click.echo("%s\t%s" % (flavor["id"], flavor["name"]))
    else:
        click.echo(r.text)

@compute.group()
def image():
    pass

@image.command()
@click.option('--outline', is_flag=True)
@click.option('--text', is_flag=True)
@click.option('-n', '--name', 'name', type=str, help='Image Name')
@click.option('-s', '--status', 'status', type=str, help='Image Status')
@click.option('-t', '--type', 'imagetype', type=str, help='Image Type')
def list(outline, text, name, status, imagetype):
    headers = { "X-Auth-Token": config.access_token }

    if outline and not text:
        url = "https://compute.%s.conoha.io/v2/%s/images" % (config.region, config.tenant_id)
    else:
        url = "https://compute.%s.conoha.io/v2/%s/images/detail" % (config.region, config.tenant_id)

    query = {}
    if name: query["name"] = name
    if status: query["status"] = status
    if imagetype: query["type"] = imagetype

    r = requests.get("%s?%s"%(url, urllib.parse.urlencode(query)), headers=headers)

    if text:
        click.echo("STATUS\tIMAGE_ID\tIMAGE_NAME");
        click.echo("-------------------------------------------------------------------------------");
        for image in json.loads(r.text)['images']:
            click.echo("%s\t%s\t%s" % (image["status"], image["id"], image["name"]))
    else:
        click.echo(r.text)

@image.command()
@click.argument("vm_id")
@click.option('-n', '--name', 'image_name', type=str, help='CREATE IMAGE NAME', required=True)
def save(vm_id, image_name):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/servers/%s/action" % (config.region, config.tenant_id, vm_id)

    payload = {
        "createImage": {
            "name": image_name
        }
    } 

    r = requests.post(url, headers=headers, data=json.dumps(payload))

    if r.status_code == 202:
        click.echo("[StatusCode: %s] Success." % r.status_code)
    else:
        click.echo("[StatusCode: %s] Failed." % r.status_code)

    click.echo(r.text)

@compute.group()
def keypair():
    pass

@keypair.command()
@click.argument("keypair_name", default=False)
@click.option('--text', is_flag=True)
def list(keypair_name, text):
    headers = { "X-Auth-Token": config.access_token }

    if keypair_name and not text:
        url = "https://compute.%s.conoha.io/v2/%s/os-keypairs/%s" % (config.region, config.tenant_id, keypair_name)
    else:
        url = "https://compute.%s.conoha.io/v2/%s/os-keypairs" % (config.region, config.tenant_id)

    r = requests.get(url, headers=headers)

    if text:
        click.echo("KEYPAIR_NAME");
        click.echo("-------------------------");
        for keypair in json.loads(r.text)['keypairs']:
            click.echo("%s" % (keypair['keypair']['name']))
    else:
        click.echo(r.text)

@keypair.command()
@click.option('-n', '--name', 'keypair_name', type=str, help='KEYPAIR NAME', required=True)
@click.option('-k', '--key', 'public_key', type=str, help='PUBLIC KEY')
def add(keypair_name, public_key):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/os-keypairs" % (config.region, config.tenant_id)

    payload = {
        "keypair": {
            "name": keypair_name
        }
    } 

    if public_key: payload['keypair']['public_key'] = public_key

    r = requests.post(url, headers=headers, data=json.dumps(payload))

    click.echo(r.text)

@keypair.command()
@click.argument("keypair_name")
def remove(keypair_name):
    headers = { "X-Auth-Token": config.access_token }
    url = "https://compute.%s.conoha.io/v2/%s/os-keypairs/%s" % (config.region, config.tenant_id, keypair_name)

    r = requests.delete(url, headers=headers)

    if r.status_code == 202:
        click.echo("[StatusCode: %s] Success." % r.status_code)
    else:
        click.echo("[StatusCode: %s] Failed." % r.status_code)

    click.echo(r.text)

def main():
    global config
    config = Config()
    cmd()

if __name__ == '__main__':
    main()
