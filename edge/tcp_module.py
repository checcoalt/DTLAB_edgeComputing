from datetime import datetime
import socket
import threading
import json
import libellium.libellium as libellium
import mqttx.mqttx as mqttx
import config as config
import requests


class TcpModule:
    """
    TCP Module for handling Libellium frames received over TCP, parsing them, and publishing the measurements to an MQTT broker.

    Attributes:
        ip_address (str): Host's IP address. Default is 'localhost'.
        port_number (int): Host's port number where it is listening. Default is 0 (gets the first available port).
        buffer_size (int): Max dimension in bytes readable from messages. Default is 1024 bytes.
        buffer (str): An empty buffer where raw data will be written.
    """

    def __init__(self, ip_address='localhost', port_number=0, buffer_size=1024):
        """
        Constructor: Defines a configurable method to initialize TCP server.

        Args:
            ip_address (str, optional): Host's IP address. Default is 'localhost'.
            port_number (int, optional): Host's port number where it is listening. Default is 0 (gets the first available port).
            buffer_size (int, optional): Max dimension in bytes readable from messages. Default is 1024 bytes.
        """
        self.ip_address = ip_address
        self.port_number = port_number
        self.buffer_size = buffer_size
        self.buffer = ''

    def start(self):
        """
        Starts a TCP connection and listens for incoming connections on the specified IP and port.
        When a connection is established, this function creates a new thread to handle the connection.
        """
        try:
            # Socket creation
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Bind
            s.bind((self.ip_address, self.port_number))

            # Listen (max 5 connections)
            s.listen(5)

            # Message at start
            print(f"[TCP MODULE] Server on: <{self.ip_address}, {self.port_number}>")

            # Always listening for new connections
            while True:
                # Accept: returns a tuple (socket, (ip, port)) of the client
                connection, client_address = s.accept()
                print("[TCP MODULE] Client: " + str(client_address))

                # Start a new thread
                t = threading.Thread(target=self.thread_function, args=(connection,))
                t.start()

        except socket.error as e:
            print("[TCP MODULE] TCP connection error: " + str(e))

    def decode(self):
        """
        Decodes the received frame into structured data using the 'libellium' module's utilities.
        Returns a dictionary with collected measurements: {measure_type: {measure_value, measure_unit}}.
        """
        # Call to 'libellium' module utilities
        measurement = libellium.Libellium(self.buffer)
        measurement.parse()
        print(measurement)

        # Create a dictionary of measures
        measurements = {}
        for measure in measurement.measurements:

            json_data = {
                "value": measure[1],
                "unit": measure[0].unit
            }
            
            measurements[measure[0].ascii_id] = json_data

        return measurements

    def to_mqtt_broker(self, measures):
        """
        Publishes the collected measurements to the MQTT broker for the selected topic using the 'mqttx' module.

        Args:
            measures (dict): A dictionary of measurement data {measure_type: measure_value}.
        """
        try:
            # Starts an MQTTX client
            #publisher = mqttx.Client(config.BROKER_IP_ADDRESS, config.TOPIC_MEASUREMENTS)
            #publisher.start()

            # dict to JSON
            json_string = {
                "metadata": {
                    "date": datetime.today().strftime('%Y-%m-%d'),
                    "time": datetime.now().strftime('%H:%M:%S.%f')[:-5],
                    "room": config.ROOM,
                    "broker": config.BROKER_IP_ADDRESS + ":" + config.BROKER_PORT_NUMBER,
                    "topic": config.TOPIC_MEASUREMENTS
                },
                "data": measures
            }

            json_string = json.dumps(json_string)

            # Definire l'URL di destinazione
            url = "http://127.0.0.1:8000/display_json"  # Sostituisci con l'URL effettivo

            # Impostare le intestazioni HTTP (opzionale)
            headers = {
                "Content-Type": "application/json",
            }
            print(json_string)
            # Effettuare la richiesta HTTP POST con i dati JSON nel corpo
            response = requests.post(url, data=json_string, headers=headers)

            # Verificare la risposta
            if response.status_code == 200:
                print("Richiesta inviata con successo.")
            else:
                print("Errore nella richiesta:", response.status_code)
                print(response.text)  # Puoi stampare la risposta per ottenere ulteriori dettagli sull'errore, se presente

            # Publish on the given topic
            publisher.publish(json_string)

            # Stop the client
            publisher.stop()

        except mqttx.MqttConnectionError:
            print("[MQTTX MODULE]: connection error.")
        except mqttx.MqttSubscriptionError:
            print("[MQTTX MODULE]: subscription error.")
        except mqttx.MqttTopicNotSpecified:
            print("[MQTTX MODULE]: topic not specified.")
        except mqttx.MqttPublishError:
            print("[MQTTX MODULE]: publish error.")

    def thread_function(self, connection):
        """
        When a connection is established, this function represents a thread
        that waits for new messages on the given connection and completes
        expected tasks of this module for the received data.

        Args:
            connection (socket.socket): The connection socket for communication with the client.
        """
        # Receive: writes the established number of bytes into the buffer
        self.buffer = connection.recv(self.buffer_size).decode("utf-8")

        # Do stuff
        measurement = self.decode()
        self.to_mqtt_broker(measurement)


if __name__ == '__main__':
    print("[TCP MODULE]: Test main.")

    test = TcpModule(config.IP_ADDRESS, int(config.PORT_NUMBER), int(config.BUFFER_SIZE))
    test.start()
