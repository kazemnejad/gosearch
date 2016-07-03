from mysql.connector import MySQLConnection
from threading import Thread, Lock

from gosearch.database import config
from gosearch.pipelines import TextNormalizationPipeline

import logging

logging.basicConfig()


class FixerThread(Thread):
    lock = Lock()

    def __init__(self, start, end):
        super(FixerThread, self).__init__()

        self.db = MySQLConnection(
            host="localhost",
            user=config.db['user'],
            password=config.db['password'],
            database=config.db['dbname'],
            autocommit=True
        )

        self.cursor = self.db.cursor()

        self.begin = start
        self.end = end

    def close_db(self):
        self.cursor.close()
        self.db.close()

    def get_update_sql(self, word_id, page_id, score):
        return

    def update_index(self, word, page, score):
        sql = "update indexes set `score`= %d where word_id = %d and page_id = %d" % (score, word[0], page[0])

        self.cursor.execute(sql)

    def get_word(self, text):
        sql = 'select id from words WHERE text = "%s"' % (text)

        self.cursor.execute(sql)
        word = self.cursor.fetchone()

        return word

    def get_position(self, word_id, page_id, position):
        sql = 'select id from positions WHERE word_id = %d AND page_id = %d AND indexx = %d' \
              % (word_id, page_id, position)

        self.cursor.execute(sql)
        pos = self.cursor.fetchone()

        return pos

    def add_position(self, word_id, page_id, position):
        sql = 'insert into positions (id, word_id, page_id, indexx) VALUES (NULL, %d , %d, %d)' \
              % (word_id, page_id, position)

        self.cursor.execute(sql)

    def get_pages_in_period(self):
        sql = "select * from pages WHERE id >= %s and id <= %d" % (self.begin, self.end)

        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def save_positions(self, word, page, positions):
        for index in positions:
            pos = self.get_position(word[0], page[0], index)
            if not pos:
                self.add_position(word[0], page[0], index)

    def process_result(self, result, page):
        words = result["words"]
        words_pos = result["wordspos"]

        for word_text in words:
            score = words[word_text]
            word = self.get_word(word_text)

            self.update_index(word, page, score)
            if word_text in words_pos:
                self.save_positions(word, page, words_pos[word_text])

    @staticmethod
    def log(msg):
        FixerThread.lock.acquire()
        print msg
        FixerThread.lock.release()

    def run(self):
        for page in self.get_pages_in_period():
            FixerThread.log("page: " + str(page[0]))
            pipeline = TextNormalizationPipeline()
            result = pipeline.process_item({
                "url": str(page[1]),
                "title": str(page[2]),
                "content": str(page[3])
            }, None)

            self.process_result(result, page)


if __name__ == "__main__":
    lst = [
        FixerThread(0, 1000),
        FixerThread(1001, 2000),
        FixerThread(2001, 3000),
        FixerThread(3001, 4000),
        FixerThread(4001, 5000),
        FixerThread(5001, 6000),
    ]

    for thread in lst:
        thread.start()

    for thread in lst:
        thread.join()
        thread.close_db()