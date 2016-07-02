# -*- coding: utf-8 -*-
import json
from mysql.connector import MySQLConnection

from flask import Flask, request, g, Response
from flask_cors import CORS
from redis import StrictRedis

from gosearch.database import config
from gosearch.searchengine import SearchEngine, SuperListJsonEncoder

app = Flask(__name__)
app.debug = True
app.secret_key = config.SECRET_KEY

CORS(app)


def get_db():
    if not hasattr(g, 'db'):
        g.db = MySQLConnection(
            host="localhost",
            user=config.db['user'],
            password=config.db['password'],
            database=config.db['dbname'],
            autocommit=True
        )

    return g.db


@app.route("/search", methods=["GET"])
def search():
    query = request.args["q"]
    ands = request.args["and"] if "and" in request.args else ""
    ors = request.args["or"] if "or" in request.args else ""
    nots = request.args["not"] if "not" in request.args else ""

    redis = StrictRedis(host="localhost")
    json_data = redis.get(query)

    if json_data is None:
        se = SearchEngine(get_db(), query, ands, nots, ors)

        json_data = json.dumps({"items": se.search()}, cls=SuperListJsonEncoder)
        redis.set(query, json_data)

    return Response(response=json_data,
                    status=200,
                    mimetype="application/json")


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()


def run():
    global app
    app.run(threaded=True)
