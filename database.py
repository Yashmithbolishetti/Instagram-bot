from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./data.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True)
    instagram_sender_id = Column(String, unique=True, index=True)
    manus_task_id = Column(String, unique=True, index=True)


def init_db():
    Base.metadata.create_all(bind=engine)
