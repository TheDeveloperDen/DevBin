from pydantic import BaseModel


class UserMetaData(BaseModel):
    ip: str
    user_agent: str
