from pydantic import BaseModel

responses = {
    500: {"description": "Internal server error"},
    400: {"description": "Not supported"},
    401: {"description": "Unauthorized"},
    404: {"description": "Not found"},
    422: {"description": "Not found"},
    200: {"description": "Successful Response",
          "content": {
              "text/plain": {},
              "image/png": {},
              "image/svg": {},
              "image/jpg": {},
              "image/eps": {},
              "text/html": {}
          }
          }
}


class PageDataModel(BaseModel):
    limit: int = 50
    page: int = 1
