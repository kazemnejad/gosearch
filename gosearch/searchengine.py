from mysql.connector import conversion
import re
import nltk
from stemming.porter2 import stem


class PageFields:
    id = 0
    url = 1
    title = 2
    content = 3
    score = 4
    word_id = 5


class PositionFields:
    id = 0
    word_id = 1
    page_id = 2
    index = 3


class SuperTuple(object):
    def __init__(self, data, result, unique_index=0):
        self.data = data
        self.unique_index = unique_index
        self.result = result

    def __getitem__(self, index):
        return self.data[index]

    def __eq__(self, other):
        answer = self[self.unique_index] == other[self.unique_index]
        if answer and self.result is not None:
            data = SuperTuple(self.data[:-1] + tuple([self[-1] + other[-1]]), None)
            self.result.add(data)
        return answer

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self[self.unique_index])

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)


class SearchEngine(object):
    def __init__(self, db, query, ands, nots, ors):
        self.db = db
        self.cursor = self.db.cursor()

        self.query = self.normalize_query(query)

        self.ands = self.normalize_query(ands)
        self.is_and_enabled = len(self.ands) > 0

        self.nots = self.normalize_query(nots)
        self.is_not_enabled = len(self.nots) > 0

        self.ors = self.normalize_query(ors)
        self.is_or_enabled = len(self.ors) > 1

    def normalize_query(self, query):
        query = re.findall(r'[A-Za-z0-9]\w*', query.lower())
        for i in range(len(query)):
            query[i] = stem(query[i])
        delWord = dict(nltk.pos_tag(query))
        for i in delWord:
            if delWord[i] == 'DT' or delWord[i] == 'IN' or delWord[i] == 'CC' or delWord[i] == 'TO':
                for j in range(query.count(i)):
                    query.remove(i)
        return query

    def get_pages_for_word(self, word):
        sql = '''SELECT pages.*, indexes.score
            FROM words
            JOIN indexes on (words.id = indexes.word_id)
            JOIN pages ON (indexes.page_id = pages.id)
            WHERE words.text = "%s"
            ORDER BY indexes.score DESC''' % conversion.MySQLConverter().escape(str(word))

        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_word_positions_in_page(self, word_id, page_id):
        sql = '''SELECT * FROM `positions` WHERE page_id = %d and %d = 2778''' % (int(page_id), int(word_id))

        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_positions_of_word(self, word_id):
        sql = '''SELECT pages.*, positions.indexx
            FROM words
            JOIN positions on (words.id = positions.word_id)
            JOIN pages ON (positions.page_id = pages.id)
            WHERE word_id = %d''' % int(word_id)

        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def search(self):
        if self.is_and_enabled:
            pass
        if len(self.query) == 1 and not self.is_and_enabled and not self.is_not_enabled and not self.is_or_enabled:
            return self.get_pages_for_word(self.query[0])
        raw_result = []
        for i in self.query:
            raw_result.append(self.get_pages_for_word(i))
        raw_result.sort(key=lambda x: len(x))
        final_result1 = set()
        final_result2 = set()
        print len(raw_result[0]), len(raw_result[1])
        raw_result[0] = [SuperTuple(x, final_result1) for x in raw_result[0]]
        raw_result[1] = [SuperTuple(x, final_result1) for x in raw_result[1]]
        set(raw_result[0]) & set(raw_result[1])
        print len(final_result1)
        final_result1 = [SuperTuple(x, final_result2) for x in final_result1]
        for i in range(2, len(raw_result)):
            raw_result[i] = [SuperTuple(x, final_result2) for x in raw_result[i]]
            set(raw_result[i]) & set(final_result1)
            final_result1 = list(final_result2)[:]
            final_result2=set()
            final_result1 = [SuperTuple(x, final_result2) for x in final_result1]
        final_result1.sort(key=lambda x: x[-1], reverse=True)
        return final_result1
