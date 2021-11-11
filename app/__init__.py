from flask import Flask

webapp = Flask(__name__)

from app import auth
from app import index