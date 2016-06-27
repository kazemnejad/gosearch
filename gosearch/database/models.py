from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship

from gosearch.database.connection import Base


class Index(Base):
    __tablename__ = 'indexes'
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    word_id = Column("word_id", Integer, ForeignKey('words.id'))
    page_id = Column("page_id", Integer, ForeignKey("pages.id"))
    score = Column("score", Integer, nullable=False, default=-1)

    page = relationship("Page", back_populates="words")
    word = relationship("Word", back_populates="pages")

    def __init__(self, score):
        self.score = score


class Page(Base):
    __tablename__ = 'pages'
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    url = Column("url", String(1000), nullable=False)
    title = Column("title", Text, nullable=False)
    content = Column("content", Text, nullable=False)

    words = relationship("Index", back_populates="page")

    def __init__(self, url, title, content):
        self.url = url
        self.title = title if title else ""
        self.content = content if content else ""


class Word(Base):
    __tablename__ = 'words'
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    text = Column("text", String(100), nullable=False, index=True)

    pages = relationship("Index", back_populates="word")

    def __init__(self, text):
        self.text = text
