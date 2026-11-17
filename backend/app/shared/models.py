from pydantic import BaseModel


class ConfluencePage(BaseModel):
    id: str
    title: str
    type: str | None = None
    status: str | None = None


class Revision(BaseModel):
    version: str
    published: str | None = None
    changecomment: str | None = None
    pageId: str
    link: str | None = None
    latest: str
    valid: str | None = None
