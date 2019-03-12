#TODO ресайклить файл логирования время от времени
import paho.mqtt.client as paho
import logging
import time
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
infoHandler = logging.FileHandler('info.log')
errorHandler = logging.FileHandler('errors.log')
infoHandler.setLevel(logging.INFO)
errorHandler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
infoHandler.setFormatter(formatter)
log.addHandler(infoHandler)
log.addHandler(errorHandler)


class TbClient:
    callback = None
    is_connected = False
    sub_dict = {}

    def __init__(self, host, token):
        self.client = paho.Client()
        self.host = host
        self.client.username_pw_set(token)
        self.callback = None

        def on_log(client, userdata, level, buf):
            log.info(buf)

        def on_connect(client, userdata, flags, rc, *extra_params):
            result_codes = {
                1: "incorrect protocol version",
                2: "invalid client identifier",
                3: "server unavailable",
                4: "bad username or password",
                5: "not authorised",
            }
            if rc == 0:
                self.is_connected = True
                log.info("connection SUCCESS")

            else:
                if rc in result_codes:
                    log.error("connection FAIL with error '%i':'%s'" % (rc, result_codes[rc]))
                else:
                    log.error("connection FAIL with unknown error")

        def on_disconnect(client, userdata, rc):
            if rc == 0:
                log.info("disconnect SUCCESS")
            else:
                log.error("disconnect FAIL with error code %i" % rc)

        def on_publish(client, userdata, result):
            log.info("data published")

        def on_message(client, userdata, message):
            content = message.payload.decode("utf-8")
            log.info(content)
            log.info(message.topic)

            if message.topic == 'v1/devices/me/attributes':
                message = eval(content)
                for key in self.sub_dict.keys():
                    if message.get(key):
                        if self.sub_dict.get(key):
                            for item in self.sub_dict.get(key):
                                print(type(item))
                                print(item)
                                item["callback"](message)


        self.client.on_disconnect = on_disconnect
        self.client.on_connect = on_connect
        self.client.on_log = on_log
        self.client.on_publish = on_publish
        self.client.on_message = on_message

    def loop(self):
        return self.client.loop()

    def connect(self):
        self.client.connect(self.host)
        self.client.loop_start()
        while self.is_connected is not True:  # Wait for connection
            time.sleep(0.2)


    def disconnect(self):
        self.client.disconnect()

    def send_telemetry(self, telemetry, quality_of_service=0, blocking=False):

        info = self.client.publish('v1/devices/me/telemetry', telemetry, quality_of_service)
        if blocking: info.wait_for_publish()

    def send_attributes(self, attributes, quality_of_service=0, blocking=False):

        info = self.client.publish('v1/devices/me/attributes', attributes, quality_of_service)
        if blocking: info.wait_for_publish()

    def unsubscribe_to_attributes(self, subscription_id):
        empty_keys = []
        for attribute in self.sub_dict.keys():
            for x in self.sub_dict[attribute]:
                if x["subscription_id"] == subscription_id:
                    self.sub_dict[attribute].remove(x)
                    log.info("Unsubscribed to " + attribute + ". subscription id " + str(subscription_id))
            if self.sub_dict[attribute] == []:
                empty_keys.append(attribute)
        for key in empty_keys:
            del self.sub_dict[key]

    def subscribe_to_attributes(self, callback, key="*"):
        self.client.subscribe('v1/devices/me/attributes', qos=2)
        self.callback = callback

        def find_max_sub_id():
            res = 1
            for key in self.sub_dict.keys():
                for item in self.sub_dict[key]:
                    if item["subscription_id"] > res:
                        res = item["subscription_id"]
            return res

        subscription_id = find_max_sub_id()
        inst = {
            "subscription_id": subscription_id,
            "callback": callback
        }

        def sub(inst, attribute):
            # subscribe to everything
            if attribute == "*":
                for attr in self.sub_dict.keys():
                    if inst not in self.sub_dict[attr]:
                        self.sub_dict[attr].append(inst)
                        log.info("Subscribed to " + attr + ", subscription id " + str(subscription_id))
            # if attribute doesnot exist create it with subscription
            elif attribute not in self.sub_dict.keys():
                self.sub_dict.update({attribute: [inst]})
                log.info("Subscribed to " + attribute + ", subscription id " + str(subscription_id))
            # if attribute exists create subscription
            else:
                self.sub_dict[attribute].append(inst)
                log.info("Subscribed to " + attribute + ", subscription id " + str(subscription_id))
        sub(inst, key)
        return(subscription_id)
