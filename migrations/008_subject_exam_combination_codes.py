"""
Migration: combined_code and related columns on subject_exam_combinations
"""


def migrate(connection):
  columns = [
      ('codes_snapshot_json', 'TEXT NULL'),
      ('combined_code', 'VARCHAR(64) NULL'),
      ('display_order', 'INT NULL'),
  ]
  with connection.cursor() as cursor:
      for col_name, col_def in columns:
          cursor.execute(
              """
              SELECT COUNT(*) AS c FROM information_schema.COLUMNS
              WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'subject_exam_combinations'
                AND COLUMN_NAME = %s
              """,
              (col_name,),
          )
          result = cursor.fetchone()
          count = result.get('c', 0) if isinstance(result, dict) else (result[0] if result else 0)
          if not int(count or 0):
              cursor.execute(
                  f"ALTER TABLE subject_exam_combinations ADD COLUMN {col_name} {col_def}"
              )
  connection.commit()
  return True
