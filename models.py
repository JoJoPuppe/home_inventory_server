from sqlalchemy import Column, Integer, String, create_engine, Table, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

item_tags = Table('item_tags', Base.metadata,
    Column('item_id', ForeignKey('items.item_id'), primary_key=True),
    Column('tag_id', ForeignKey('tags.tag_id'), primary_key=True)
)


class Item(Base):
    __tablename__ = "items"

    item_id = Column(Integer, primary_key=True, index=True)
    label_id = Column(Integer, ForeignKey('labels.label_id'))
    parent_item_id = Column(Integer, ForeignKey('items.item_id'))
    name = Column(String, nullable=False)
    state = Column(Integer, ForeignKey('states.state_id'))
    comment = Column(String)
    image_lg_path = Column(String)
    image_sm_path = Column(String)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    last_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    tags = relationship("Tag", secondary=item_tags, back_populates="items")


class State(Base):
    __tablename__ = "states"

    state_id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String)


class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True, index=True)
    tag_name = Column(String)
    items = relationship("Item", secondary=item_tags, back_populates="tags")


class Label(Base):
    __tablename__ = "labels"
    label_id = Column(Integer, primary_key=True, index=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"
    event_id = Column(Integer, primary_key=True, index=True)
    event_date = Column(DateTime(timezone=True), server_default=func.now())
    item_id = Column(Integer, ForeignKey('items.item_id'))
    to_state = Column(Integer, ForeignKey('states.state_id'))
    parent_item_id = Column(Integer, ForeignKey('items.item_id'))


def init_db():
    Base.metadata.create_all(bind=engine)

def fill_states():
    session = SessionLocal()
    initial_states = [
        {"state_name": "stored"},
        {"state_name": "not stored"},
    ]
    for state_data in initial_states:
        # Check if the state already exists
        existing_state = session.query(State).filter_by(state_name=state_data["state_name"]).first()
        if not existing_state:
            # State does not exist, so add it
            state = State(**state_data)
            session.add(state)

    session.commit()
    session.close()
