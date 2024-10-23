import time
import paramiko
import smtplib
from email.mime.text import MIMEText
import paho.mqtt.client as mqtt
import json

# Configuration
MQTT_BROKER = "192.168.0.1"  # MQTT broker IP
MQTT_PORT = 1883
MQTT_USER = "user123"  # MQTT username
MQTT_PASS = "password123"  # MQTT password

EMAIL_SENDER = "example@example.com"  # Sender email
EMAIL_RECEIVER = "example@example.com"  # Receiver email
SMTP_SERVER = "192.168.0.2"  # Your SMTP server
SMTP_PORT = 25  # or 465 for SSL

# List of servers and services to monitor and restart
SERVERS = [
    {
        "ip": "192.168.0.3",
        "ssh_user": "user1",
        "ssh_pass": "pass1",
        "services": ["service1.service", "service2.service"],
        "device_name": "Device Monitor 1"
    },
    {
        "ip": "192.168.0.4",
        "ssh_user": "user2",
        "ssh_pass": "pass2",
        "services": ["service3.service"],
        "device_name": "Device Monitor 2"
    },
    {
        "ip": "192.168.0.5",
        "ssh_user": "user3",
        "ssh_pass": "pass3",
        "services": ["service4.service", "service5.service"],
        "device_name": "Device Monitor 3"
    },
    {
        "ip": "192.168.0.6",
        "ssh_user": "user4",
        "ssh_pass": "pass4",
        "services": ["service6.service", "service7.service"],
        "device_name": "Device Monitor 4"
    },
    {
        "ip": "192.168.0.7",
        "ssh_user": "user5",
        "ssh_pass": "pass5",
        "services": ["service8.service", "service9.service", "service10.service"],
        "device_name": "Device Monitor 5"
    },
    {
        "ip": "192.168.0.8",
        "ssh_user": "user6",
        "ssh_pass": "pass6",
        "services": ["service11.service"],
        "device_name": "Device Monitor 6"
    },
    {
        "ip": "192.168.0.9",
        "ssh_user": "user7",
        "ssh_pass": "pass7",
        "services": ["service12.service"],
        "device_name": "Device Monitor 7"
    },
]

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    print("Connected to MQTT Broker")
except Exception as e:
    print(f"Failed to connect to MQTT Broker: {e}")

def publish_device_discovery(device_name, ip):
    """Publish a discovery message for the device."""
    discovery_topic = f"homeassistant/device/{ip.replace('.', '_')}/config"
    payload = {
        "name": device_name,
        "identifiers": [ip],
        "manufacturer": "RandomManufacturer",
        "model": "RandomModel",
        "sw_version": "1.0",
        "configuration_url": f"http://{ip}",
        "via_device": ip
    } 
    mqtt_client.publish(discovery_topic, json.dumps(payload), retain=True)

def publish_service_discovery(service, ip, device_name):
    """Publish discovery message for a service under the device."""
    service_name = f"{service.replace('.', '_')}"
    discovery_topic = f"homeassistant/binary_sensor/{service_name}_{ip.replace('.', '_')}/config"
    payload = {
        "name": f"{service} on {ip}",
        "state_topic": f"service/{service}/{ip}",
        "payload_on": "up",
        "payload_off": "down",
        "device_class": "connectivity",
        "unique_id": f"sensor_{service}_{ip}",
        "device": {
            "identifiers": [ip],
            "name": device_name,
            "manufacturer": "RandomManufacturer",
            "model": "RandomModel",
        }
    }
    mqtt_client.publish(discovery_topic, json.dumps(payload), retain=True)

def publish_restart_service_action(service, ip, device_name):
    """Publish discovery message for a restart service button."""
    service_name = f"{service.replace('.', '_')}"
    discovery_topic = f"homeassistant/button/{service_name}_{ip.replace('.', '_')}/config"
    payload = {
        "name": f"Restart {service} on {ip}",
        "command_topic": f"service/restart/{service}/{ip}",
        "device": {
            "identifiers": [ip],
            "name": device_name,
            "manufacturer": "RandomManufacturer",
            "model": "RandomModel",
        },
        "unique_id": f"restart_{service}_{ip}",
    } 
    mqtt_client.publish(discovery_topic, json.dumps(payload), retain=True)

def publish_stop_service_action(service, ip, device_name):
    """Publish discovery message for a stop service button."""
    service_name = f"{service.replace('.', '_')}"
    discovery_topic = f"homeassistant/button/stop_{service_name}_{ip.replace('.', '_')}/config"
    payload = {
        "name": f"Stop {service} on {ip}",
        "command_topic": f"service/stop/{service}/{ip}",
        "device": {
            "identifiers": [ip],
            "name": device_name,
            "manufacturer": "RandomManufacturer",
            "model": "RandomModel",
        },
        "unique_id": f"stop_{service}_{ip}",
    } 
    mqtt_client.publish(discovery_topic, json.dumps(payload), retain=True)

def check_service_status(ip, ssh_user, ssh_pass, service_name):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=ssh_user, password=ssh_pass)

        stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service_name}')
        status = stdout.read().strip().decode()

        ssh.close()
        return status == 'active'
    except Exception as e:
        print(f"Error checking service status for {service_name} on {ip}: {e}")
        return False

def restart_service(ip, ssh_user, ssh_pass, service_name):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {ip} as {ssh_user}...")
        ssh.connect(ip, username=ssh_user, password=ssh_pass)

        command = f'sudo systemctl restart {service_name}'
        print(f"Executing command: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()

        output = stdout.read().decode().strip()
        error_output = stderr.read().decode().strip()
        if error_output:
            print(f"Error restarting {service_name} on {ip}: {error_output}")
        else:
            print(f"Successfully restarted {service_name} on {ip}")
            send_restart_email_notification(service_name, ip)

    except Exception as e:
        print(f"Error restarting service {service_name} on {ip}: {e}")

def stop_service(ip, ssh_user, ssh_pass, service_name):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {ip} as {ssh_user}...")
        ssh.connect(ip, username=ssh_user, password=ssh_pass)

        command = f'sudo systemctl stop {service_name}'
        print(f"Executing command: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()

        output = stdout.read().decode().strip()
        error_output = stderr.read().decode().strip()
        if error_output:
            print(f"Error stopping {service_name} on {ip}: {error_output}")
        else:
            print(f"Successfully stopped {service_name} on {ip}")
            send_stop_email_notification(service_name, ip)

    except Exception as e:
        print(f"Error stopping service {service_name} on {ip}: {e}")

def send_restart_email_notification(service_name, ip):
    msg = MIMEText(f"The service {service_name} has been successfully restarted on {ip}.")
    msg['Subject'] = f"Service Restarted: {service_name}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
        print("Restart email notification sent.")
    except Exception as e:
        print(f"Error sending restart email: {e}")

def send_stop_email_notification(service_name, ip):
    msg = MIMEText(f"The service {service_name} has been successfully stopped on {ip}.")
    msg['Subject'] = f"Service Stopped: {service_name}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
        print("Stop email notification sent.")
    except Exception as e:
        print(f"Error sending stop email: {e}")

def send_service_down_email_notification(service_name, ip):
    msg = MIMEText(f"The service {service_name} is down on {ip}. Please check it.")
    msg['Subject'] = f"Service Alert: {service_name} is Down"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
        print("Service down email notification sent.")
    except Exception as e:
        print(f"Error sending service down email: {e}")

def on_message(client, userdata, message):
    print(f"Received message on topic: {message.topic}")
    topic_parts = message.topic.split('/')

    if len(topic_parts) == 4:
        action = topic_parts[1]
        service = topic_parts[2]
        ip = topic_parts[3]

        if action == 'restart':
            print(f"Processing restart command for {service} on {ip}")
            for server in SERVERS:
                if server["ip"] == ip:
                    ssh_user = server["ssh_user"]
                    ssh_pass = server["ssh_pass"]
                    restart_service(ip, ssh_user, ssh_pass, service)
                    return
        elif action == 'stop':
            print(f"Processing stop command for {service} on {ip}")
            for server in SERVERS:
                if server["ip"] == ip:
                    ssh_user = server["ssh_user"]
                    ssh_pass = server["ssh_pass"]
                    stop_service(ip, ssh_user, ssh_pass, service)
                    return
    else:
        print("Message format is incorrect or incomplete.")

def main():
    # Publish device discovery messages
    for server in SERVERS:
        device_name = server["device_name"]
        ip = server["ip"]
        publish_device_discovery(device_name, ip)

        # Publish discovery messages for each service
        for service in server["services"]:
            publish_service_discovery(service, ip, device_name)
            publish_restart_service_action(service, ip, device_name)
            publish_stop_service_action(service, ip, device_name)  # Add stop action

    mqtt_client.loop_start()
    mqtt_client.subscribe("service/restart/#")
    mqtt_client.subscribe("service/stop/#")  # Subscribe to stop actions
    mqtt_client.on_message = on_message
    print("Subscribed to service/restart/# and service/stop/#")

    try:
        while True:
            for server in SERVERS:
                ip = server["ip"]
                ssh_user = server["ssh_user"]
                ssh_pass = server["ssh_pass"]
                services = server["services"]

                for service in services:
                    service_status = check_service_status(ip, ssh_user, ssh_pass, service)
                    mqtt_client.publish(f"service/{service}/{ip}", "up" if service_status else "down")

                    if not service_status:
                        print(f"{service} is not running on {ip}. Sending email notification.")
                        send_service_down_email_notification(service, ip)
                    else:
                        print(f"{service} is running on {ip}.")

            time.sleep(30)  # Check every minute
    except KeyboardInterrupt:
        pass
    finally:
        mqtt_client.loop_stop()

if __name__ == "__main__":
    main()

