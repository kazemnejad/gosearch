from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship

from gosearch.database.connection import Base

word_page_table = Table('word_page', Base.metadata,
                        Column('page_id', Integer, ForeignKey('pages.id')),
                        Column('word_id', Integer, ForeignKey('words.id'))
                        )


class Page(Base):
    __tablename__ = 'pages'
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    url = Column("url", String(1000), nullable=False)

    words = relationship(
        "Word",
        secondary=word_page_table,
        back_populates="pages")

    def __init__(self, url):
        self.url = url


class Word(Base):
    __tablename__ = 'words'
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    text = Column("text", String(100), nullable=False, index=True)

    pages = relationship(
        "Page",
        secondary=word_page_table,
        back_populates="words")

    def __init__(self, text):
        self.text = text