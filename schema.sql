-- Student Management: database schema
-- SQLite is used by default and the app creates the table automatically on startup.
-- This file documents the equivalent DDL (SQLite syntax).

CREATE TABLE students (
    student_id  INTEGER      PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    phone       VARCHAR(20),
    age         INTEGER      NOT NULL CHECK (age BETWEEN 18 AND 60),
    course      VARCHAR(100) NOT NULL,
    address     VARCHAR(255),
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_students_email UNIQUE (email)
);

CREATE INDEX ix_students_course ON students (course);
