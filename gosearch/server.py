# -*- coding: utf-8 -*-
from mysql.connector import MySQLConnection, conversion
from sqlalchemy import text

from flask import Flask, jsonify, render_template, request, g
from flask_cors import CORS

from gosearch.database import config
from gosearch.database.connection import db_session

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


def get_pages_for_word(word, cursor):
    sql = '''SELECT pages.*, indexes.score, pages.*
        FROM words
        JOIN indexes on (words.id = indexes.word_id)
        JOIN pages ON (indexes.page_id = pages.id)
        WHERE words.text = "%s"
        ORDER BY indexes.score DESC''' % conversion.MySQLConverter().escape(str(word))

    cursor.execute(sql)
    return cursor.fetchall()


@app.route("/search", methods=["GET"])
def search():
    query = request.args["q"]
    ands=[]
    cursor = get_db().cursor()

    items = []
    for row in get_pages_for_word(query, cursor):
        items.append({
            "id": int(row[0]),
            "url": unicode(row[1].decode("utf-8")),
            "title": unicode(row[2].decode("utf-8")),
            "content": unicode(row[3][:100].decode("utf-8")) + "...",
            "score": int(row[4])
        })

    cursor.close()
    return jsonify({"items": items})


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()


def run():
    global app
    app.run()
