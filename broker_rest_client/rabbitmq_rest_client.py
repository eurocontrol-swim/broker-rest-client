"""
Copyright 2019 EUROCONTROL
==========================================

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the 
following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following 
   disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following 
   disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products 
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

==========================================

Editorial note: this license is an instance of the BSD license template as provided by the Open Source Initiative: 
http://opensource.org/licenses/BSD-3-Clause

Details on EUROCONTROL: http://www.eurocontrol.int
"""
import typing as t
from urllib.parse import quote

from requests import Response
from rest_client import Requestor, ClientFactory
from rest_client.errors import APIError
from rest_client.typing import RequestHandler

__author__ = "EUROCONTROL (SWIM)"


class RabbitMQRestClient(Requestor, ClientFactory):

    def __init__(self, request_handler: RequestHandler) -> None:
        Requestor.__init__(self, request_handler)
        self._request_handler = request_handler

        self._vhost = "/"

    @property
    def vhost(self):
        return quote(self._vhost, safe='')

    @vhost.setter
    def vhost(self, value):
        self._vhost = value

    def _get_create_topic_url(self, name):
        return f'api/exchanges/{self.vhost}/{name}'

    def _get_delete_topic_url(self, name):
        return self._get_create_topic_url(name)

    def _get_create_queue_url(self, name):
        return f'api/queues/{self.vhost}/{name}'

    def _get_bind_queue_url(self, queue, topic):
        return f'api/bindings/{self.vhost}/e/{topic}/q/{queue}'

    def _get_delete_queue_url(self, name):
        return f'api/queues/{self.vhost}/{name}'

    def _get_queue_bindings_url(self, queue):
        return f'api/queues/{self.vhost}/{queue}/bindings'

    def _get_delete_queue_binding_url(self, queue, topic, props):
        return f'api/bindings/{self.vhost}/e/{topic}/q/{queue}/{props}'

    def create_topic(self, name: str, durable: t.Optional[bool] = False) -> None:
        """
        Creates a new topic in RabbitMQ. It is basically an exchange of type 'topic'
        :param name:
        :param durable: indicates whether it survives a broker restart
        :raises: rest_client.errors.APIError
        """
        url = self._get_create_topic_url(name)

        data = {
            "type": "topic",
            "durable": durable,
            "auto_delete": False,
            "internal": False,
            "arguments": {}
        }

        self.perform_request('PUT', url, json=data)

    def delete_topic(self, name: str) -> None:
        """
        Deletes a topic
        :param name:
        :raises: rest_client.errors.APIError
        """
        url = self._get_delete_topic_url(name)

        self.perform_request('DELETE', url)

    def create_queue(self, name: str, durable: t.Optional[bool] = False) -> None:
        """
        Creates a new queue
        :param name:
        :param durable: indicates whether the queue survives a broker restart
        :raises: rest_client.errors.APIError
        """
        url = self._get_create_queue_url(name)
        data = {
            "durable": durable,
            "auto_delete": False,
            "arguments": {}
        }

        self.perform_request('PUT', url, json=data)

    def bind_queue_to_topic(self,
                            queue: str,
                            key: str,
                            topic: str = 'default',
                            durable: t.Optional[bool] = False) -> None:
        """
        Binds a queue with a topic using a routing key
        :param queue: the name of the queue
        :param key: the routing key by which the queue will be bound to the topic
        :param topic: the name of the topic
        :param durable: indicates whether the binding will survive a broker restart
        :raises: rest_client.errors.APIError
        """
        if topic == 'default':
            topic = 'amq.topic'

        url = self._get_bind_queue_url(queue, topic)
        data = {
            "routing_key": key,
            "arguments": {
                "durable": durable
            }
        }

        self.perform_request('POST', url, json=data)

    def delete_queue(self, name: str) -> None:
        """
        Deletes a queue
        :param name:
        :raises: rest_client.errors.APIError
        """
        url = self._get_delete_queue_url(name)

        self.perform_request('DELETE', url)

    def get_queue_bindings(self, queue: str, topic: str = None, key: str = None) -> t.List[t.Dict]:
        """
        Retrieves the bindings of a given queue
        :param queue: the name of the queue
        :param topic: the name of the topic (for filtering)
        :param key: the routing key of the binding (for filtering)
        :raises: rest_client.errors.APIError
        """
        url = self._get_queue_bindings_url(queue)

        bindings = self.perform_request('GET', url)

        if topic is not None:
            bindings = [b for b in bindings if b['source'] == topic]

        if key is not None:
            bindings = [b for b in bindings if b['routing_key'] == key]

        return bindings

    def delete_queue_binding(self, queue: str, topic: str, key: str) -> None:
        """
        Deletes a queue binding
        :param queue: the name of the queue
        :param topic: the topic the queue is bound to
        :param key: the routing_key of the binding
        """
        bindings = self.get_queue_bindings(queue, topic=topic, key=key)

        if not bindings:
            raise APIError(f"No binding found between topic '{topic}' and queue '{queue}' with name '{key}'", 404)

        props = bindings[0]['properties_key']

        url = self._get_delete_queue_binding_url(queue, topic, props)

        self.perform_request('DELETE', url)
