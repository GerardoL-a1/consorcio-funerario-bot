import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask
from routes.webhook import webhook_blueprint

app = Flask(__name__)
app.register_blueprint(webhook_blueprint)

@app.route('/', methods=['GET'])
def home():
    return '✅ Bot Consorcio Funerario funcionando.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
