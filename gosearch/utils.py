from stemming.porter2 import stem


class TextUtils:
    @staticmethod
    def apply_porter(wordsList):
        for i in xrange(len(wordsList)):
            wordsList[i] = stem(wordsList[i])