from sqlalchemy.orm import Session, joinedload

from models import Classroom, Student
from schemas import StudentCreate, StudentUpdate


def get_students(
    db: Session,
    search: str | None = None,
    class_id: int | None = None
):
    query = (
        db.query(Student)
        .options(joinedload(Student.classroom))
    )

    if search:
        search_value = f"%{search}%"

        query = query.filter(
            (Student.full_name.like(search_value))
            |
            (Student.student_code.like(search_value))
            |
            (Student.email.like(search_value))
        )

    if class_id is not None:
        query = query.filter(
            Student.class_id == class_id
        )

    return query.all()


def get_student(
    db: Session,
    student_id: int
):
    return (
        db.query(Student)
        .options(joinedload(Student.classroom))
        .filter(Student.id == student_id)
        .first()
    )


def get_classroom(
    db: Session,
    class_id: int
):
    return (
        db.query(Classroom)
        .filter(Classroom.id == class_id)
        .first()
    )


def get_student_by_code(
    db: Session,
    student_code: str
):
    return (
        db.query(Student)
        .filter(Student.student_code == student_code)
        .first()
    )


def get_student_by_email(
    db: Session,
    email: str
):
    return (
        db.query(Student)
        .filter(Student.email == email)
        .first()
    )


def get_student_by_code_except(
    db: Session,
    student_code: str,
    student_id: int
):
    return (
        db.query(Student)
        .filter(
            Student.student_code == student_code,
            Student.id != student_id
        )
        .first()
    )


def get_student_by_email_except(
    db: Session,
    email: str,
    student_id: int
):
    return (
        db.query(Student)
        .filter(
            Student.email == email,
            Student.id != student_id
        )
        .first()
    )


def count_students_in_class(
    db: Session,
    class_id: int
):
    return (
        db.query(Student)
        .filter(Student.class_id == class_id)
        .count()
    )


def create_student(
    db: Session,
    student_data: StudentCreate
):
    student = Student(
        student_code=student_data.student_code,
        full_name=student_data.full_name,
        email=student_data.email,
        age=student_data.age,
        gender=student_data.gender,
        class_id=student_data.class_id
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


def update_student(
    db: Session,
    student: Student,
    student_data: StudentUpdate
):
    data = student_data.model_dump(
        exclude_unset=True
    )

    for field, value in data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    return student