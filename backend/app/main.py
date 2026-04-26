from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import calculator, cost, generation, panel_data, policy, poverty, projects, regions, weather
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_database, initialize_database
from data_pipeline.db.session import dispose_engine as dispose_pipeline_database
from data_pipeline.db.session import initialize_database as initialize_pipeline_database
from app.schemas.response import Result


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)
    logger = get_logger('app.lifespan')
    await initialize_database()
    await initialize_pipeline_database()
    logger.info('backend starting')
    yield
    await dispose_pipeline_database()
    await dispose_database()
    logger.info('backend stopped; db pools disposed')


app = FastAPI(title='PV Poverty Alleviation API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

def include_api_router(router, *, v1_prefix: str, tags: list[str]) -> None:
    app.include_router(router, prefix=f'/v1{v1_prefix}', tags=tags)
    app.include_router(router, prefix=f'/api/v1{v1_prefix}', tags=tags)


include_api_router(projects.router, v1_prefix='/projects', tags=['Projects'])
include_api_router(calculator.router, v1_prefix='/calc', tags=['Calculator'])
include_api_router(policy.router, v1_prefix='', tags=['Policy'])
include_api_router(weather.router, v1_prefix='', tags=['Weather'])
include_api_router(poverty.router, v1_prefix='', tags=['Poverty'])
include_api_router(cost.router, v1_prefix='', tags=['Cost'])
include_api_router(generation.router, v1_prefix='', tags=['Generation'])
include_api_router(regions.router, v1_prefix='', tags=['Regions'])
include_api_router(panel_data.router, v1_prefix='', tags=['PanelData'])


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=Result.error(
            code=int(exc.status_code),
            message=exc.detail if isinstance(exc.detail, str) else 'Request Error',
        ).model_dump(by_alias=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = 'Request validation failed'
    if errors:
        first = errors[0]
        location = '.'.join(str(item) for item in first.get('loc', []) if item != 'body')
        error_text = first.get('msg', 'Invalid request')
        message = f'{location}: {error_text}' if location else str(error_text)

    return JSONResponse(
        status_code=422,
        content=Result.error(code=422, message=message).model_dump(by_alias=True),
    )


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    logger = get_logger('app.exception')
    logger.exception('unhandled exception')
    return JSONResponse(
        status_code=500,
        content=Result.error(
            code=500,
            message=f'Internal Server Error: {str(exc)}' if settings.DEBUG else 'Internal Server Error',
        ).model_dump(by_alias=True),
    )


@app.get('/health', tags=['System'])
async def health_check():
    return Result.success(data={'status': 'healthy'}).model_dump(by_alias=True)
