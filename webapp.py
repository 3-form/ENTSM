import os
from resources import app
from resources.rest import init_db

APP_SECRET_KEY = \
    'YOUR KEY HERE'

if __name__ == '__main__':
    app.secret_key = APP_SECRET_KEY
    if not os.path.exists(app.config.get('DATABASE')):
        init_db()
    app.run(host=app.config.get('IP'), port=app.config.get('PORT'), use_debugger=False, debug=True, use_reloader=False)