import re
from json import JSONEncoder
from mysql.connector import conversion
from mysql.connector.constants import FieldType
from mysql.connector.cursor import MySQLCursorDict

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


class CallbackProvider(object):
    def __init__(self, callback=None):
        self.callback = callback

    def get(self):
        return self.callback

    def set(self, callback):
        self.callback = callback

    def reset(self):
        self.set(None)


class SuperCursor(MySQLCursorDict):
    def set_callback_provider(self, callback_provider):
        self.callback_provider = callback_provider

    def _row_to_list(self, row, fields):

        convertor = self._connection.converter

        i = 0
        result = [None] * len(fields)

        if not convertor._cache_field_types:
            convertor._cache_field_types = {}
            for name, info in FieldType.desc.items():
                try:
                    convertor._cache_field_types[info[0]] = getattr(
                        convertor, '_{0}_to_python'.format(name))
                except AttributeError:
                    # We ignore field types which has no method
                    pass

        for field in fields:
            field_type = field[1]

            if (row[i] == 0 and field_type != FieldType.BIT) or row[i] is None:
                # Don't convert NULL value
                i += 1
                continue

            try:
                result[i] = convertor._cache_field_types[field_type](row[i], field)
            except KeyError:
                # If one type is not defined, we just return the value as str
                try:
                    result[i] = row[i].decode('utf-8')
                except UnicodeDecodeError:
                    result[i] = row[i]
            except (ValueError, TypeError) as err:
                err.message = "{0} (field {1})".format(str(err), field[0])
                raise

            i += 1

        return SuperList(result, self.callback_provider)

    def _row_to_python(self, rowdata, desc=None):
        return self._row_to_list(rowdata, desc)


class SuperList(object):
    def __init__(self, data, on_equal_callback_provider, unique_index=0):
        self.data = data
        self.unique_index = unique_index
        # self.result = result
        self.on_equal_callback_provider = on_equal_callback_provider

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __eq__(self, other):
        answer = self[self.unique_index] == other[self.unique_index]
        # if answer and self.result is not None:
        #     data = SuperTuple(self.data[:-1] + tuple([self[-1] + other[-1]]), None)
        #     self.result.add(data)

        callback = self.on_equal_callback_provider.get()
        if answer and callback is not None:
            callback(self, other)

        return answer

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self[self.unique_index])

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)


class SuperListJsonEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SuperList):
            return {
                "id": int(obj[0]),
                "url": unicode(obj[1].decode("utf-8")),
                "title": unicode(obj[2].decode("utf-8")),
                "content": unicode(obj[3].decode("utf-8"))[:300],
                "score": int(obj[4])
            }

        return JSONEncoder.default(self, obj)


class superset(object):
    def __init__(self, callback_provider):
        self.callback_provider = callback_provider

    def intersection(self, aSet, bSet, on_insert_callback):
        result = set()

        def callback(zelf, other):
            result.add(on_insert_callback(zelf, other))

        self.callback_provider.set(callback)
        aSet & bSet

        self.callback_provider.reset()
        return result


class SearchEngine(object):
    def __init__(self, db, query, ands, nots, ors):
        self.callback_provider = CallbackProvider()

        self.db = db
        self.cursor = self.db.cursor(cursor_class=SuperCursor)
        self.cursor.set_callback_provider(self.callback_provider)

        self.query = self._normalize_query(query)
        self.word_ids = {}

        self.ands = self._normalize_query(ands)
        self.is_and_enabled = len(self.ands) > 0

        self.nots = self._normalize_query(nots)
        self.is_not_enabled = len(self.nots) > 0

        self.ors = self._normalize_query(ors)
        self.is_or_enabled = len(self.ors) > 1

    @staticmethod
    def _normalize_query(query):
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
        sql = '''SELECT pages.*, words.id, indexes.score
            FROM words
            JOIN indexes on (words.id = indexes.word_id)
            JOIN pages ON (indexes.page_id = pages.id)
            WHERE words.text = "%s"
            ORDER BY indexes.score DESC''' % conversion.MySQLConverter().escape(str(word))

        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        if len(result) > 0:
            self.word_ids[word] = result[0][-2]

        return result

    def get_word_positions_in_page(self, word_id, page_id):
        sql = '''SELECT id, indexx FROM `positions` WHERE page_id = %d and word_id = %d ORDER BY indexx''' \
              % (int(page_id), int(word_id))

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

        result = self._raw_query_search(self.query)
        self._apply_positions(result, self.query)

        result.sort(key=lambda x: x[-1], reverse=True)

        return result

    def _apply_positions(self, result, words):
        i = 0
        while i + 1 < len(words):
            word_id = self.word_ids.get(words[i])
            next_word_id = self.word_ids.get(words[i + 1])

            if not word_id or not next_word_id:
                i += 1
                continue

            for page in result:
                page[-1] += self._get_positions_score(page[0], word_id, next_word_id)

            i += 1

    def _raw_query_search(self, query):
        word_results = []
        for word in query:
            word_results.append(self.get_pages_for_word(word))

        word_results.sort(key=lambda res: len(res))

        result = superset(self.callback_provider).intersection(
            set(word_results[0]),
            set(word_results[1]),
            self._summarize_scores_on_insert
        )

        for i in range(2, len(word_results)):
            result = superset(self.callback_provider).intersection(
                result,
                set(word_results[i]),
                self._summarize_scores_on_insert
            )

        return list(result)

    def _get_positions_score(self, page_id, first_word_id, second_word_id):
        first_positions = self.get_word_positions_in_page(first_word_id, page_id)
        second_positions = self.get_word_positions_in_page(second_word_id, page_id)

        score = 0

        start = 0
        for i in xrange(len(first_positions)):
            element = first_positions[i][-1]
            try:
                start = self._get_first_bigger_number(element, second_positions, start)
            except IndexError:
                break

            dif = second_positions[start][-1] - element
            if dif == 1:
                score += 50
                start += 1
            elif dif == 2:
                score += 5
                start += 1

        return score

    @staticmethod
    def _get_first_bigger_number(source, lst, start):
        element = lst[start][-1]
        while source > element:
            start += 1
            element = lst[start][-1]

        return start

    @staticmethod
    def _summarize_scores_on_insert(self, other):
        self.data[-1] = self[-1] + other[-1]
        return self
    def _advance_search(self):
        result = self._raw_query_search(self.ands)
        not_word_results = []
        for word in self.nots:
            not_word_results.append(self.get_pages_for_word(word))
        # bayad supelist beshan
        for tupel in range(len(result)):
            for not_tupels in not_word_results:
                if result[tupel] in not_tupels:
                    del result[tupel]
                    break
        or_word_results = []
        for word in self.ors:
            or_word_results.append(self.get_pages_for_word(word))
        #bayad super list beshan
        for tupels in result[0]:
            for tupel in range(len(tupels)):
                flag = 0
                for or_tupels in or_word_results:
                    if tupels[tupel] in or_tupels:
                        flag += 1
                        continue
                if flag == 0:
                    del result[0][tupel]
                else:
                    result[0][tupel][-1] += flag*10
        return result

