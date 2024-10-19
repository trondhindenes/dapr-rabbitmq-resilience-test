import os

import uvicorn  # noqa

from main import app


if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('APP_PORT', 8000)),
        log_level='debug',
    )
