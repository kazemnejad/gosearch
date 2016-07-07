# -*- coding: utf-8 -*-
import cPickle
import json
import time
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

    try:
        page = int(request.args["page"])
    except:
        page = 1

    # cache server
    redis = StrictRedis(host="localhost")

    # start measuring elapsed time
    start = time.time()

    # try to load result from cache
    key = json.dumps({
        "q": query,
        "a": ands,
        "o": ors,
        "n": nots
    })
    cache_result = redis.get(key)

    items = cPickle.loads(cache_result) if cache_result else None
    if not items:
        items = SearchEngine(get_db(), query, ands, nots, ors) \
            .search()

        # store results in cache
        redis.set(key, cPickle.dumps(items))

    elapsed_time = (time.time() - start) * 1000

    items_count = len(items)
    pages_count = items_count // 10
    if pages_count < items_count / 10.0:
        pages_count += 1

    if page > pages_count:
        page = pages_count

    # convert to index based
    page -= 1

    # calculate last item within this page
    last_item_index = (page * 10) + 10

    json_data = json.dumps({
        "items": items[page * 10: last_item_index if last_item_index < items_count else items_count],
        "total_count": items_count,
        "elapsed_time": int(elapsed_time)
    }, cls=SuperListJsonEncoder)

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
