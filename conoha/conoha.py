#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import datetime
import urllib.parse
import click
import requests
import re
import json
import toml
import webbrowser

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

    def get_addr(self, addresses, interface_text="ext", tcp_version=4):
        data = [value for interface, value in addresses.items() if interface_text + '-' in interface]
        if data:
            for addr in data[0]:
                if addr['version'] == tcp_version:
                    return addr

        return {}

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
        click.echo("STATUS\tVM_ID\t\t\t\t\tGIP\t\tPIP\t\tINSTANCE_NAME_TAG")
        click.echo("-------------------------------------------------------------------------------------------------")
        servers = json.loads(r.text)['servers']
        servers = sorted(servers, key=lambda server: server["metadata"]['instance_name_tag'])
        for server in servers:
            grobal_ip = config.get_addr(server["addresses"], "ext")
            private_ip = config.get_addr(server["addresses"], "local")
            click.echo("%s\t%s\t%s\t%s\t%s" % (
                server["status"],
                server["id"],
                grobal_ip.get("addr") if grobal_ip.get("addr") else "\t",
                private_ip.get("addr") if private_ip.get("addr") else "\t",
                server["metadata"]['instance_name_tag']
            ))
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
@click.option('-g', '--group-names', 'groupNames', type=str, multiple=True, help='Security group name')
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
        securityGroups = []
        for groupName in groupNames:
            securityGroups.append({ 'name': groupName })
        payload['server']['security_groups'] = securityGroups

    r = requests.post(url, headers=headers, data=json.dumps(payload))

    click.echo(r.text)

@vm.command()
@click.argument("vm_id")
@click.option('--text', is_flag=True)
@click.option('--open', is_flag=True)
@click.option('-t', '--type', 'type', type=str, help='Console type(serial|vnc)')
def console(vm_id, text, open, type):
    headers = { "X-Auth-Token": config.access_token }

    url = "https://compute.%s.conoha.io/v2/%s/servers/detail" % (config.region, config.tenant_id)
    r = requests.get(url, headers=headers)

    # check vm_id
    if re.fullmatch(r'[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}', vm_id):
        servers = filter(lambda x: x['id'] == vm_id, json.loads(r.text)['servers'])
    else:
        servers = filter(lambda x: x['metadata']['instance_name_tag'] == vm_id, json.loads(r.text)['servers'])

    server = next(servers, None)

    if server == None:
        click.echo("Not found instance.")
        exit();

    vm_id = server['id'];

    url = "https://compute.%s.conoha.io/v2/%s/servers/%s/action" % (config.region, config.tenant_id, vm_id)

    payload = {
        "os-getWebConsole": {
            "type": "serial"
        }
    }

    if type == 'vnc':
        payload = {
            "os-getVNCConsole": {
                "type": "novnc"
            }
        }

    r = requests.post(url, headers=headers, data=json.dumps(payload))

    # open webbrowser
    if open:
        console = json.loads(r.text)['console']

        webbrowser.open(console["url"])
        exit()

    # echo text style
    if text:
        console = json.loads(r.text)['console']

        click.echo("CONSOLE_TYPE\tCONSOLE_URL")
        click.echo("-------------------------------------------------------------------------------")
        click.echo("%s\t\t%s" % (console["type"], console["url"]))
    else:
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
        click.echo("FLAVOR_ID\t\t\t\tFLOVOR_NAME\tRAM\tVCPUS\tDISK")
        click.echo("-------------------------------------------------------------------------------")
        flavors = json.loads(r.text)['flavors']
        flavors = sorted(flavors, key=lambda flavor: flavor["name"])
        for flavor in flavors:
            click.echo("{id}\t{name:<13s}\t{ram:>5d}\t{vcpus:>5d}\t{disk:>4d}".format(id=flavor["id"], name=flavor["name"], ram=flavor["ram"], vcpus=flavor["vcpus"], disk=flavor["disk"]))
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
@click.option('-t', '--tag', 'tag', type=str, help='Image Tag')
def list(outline, text, name, status, tag):
    headers = { "X-Auth-Token": config.access_token }

    if outline and not text:
        url = "https://compute.%s.conoha.io/v2/%s/images" % (config.region, config.tenant_id)
    else:
        url = "https://compute.%s.conoha.io/v2/%s/images/detail" % (config.region, config.tenant_id)

    query = {}
    if name: query["name"] = name
    if status: query["status"] = status
    if tag: query["tag"] = tag

    r = requests.get("%s?%s"%(url, urllib.parse.urlencode(query)), headers=headers)

    if text:
        click.echo("STATUS\tIMAGE_ID\t\t\t\tOS_TYPE\t\t\t\tIMAGE_NAME")
        click.echo("-------------------------------------------------------------------------------")
        images = json.loads(r.text)['images']
        images = sorted(images, key=lambda image: image["name"])
        for image in images:
            click.echo("{status}\t{id}\t{ostype:26s}\t{name}".format(status=image["status"], id=image["id"], ostype=image["metadata"]["os_type"], name=image["name"]))
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
        click.echo("KEYPAIR_NAME")
        click.echo("-------------------------")
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

#########################################
# NETWORK API
#########################################
@cmd.group()
def network():
    pass

@network.command()
@click.option('--text', is_flag=True)
def list(text):
    headers = { "X-Auth-Token": config.access_token }

    url = "https://networking.%s.conoha.io/v2.0/networks" % (config.region)

    r = requests.get(url, headers=headers)

    if text:
        networks = json.loads(r.text)['networks']

        click.echo("STATUS\tNETWORK_ID\t\t\t\tNETWORK_NAME")
        click.echo("-------------------------------------------------------------------------------")
        networks = sorted(networks, key=lambda network: network["name"])
        for network in networks:
            click.echo("%s\t%s\t%s" % (network['status'], network['id'], network['name']))
    else:
        click.echo(r.text)

@network.group()
def port():
    pass

@port.command()
@click.option('--text', is_flag=True)
def list(text):
    headers = { "X-Auth-Token": config.access_token }

    url = "https://networking.%s.conoha.io/v2.0/ports" % (config.region)

    r = requests.get(url, headers=headers)

    if text:
        ports = json.loads(r.text)['ports']
        click.echo("STATUS\tPORT_ID\t\t\t\t\tPORT_NAME\t\t\tMAC_ADDRESS")
        click.echo("-------------------------------------------------------------------------------------------------")
        ports = sorted(ports, key=lambda port: port["name"])
        for port in ports:
            click.echo("%s\t%s\t%s\t%s" % (port['status'], port['id'], port['name'], port['mac_address']))
    else:
        click.echo(r.text)

@network.group()
def subnet():
    pass

@subnet.command()
@click.option('--text', is_flag=True)
def list(text):
    headers = { "X-Auth-Token": config.access_token }

    url = "https://networking.%s.conoha.io/v2.0/subnets" % (config.region)

    r = requests.get(url, headers=headers)

    if text:
        subnets = json.loads(r.text)['subnets']
        click.echo("SUBNET_ID\t\t\t\tSUBNET_NAME\t\t\tCIDR")
        click.echo("-------------------------------------------------------------------------------------------------")
        subnets = sorted(subnets, key=lambda subnet: subnet["name"])
        for subnet in subnets:
            click.echo("%s\t%s\t%s" % (subnet['id'], subnet['name'], subnet['cidr']))
    else:
        click.echo(r.text)

@network.group()
def security_group():
    pass

@security_group.command()
@click.option('--text', is_flag=True)
def list(text):
    headers = { "X-Auth-Token": config.access_token }

    url = "https://networking.%s.conoha.io/v2.0/security-groups" % (config.region)

    r = requests.get(url, headers=headers)

    if text:
        security_groups = json.loads(r.text)['security_groups']

        click.echo("GROUP_NAME")
        click.echo("-------------------------")
        security_groups = sorted(security_groups, key=lambda security_group: security_group["description"])
        for security_group in security_groups:
            click.echo("%s" % (security_group['description']))
    else:
        click.echo(r.text)

def main():
    global config
    config = Config()
    cmd()

if __name__ == '__main__':
    main()
