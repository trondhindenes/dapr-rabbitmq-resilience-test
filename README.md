# Dapr resiliency testing

## Prerequisites
Dapr CLI: You need to have the dapr cli installed already. Download the dapr cli and then run `dapr init -s` in the current dir, this will download the dapr daemon cli)
Initialize the python app (assuming you have pyenv and poetry installed, pyenv has access to python 3.12.6, and that you've set the global poetry flag `poetry config virtualenvs.in-project = true`):
```shell
PYENV_VERSION=3.12.6 python3 -m venv .venv
poetry install
```


## Run it
First, start rabbitmq
```shell
docker run -p 5672:5672 -p 15672:15672 --hostname my-rabbit -e RABBITMQ_DEFAULT_USER=user -e RABBITMQ_DEFAULT_PASS=password rabbitmq:3-management
```

Then, run dapr (you need to have it installed already. Download the dapr cli and then run `dapr init -s`)
```shell
dapr run --app-id orders --app-port 8000 \
--app-max-concurrency 1 \
--resources-path local_dev/components \
--config local_dev/config.yml \
--scheduler-host-address "" \
--dapr-grpc-port 5001 \
--dapr-http-port 5002
```

Then, start the app:
```shell
poetry run python src/run_main.py
```

## Test different things
The test app has an endpoint `/invoke-order` which will publish a message to itself.
This endpoint can be invoked with different parameters in order to make the pubsub receiver endpoint respond with different behaviors:

Some findings. See also https://docs.dapr.io/reference/api/pubsub_api/

### RETRY
`curl 'http://localhost:8000/invoke-order?status_string=RETRY'`

This will cause Dapr to attempt to re-send the message over and over. This is done by the local
dapr daemon(sidecar), it does not seem to be returned to the queue. If the dapr daemon is shut down,
the message remains un-acked and returned to the queue.
You can use the rabbitmq web interface (http://localhost:15672/#/queues/%2F/orders-orders) to get rid of the stuck message (purge queue) before starting dapr back up

### HTTP500 response
`curl 'http://localhost:8000/invoke-order?status_http_code=500&wait_secs=1'`
This causes the pubsub endpoint to respond with a http 500 when it receives a message. The effect is same as for RETRY above.

### HTTP400 response:
`curl 'http://localhost:8000/invoke-order?status_http_code=400'`
Same effect as for RETRY. If a 404 is specified, dapr logs "non-retriable error returned from app while processing pub/sub", 
and drops the message withot retrying


### DROP
`curl 'http://localhost:8000/invoke-order?status_string=DROP'`
Message is dropped. Dapr daemon logs a warning

### Force crash
`curl http://localhost:8000/invoke-order?force_fail=true`
This causes the Fastapi app to abruptly shut down, not returning anything at all to dapr.
Dapr seems to handle this in the same way as a retry: the dapr daemon attempts to re-deliver the message
If the dapr daemon is shut down, the message is deleted to the queue, as it hasn't been acked.

### TTL with retry
`curl 'http://localhost:8000/invoke-order?status_string=RETRY&wait_secs=1'`
Before running this test, pubsub definition ttlInSeconds in set to "10" (it is not set by default). This test causes dapr to retry the message around 10 times, 
before dropping it. If dead-letter queue is enabled, message is placed on DLQ

### TTL with retry - multiple messages
`curl 'http://localhost:8000/invoke-order?status_string=RETRY&wait_secs=1&msg_count=3'`

### retry with "requeueInFailure" set to "false"
`curl 'http://localhost:8000/invoke-order?status_string=RETRY&wait_secs=1&msg_count=3'`
with this setting, dapr will not retry any messages, and will also not return items to the queue when the dapr daemon is stopped.
