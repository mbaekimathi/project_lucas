"""
Migration: add 'successful' status for instant student exam applications.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE student_exam_applications
            MODIFY COLUMN status ENUM(
                'pending', 'successful', 'approved', 'rejected', 'withdrawn'
            ) NOT NULL DEFAULT 'successful'
        """)
    connection.commit()
    return True
