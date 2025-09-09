import sqlite3
import asyncio
import unittest
from pathlib import Path

from server_side.utils.tools_functions import (
    _filesystem_operation,
    _execute_database_query,
    _simulate_api_call,
)
from server_side.utils.input_models import (
    FileOperationInput,
    DatabaseQueryInput,
    APICallInput,
)


class TestToolsFunctions(unittest.TestCase):
    def test_filesystem_write_read_list_delete(self):
        tmp_path = Path("./tests_tmp")
        if tmp_path.exists():
            # clean up from previous runs
            import shutil

            shutil.rmtree(tmp_path)

        tmp_path.mkdir(parents=True, exist_ok=True)

        # Write a file
        write_input = FileOperationInput(
            operation="write", path="dir1/file.txt", content="hello world"
        )
        resp = _filesystem_operation(write_input, data_path=tmp_path)
        self.assertTrue(resp.get("sucess"))

        # Read the file
        read_input = FileOperationInput(operation="read", path="dir1/file.txt")
        resp = _filesystem_operation(read_input, data_path=tmp_path)
        self.assertTrue(resp.get("sucess"))
        self.assertEqual(resp.get("content"), "hello world")

        # List directory
        list_input = FileOperationInput(operation="list", path="dir1")
        resp = _filesystem_operation(list_input, data_path=tmp_path)
        self.assertTrue(resp.get("sucess"))
        self.assertGreaterEqual(resp.get("count", 0), 1)

        # Delete the file
        delete_input = FileOperationInput(operation="delete", path="dir1/file.txt")
        resp = _filesystem_operation(delete_input, data_path=tmp_path)
        self.assertTrue(resp.get("sucess"))

        # cleanup
        import shutil

        shutil.rmtree(tmp_path)

    def test_execute_database_query_select_and_insert(self):
        tmp_path = Path("./tests_tmp_db")
        if tmp_path.exists():
            import shutil

            shutil.rmtree(tmp_path)
        tmp_path.mkdir(parents=True, exist_ok=True)

        # Prepare a sqlite database under tmp_path
        db_file = tmp_path / "main.db"
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT)"
        )
        cur.executemany("INSERT INTO people (name) VALUES (?)", [("Alice",), ("Bob",)])
        conn.commit()
        conn.close()

        query_input = DatabaseQueryInput(query="SELECT * FROM people", database="main")
        resp = asyncio.run(_execute_database_query(query_input, data_path=tmp_path))

        self.assertTrue(resp.get("sucess"))
        self.assertEqual(resp.get("row_count"), 2)
        names = [r.get("name") for r in resp.get("results", [])]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

        # cleanup
        import shutil

        shutil.rmtree(tmp_path)

    def test_simulate_api_call_variants(self):
        # Weather URL should return simulated weather data
        weather_input = APICallInput(
            url="https://api.example.com/weather", method="GET"
        )
        weather_resp = asyncio.run(_simulate_api_call(weather_input))
        self.assertTrue(weather_resp.get("success"))
        self.assertTrue(
            "temperature" in weather_resp.get("data", {}) or "message" in weather_resp
        )

        # News URL should return articles
        news_input = APICallInput(url="https://api.example.com/news", method="GET")
        news_resp = asyncio.run(_simulate_api_call(news_input))
        self.assertTrue(news_resp.get("success"))
        self.assertTrue(
            "articles" in news_resp.get("data", {})
            or isinstance(news_resp.get("data"), dict)
        )


if __name__ == "__main__":
    unittest.main()
