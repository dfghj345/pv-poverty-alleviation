from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import calculator, cost, generation, policy, poverty, projects, regions, weather
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.schemas.response import Result
from app.services.pipeline_reader import dispose_pipeline_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)
    logger = get_logger('app.lifespan')
    logger.info('backend starting')
    yield
    await dispose_pipeline_engine()
    await engine.dispose()
    logger.info('backend stopped; db pools disposed')


app = FastAPI(title='PV Poverty Alleviation API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(projects.router, prefix='/v1/projects', tags=['Projects'])
app.include_router(calculator.router, prefix='/v1/calc', tags=['Calculator'])
app.include_router(policy.router, prefix='/v1', tags=['Policy'])
app.include_router(weather.router, prefix='/v1', tags=['Weather'])
app.include_router(poverty.router, prefix='/v1', tags=['Poverty'])
app.include_router(cost.router, prefix='/v1', tags=['Cost'])
app.include_router(generation.router, prefix='/v1', tags=['Generation'])
app.include_router(regions.router, prefix='/v1', tags=['Regions'])


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=Result.error(
            code=int(exc.status_code),
            message=exc.detail if isinstance(exc.detail, str) else 'Request Error',
        ).model_dump(),
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
        ).model_dump(),
    )


@app.get('/health', tags=['System'])
async def health_check():
    return Result.success(data={'status': 'healthy'}).model_dump()
