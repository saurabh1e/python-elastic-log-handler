import logging
import logging.handlers
import requests
import traceback
import datetime
import json

from threading import Event, Thread, Condition, Lock, enumerate
from time import sleep


class LogHandler(logging.Handler):

    # Hold all logs buffered
    logs = []

    # Event for locking buffer additions while draining
    buffer_event = Event()

    # Condition to count log messages
    logs_counter_condition = Condition()

    # Lock to only drain logs once
    drain_lock = Lock()

    def __init__(self, logs_drain_count=100, logs_drain_timeout=10, log_type='python',
                 url=None, index=None, index_type=None, username=None, password=None):

        logging.Handler.__init__(self)
        self.log_type = log_type
        self.logs_drain_count = logs_drain_count
        self.logs_drain_timeout = logs_drain_timeout
        if not url:
            raise Exception
        self.index = index
        self.index_type = index_type
        self.url = "{0}/{1}/{2}/_bulk".format(url, index, index_type)
        self.username = username
        self.password = password

        self.is_main_thread_active = lambda: any((i.name == "MainThread") and i.is_alive() for i in enumerate())

        self.buffer_event.set()

        # Create threads
        timeout_thread = Thread(target=self.wait_to_timeout_and_drain)
        counter_thread = Thread(target=self.count_logs_and_drain)

        # And start them
        timeout_thread.start()
        counter_thread.start()

    def wait_to_timeout_and_drain(self):

        while True:
            sleep(self.logs_drain_timeout)
            if len(self.logs) > 0:
                self.drain_messages()

            if not self.is_main_thread_active():
                # Signal the counter thread so it would exit as well
                try:
                    self.logs_counter_condition.acquire()
                    self.logs_counter_condition.notify()
                finally:
                    self.logs_counter_condition.release()
                    break

    def count_logs_and_drain(self):
        try:
            # Acquire the condition
            self.logs_counter_condition.acquire()

            # Running indefinite
            while True:

                # Waiting for new log lines to come
                self.logs_counter_condition.wait()

                if not self.is_main_thread_active():
                    break

                # Do we have enough logs to drain?
                if len(self.logs) >= self.logs_drain_count:
                    self.drain_messages()

        finally:
            self.logs_counter_condition.release()

    def add_to_buffer(self, message):

        # Check if we are currently draining buffer so we wont loose logs
        self.buffer_event.wait()

        try:
            # Acquire the condition
            self.logs_counter_condition.acquire()
            self.logs.extend([
                '{"index": {"_index": "' + self.index + '", '
                '"_type": "' + self.index_type + '"}}',
                json.dumps(message)])

            # Notify watcher for a new log coming in

            self.logs_counter_condition.notify()

        finally:
            # Release the condition
            self.logs_counter_condition.release()

    def handle_exceptions(self, message):
        if message.exc_info:
            return '\n'.join(traceback.format_exception(*message.exc_info))
        else:
            return message.getMessage()

    def format_message(self, message):

        message_field = self.handle_exceptions(message)
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S") + ".%03d" % (now.microsecond / 1000) + "Z"

        return_json = {
            "logger": message.name,
            "line_number": message.lineno,
            "path_name": message.pathname,
            "log_level": message.levelname,
            "message": message_field,
            "type": self.log_type,
            "@timestamp": timestamp
        }

        return return_json

    def backup_logs(self, logs):
        timestamp = datetime.datetime.now().strftime("%d%m%Y-%H%M%S")
        print("Backing up your logs to log-failures-{0}.txt".format(timestamp))
        with open("log-failures-{0}.txt".format(timestamp), "a") as f:
            f.writelines('\n'.join(logs))

    def drain_messages(self):
        try:
            self.buffer_event.clear()
            self.drain_lock.acquire()

            # Copy buffer
            temp_logs = list(self.logs)
            self.logs = []

            # Release the event
            self.buffer_event.set()

            # Not configurable from the outside
            sleep_between_retries = 2000
            number_of_retries = 4

            success_in_send = False
            headers = {"Content-type": "text/plain"}
            for current_try in range(number_of_retries):
                response = requests.post(self.url, headers=headers,
                                         data='\n'.join(temp_logs)+'\n', auth=(self.username, self.password))
                if response.status_code != 200:  # 429 400, on 400 print stdout
                    if response.status_code == 400:

                        print("Got unexpected 400 code , response: {0}".format(response.text))
                        self.backup_logs(temp_logs)

                    if response.status_code == 401:
                        print("You are not authorized ! dropping..")
                        break

                    sleep(sleep_between_retries)
                    sleep_between_retries *= 2
                else:
                    success_in_send = True
                    break

            if not success_in_send:

                # Write to file
                self.backup_logs(temp_logs)

        finally:
            self.buffer_event.set()
            self.drain_lock.release()

    def emit(self, record):
        self.add_to_buffer(self.format_message(record))
