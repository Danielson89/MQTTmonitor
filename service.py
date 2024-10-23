import time
import paramiko
import smtplib
from email.mime.text import MIMEText
import paho.mqtt.client as mqtt
import json

# Configuration
MQTT_BROKER = "192.0.2.1"  # MQTT broker IP
MQTT_PORT = 1883
MQTT_USER = "user123"  # MQTT username
MQTT_PASS = "password123"  # MQTT password

# List of servers and services to monitor
SERVERS = [
    {
        "ip": "192.0.2.2",
        "ssh_user": "userA",
        "ssh_pass": "passA",
        "services": ["service1.service", "service2.service"],
        "device_name": "Device Monitor A"
    },
    {
        "ip": "192.0.2.3",
        "ssh_user": "userB",
        "ssh_pass": "passB",
        "services": ["service3.service"],
        "device_name": "Device Monitor B"
    },
    {
        "ip": "192.0.2.4",
        "ssh_user": "userC",
        "ssh_pass": "passC",
        "services": ["service4.service", "service5.service"],
        "device_name": "Device Monitor C"
    },
    {
        "ip": "192.0.2.5",
        "ssh_user": "userD",
        "ssh_pass": "passD",
        "services": ["service6.service", "service7.service"],
        "device_name": "Device Monitor D"
    },
    {
        "ip": "192.0.2.6",
        "ssh_user": "userE",
        "ssh_pass": "passE",
        "services": ["service8.service", "service9.service", "service10.service", "service11.service", "service12.service"],
        "device_name": "Device Monitor E"
    },
    {
        "ip": "192.0.2.7",
        "ssh_user": "userF",
        "ssh_pass": "passF",
        "services": ["service13.service"],
        "device_name": "Device Monitor F"
    },
    {
        "ip": "192.0.2.8",
        "ssh_user": "userG",
        "ssh_pass": "passG",
        "services": ["service14.service"],
        "device_name": "Device Monitor G"
    },
]

EMAIL_SENDER = "example@example.com"  # Sender email
EMAIL_RECEIVER = "receiver@example.com"  # Receiver email
SMTP_SERVER = "192.0.2.9"  # Your SMTP server
SMTP_PORT = 25  # or 465 for SSL

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

def publish_device_discovery(device_name, ip):
    """Publish a discovery message for the device."""
    discovery_topic = f"homeassistant/device/{ip.replace('.', '_')}/config"
    payload = {
        "name": device_name,
        "identifiers": [ip],
        "manufacturer": "ManufacturerName",
        "model": "ModelName",
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
        "unique_id": f"{service}_{ip}",
        "device": {
            "identifiers": [ip],
            "name": device_name,
            "manufacturer": "ManufacturerName",
            "model": "ModelName",
        }
    }
    mqtt_client.publish(discovery_topic, json.dumps(payload), retain=True)

def check_service_status(ip, ssh_user, ssh_pass, service_name):
    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=ssh_user, password=ssh_pass)

        # Execute systemd command to check service status
        stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service_name}')
        status = stdout.read().strip().decode()

        ssh.close()
        return status == 'active'
    except Exception as e:
        print(f"Error checking service status for {service_name} on {ip}: {e}")
        return False

def send_email_notification(service_name, ip):
    msg = MIMEText(f"The service {service_name} has stopped on {ip}.")
    msg['Subject'] = f"Service Alert: {service_name} Stopped"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
        print("Email notification sent.")
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    # Publish device discovery message
    for server in SERVERS:
        device_name = server["device_name"]
        ip = server["ip"]
        publish_device_discovery(device_name, ip)

        # Publish discovery messages for each service
        for service in server["services"]:
            publish_service_discovery(service, ip, device_name)

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
                    send_email_notification(service, ip)
                else:
                    print(f"{service} is running on {ip}.")

        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
