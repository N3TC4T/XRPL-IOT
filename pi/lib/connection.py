import logging
import time
import json
import sys
import random
from multiprocessing import Queue
from threading import Thread, Event, Timer
from collections import OrderedDict

import websocket

from .exceptions import ResponseFormatError


class Connection(Thread):
    def __init__(self, *args, server=None, timeout=None, log_level=None, **kwargs):
        self.socket = None
        self.server = server if server else 'wss://s.altnet.rippletest.net:51233'
        self.q = Queue()
        self.channel_configs = OrderedDict()

        # ripple private stuff
        self._ledgerVersion = None
        self._fee_base = None
        self._fee_ref = None

        # Connection Handling Attributes
        self.connected = Event()
        self.disconnect_called = Event()
        self.reconnect_required = Event()
        self.reconnect_interval = 10
        self.paused = Event()

        # Setup Timer attributes
        # Tracks API Connection & Responses
        self.ping_timer = None
        self.ping_interval = 120

        # Tracks Websocket Connection
        self.connection_timer = None
        self.connection_timeout = timeout if timeout else 30

        # Tracks responses from send_ping()
        self.pong_timer = None
        self.pong_received = False
        self.pong_timeout = 30

        # Logging stuff
        self.log = logging.getLogger(self.__module__)
        logging.basicConfig(stream=sys.stdout, format="[%(filename)s:%(lineno)s - %(funcName)10s() : %(message)s")
        if log_level == logging.DEBUG:
            websocket.enableTrace(True)
        self.log.setLevel(level=log_level if log_level else logging.DEBUG)

        # Call init of Thread and pass remaining args and kwargs
        Thread.__init__(self)
        self.daemon = True

    def disconnect(self):
        """Disconnects from the websocket connection and joins the Thread.
        :return:
        """
        self.log.debug("Disconnecting from API..")
        self.reconnect_required.clear()
        self.disconnect_called.set()
        if self.socket:
            self.socket.close()
        self.join(timeout=1)

    def reconnect(self):
        """Issues a reconnection by setting the reconnect_required event.
        :return:
        """
        # Reconnect attempt at self.reconnect_interval
        self.log.debug("Initiation reconnect sequence..")
        self.connected.clear()
        self.reconnect_required.set()
        if self.socket:
            self.socket.close()

    def _connect(self):
        """Creates a websocket connection.
        :return:
        """
        self.log.debug("Initializing Connection..")
        self.socket = websocket.WebSocketApp(
            self.server,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        self.log.debug("Starting Connection..")
        self.socket.run_forever()

        while self.reconnect_required.is_set():
            if not self.disconnect_called.is_set():
                self.log.info("Attempting to connect again in %s seconds."
                              % self.reconnect_interval)
                self.state = "unavailable"
                time.sleep(self.reconnect_interval)

                # We need to set this flag since closing the socket will
                # set it to False
                self.socket.keep_running = True
                self.socket.run_forever()

    def run(self):
        """Main method of Thread.
        :return:
        """
        self.log.debug("Starting up..")
        self._connect()

    def _on_message(self, ws, message):
        """Handles and passes received data to the appropriate handlers.
        :return:
        """
        raw, received_at = message, time.time()
        self.log.debug("Received new message %s at %s", raw, received_at)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Something wrong with this data, log and discard
            return

        if isinstance(data, dict):
            # This is a valid message
            self._data_handler(data, received_at)

        # We've received data, reset timers
        self._start_timers()

    def _on_close(self, ws, *args):
        self.log.info("Connection closed")
        self.connected.clear()
        self._stop_timers()

    def _on_open(self, ws):
        self.log.info("Connection opened")
        self.connected.set()
        self.send_ping()
        self.subscribe_ledger()
        self._start_timers()
        if self.reconnect_required.is_set():
            self.log.info("Connection reconnected, re-subscribing..")
            self._resubscribe(soft=False)

    def _on_error(self, ws, error):
        self.log.info("Connection Error - %s", error)
        self.reconnect_required.set()
        self.connected.clear()

    def subscribe_ledger(self):
        self.log.debug("Subscribe to ledger changes...")
        self.socket.send(json.dumps(dict(command='subscribe', id=random.randint(1,101), streams=['ledger'])))

    def _stop_timers(self):
        """Stops ping, pong and connection timers.
        :return:
        """
        if self.ping_timer:
            self.ping_timer.cancel()

        if self.connection_timer:
            self.connection_timer.cancel()

        if self.pong_timer:
            self.pong_timer.cancel()
        self.log.debug("Timers stopped.")

    def _start_timers(self):
        """Resets and starts timers for API data and connection.
        :return:
        """
        self.log.debug("Resetting timers..")
        self._stop_timers()

        # Sends a ping at ping_interval to see if API still responding
        self.ping_timer = Timer(self.ping_interval, self.send_ping)
        self.ping_timer.start()

        # Automatically reconnect if we did not receive data
        self.connection_timer = Timer(self.connection_timeout,
                                      self._connection_timed_out)
        self.connection_timer.start()

    def send_ping(self):
        """Sends a ping message to the API and starts pong timers.
        :return:
        """
        self.log.debug("Sending ping to API..")
        self.socket.send(json.dumps(dict(command='ping', id=random.randint(1,101))))
        self.pong_timer = Timer(self.pong_timeout, self._check_pong)
        self.pong_timer.start()

    def _check_pong(self):
        """Checks if a Pong message was received.
        :return:
        """
        self.pong_timer.cancel()
        if self.pong_received:
            self.log.debug("Pong received in time.")
            self.pong_received = False
        else:
            # reconnect
            self.log.debug("Pong not received in time."
                           "Issuing reconnect..")
            self.reconnect()

    def send(self, payload=None, **kwargs):
        """Sends the given Payload to the API via the websocket connection.
        :param payload:
        :param kwargs: payload parameters as key=value pairs
        :return:
        """

        if payload:
            payload = json.dumps(payload)
        else:
            payload = json.dumps(kwargs)
        self.log.debug("Sending payload to API: %s", payload)
        try:
            self.socket.send(payload)
        except websocket.WebSocketConnectionClosedException:
            self.log.error("Did not send out payload %s - client not connected. ", kwargs)

    def pass_to_client(self, event, data, *args):
        """Passes data up to the client via a Queue().
        :param event:
        :param data:
        :param args:
        :return:
        """
        self.q.put((event, data, *args))

    def _connection_timed_out(self):
        """Issues a reconnection if the connection timed out.
        :return:
        """
        self.log.debug("Fired! Issuing reconnect..")
        self.reconnect()

    def _pause(self):
        """Pauses the connection.
        :return:
        """
        self.log.debug("Setting paused() Flag!")
        self.paused.set()

    def _unpause(self):
        """Unpauses the connection.
        Send a message up to client that he should re-subscribe to all
        channels.
        :return:
        """
        self.log.debug("Clearing paused() Flag!")
        self.paused.clear()
        self.log.debug("Re-subscribing softly..")
        self._resubscribe(soft=True)

    def _pong_handler(self):
        """Handle a pong response.
        :return:
        """
        # We received a Pong response to our Ping!
        self.log.debug("Received a Response message!")
        self.pong_received = True

    def _data_handler(self, data, ts):
        """Distributes system messages to the appropriate handler.
        System messages include everything that arrives as a dict,
        :param data:
        :param ts:
        :return:
        """
        # Unpack the data
        event = data.pop('type')
        if event:
            if data.get('result'):
                if not isinstance(data.get('id'), int) or not data.get('id') >= 0:
                    raise ResponseFormatError('valid id not found in response', data)

                self.log.debug("Distributing %s to _response_handler..", data)
                self._response_handler(event, data, ts)
            elif data.get('engine_result'):
                self._response_handler(event, data, ts)
            else:
                self._pong_handler()
        elif event == 'ledgerClosed':
            self._ledger_handler(data, ts)
        elif not event or data.error:
            # Error handling
            # Todo: Should be handle the error
            print('error', data.error, data.error_message, data)
        else:
            self.log.error("Unhandled event: %s, data: %s", event, data)

    def _ledger_handler(self, data, ts):
        self._ledgerVersion = data.get('ledger_index')
        self._fee_base = data.get('fee_base')
        self._fee_ref = data.get('fee_ref')

    def _response_handler(self, event, data, ts):
        """Handles responses to (un)subscribe and conf commands.
        Passes data up to client.
        :param data:
        :param ts:
        :return:
        """
        self.log.debug("Passing %s to client..", data)
        self.pass_to_client(event, data, ts)

    def _resubscribe(self, soft=False):
        """Resubscribes to all channels found in self.channel_configs.
        :param soft: if True, unsubscribes first.
        :return: None
        """
        q_list = []
        while True:
            try:
                identifier, q = self.channel_configs.popitem(last=True if soft else False)
            except KeyError:
                break
            q_list.append((identifier, q.copy()))
            if soft:
                q['command'] = 'unsubscribe'
            self.send(**q)

        # Resubscribe for soft start.
        if soft:
            for identifier, q in reversed(q_list):
                self.channel_configs[identifier] = q
                self.send(**q)
        else:
            for identifier, q in q_list:
                self.channel_configs[identifier] = q
