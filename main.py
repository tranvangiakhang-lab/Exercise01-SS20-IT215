from datetime import datetime, timezone

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

import crud
import models

from database import Base, engine, get_db

from schemas import (
    APIResponse,
    StudentCreate,
    StudentResponse,
    StudentUpdate
)


app = FastAPI(
    title="Student Management API",
    description="API quản lý sinh viên theo lớp học",
    version="1.0.0"
)


Base.metadata.create_all(
    bind=engine
)


def current_timestamp():
    return datetime.now(
        timezone.utc
    )


def response_data(
    status_code: int,
    message: str,
    data,
    error,
    path: str
):
    return {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": current_timestamp(),
        "path": path
    }


@app.exception_handler(
    HTTPException
)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data(
            status_code=exc.status_code,
            message=str(exc.detail),
            data=None,
            error={
                "code": exc.status_code,
                "detail": str(exc.detail)
            },
            path=request.url.path
        )
    )


@app.exception_handler(
    RequestValidationError
)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content=response_data(
            status_code=422,
            message="Dữ liệu không hợp lệ",
            data=None,
            error=exc.errors(),
            path=request.url.path
        )
    )


@app.exception_handler(
    Exception
)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content=response_data(
            status_code=500,
            message="Internal Server Error",
            data=None,
            error={
                "detail": str(exc)
            },
            path=request.url.path
        )
    )


@app.get("/")
def root():
    return response_data(
        status_code=200,
        message="Student Management API is running",
        data={
            "docs": "/docs"
        },
        error=None,
        path="/"
    )

@app.get(
    "/students",
    response_model=APIResponse[list[StudentResponse]]
)
def get_students(
    request: Request,
    search: str | None = Query(
        default=None,
        description="Tìm theo tên, mã sinh viên hoặc email"
    ),
    class_id: int | None = Query(
        default=None,
        ge=1
    ),
    db: Session = Depends(get_db)
):
    students = crud.get_students(
        db=db,
        search=search,
        class_id=class_id
    )

    return response_data(
        status_code=200,
        message="Lấy danh sách sinh viên thành công",
        data=students,
        error=None,
        path=request.url.path
    )


@app.get(
    "/students/{student_id}",
    response_model=APIResponse[StudentResponse]
)
def get_student(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    student = crud.get_student(
        db,
        student_id
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sinh viên"
        )

    return response_data(
        status_code=200,
        message="Lấy thông tin sinh viên thành công",
        data=student,
        error=None,
        path=request.url.path
    )


@app.post(
    "/students",
    response_model=APIResponse[StudentResponse],
    status_code=status.HTTP_201_CREATED
)
def create_student(
    student_data: StudentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    existing_code = crud.get_student_by_code(
        db,
        student_data.student_code
    )

    if existing_code:
        raise HTTPException(
            status_code=409,
            detail="Mã sinh viên đã tồn tại"
        )

    existing_email = crud.get_student_by_email(
        db,
        str(student_data.email)
    )

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email đã tồn tại"
        )

    classroom = crud.get_classroom(
        db,
        student_data.class_id
    )

    if not classroom:
        raise HTTPException(
            status_code=404,
            detail="Lớp học không tồn tại"
        )

    if classroom.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Lớp học không hoạt động"
        )

    student_count = crud.count_students_in_class(
        db,
        classroom.id
    )

    if student_count >= classroom.max_students:
        raise HTTPException(
            status_code=400,
            detail="Lớp học đã đủ số lượng sinh viên"
        )

    student = crud.create_student(
        db,
        student_data
    )

    student = crud.get_student(
        db,
        student.id
    )

    return response_data(
        status_code=201,
        message="Thêm sinh viên thành công",
        data=student,
        error=None,
        path=request.url.path
    )


@app.put(
    "/students/{student_id}",
    response_model=APIResponse[StudentResponse]
)
def update_student(
    student_id: int,
    student_data: StudentUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    student = crud.get_student(
        db,
        student_id
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sinh viên"
        )

    if student_data.student_code is not None:
        existing_code = crud.get_student_by_code_except(
            db,
            student_data.student_code,
            student_id
        )

        if existing_code:
            raise HTTPException(
                status_code=409,
                detail="Mã sinh viên đã tồn tại"
            )

    if student_data.email is not None:
        existing_email = crud.get_student_by_email_except(
            db,
            str(student_data.email),
            student_id
        )

        if existing_email:
            raise HTTPException(
                status_code=409,
                detail="Email đã tồn tại"
            )

    if (
        student_data.class_id is not None
        and student_data.class_id != student.class_id
    ):
        new_classroom = crud.get_classroom(
            db,
            student_data.class_id
        )

        if not new_classroom:
            raise HTTPException(
                status_code=404,
                detail="Lớp học mới không tồn tại"
            )

        if new_classroom.status != "active":
            raise HTTPException(
                status_code=400,
                detail="Lớp học mới không hoạt động"
            )

        student_count = crud.count_students_in_class(
            db,
            new_classroom.id
        )

        if student_count >= new_classroom.max_students:
            raise HTTPException(
                status_code=400,
                detail="Lớp học mới đã đủ số lượng sinh viên"
            )

    student = crud.update_student(
        db,
        student,
        student_data
    )

    student = crud.get_student(
        db,
        student.id
    )

    return response_data(
        status_code=200,
        message="Cập nhật sinh viên thành công",
        data=student,
        error=None,
        path=request.url.path
    )