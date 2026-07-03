from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    host_name: str


class JoinSessionRequest(BaseModel):
    participant_name: str


class StartSessionRequest(BaseModel):
    host_name: str
    lat: float
    lng: float


class SubmitAnswersRequest(BaseModel):
    participant_name: str
    answers: dict


class RetrySessionRequest(BaseModel):
    host_name: str


class EndSessionRequest(BaseModel):
    host_name: str
