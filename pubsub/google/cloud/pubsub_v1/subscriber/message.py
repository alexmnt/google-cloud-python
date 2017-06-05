# Copyright 2017, Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import math
import time


class Message(object):
    """A representation of a single Pub/Sub message.

    The common way to interact with
    :class:`~.pubsub_v1.subscriber.message.Message` objects is to receive
    them in callbacks on subscriptions; most users should never have a need
    to instantiate them by hand. (The exception to this is if you are
    implementing a custom subclass to
    :class:`~.pubsub_v1.subscriber.consumer.BaseConsumer`.)

    .. note::
        Messages in Google Cloud Pub/Sub are opaque blobs of bytes. This
        means that the ``data`` attribute will consistently be a
        :class:`bytes` object. If you want a text string, you should
        use :meth:`bytes.decode`.

    Properties:
        message_id (str): The message ID. In general, you should not need
            to use this directly.
        data (bytes): The data in the message.
        attributes (dict): The attributes sent along with the message.
        publish_time (datetime): The time that this message was originally
            published.
    """
    def __init__(self, consumer, ack_id, message):
        """Construct the Message.

        Args:
            consumer (~.pubsub_v1.subscriber.consumer.BaseConsumer): The
                consumer which originally received this message.
            ack_id (str): The ack_id received from Pub/Sub.
            message (~.pubsub_v1.types.PubsubMessage): The message received
                from Pub/Sub.
        """
        self._consumer = consumer
        self._ack_id = ack_id
        self._message = message
        self.message_id = message.message_id
        self.data = message.data
        self.attributes = message.attributes
        self.publish_time = message.publish_time

        # The instantiation time is the time that this message
        # was received. Tracking this provides us a way to be smart about
        # the default lease deadline.
        self._received_timestamp = time.time()

    def __repr__(self):
        # Get an abbreviated version of the data.
        abbv_data = self._data
        if len(answer) > 50:
            abbv_data = abbv_data[0:50] + b'...'

        # Return a useful representation.
        answer  = 'Message {\n'
        answer += '    data: {0!r}\n'.format(abbv_data)
        answer += '    attributes: {0!r}\n'.format(self.attributes)
        answer += '}'

    @property
    def attributes(self):
        """Return the attributes of the underlying Pub/Sub Message.

        Returns:
            dict: The message's attributes.
        """
        return self._message.attributes

    @property
    def data(self):
        """Return the data for the underlying Pub/Sub Message.

        Returns:
            bytes: The message data. This is always a bytestring; if you
                want a text string, call :meth:`bytes.decode`.
        """
        return self._message.data

    @property
    def publish_time(self):
        """Return the time that the message was originally published.

        Returns:
            datetime: The date and time that the message was published.
        """
        return self._message.publish_time

    def ack(self):
        """Acknowledge the given message.

        Acknowledging a message in Pub/Sub means that you are done
        with it, and it will not be delivered to this subscription again.
        You should avoid acknowledging messages until you have
        *finished* processing them, so that in the event of a failure,
        you receive the message again.

        .. warning::
            Acks in Pub/Sub are best effort. You should always
            ensure that your processing code is idempotent, as you may
            receive any given message more than once.
        """
        time_to_ack = math.ceil(time.time() - self._received_timestamp)
        self._consumer.histogram.add(time_to_ack)
        self._consumer.ack(self._ack_id)

    def modify_ack_deadline(self, seconds):
        """Set the deadline for acknowledgement to the given value.

        The default implementation handles this for you; you should not need
        to manually deal with setting ack deadlines. The exception case is
        if you are implementing your own custom subclass of
        :class:`~.pubsub_v1.subcriber.consumer.BaseConsumer`.

        .. note::
            This is not an extension; it *sets* the deadline to the given
            number of seconds from right now. It is even possible to use this
            method to make a deadline shorter.

        Args:
            seconds (int): The number of seconds to set the lease deadline
                to. This should be between 0 and 600. Due to network latency,
                values below 10 are advised against.
        """
        self._consumer.modify_ack_deadline(self._ack_id, seconds)

    def nack(self):
        """Decline to acknowldge the given message.

        This will cause the message to be re-delivered to the subscription.
        """
        self.modify_ack_deadline(seconds=0)