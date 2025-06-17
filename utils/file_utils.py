import json
import aiofiles


class MultiFileManager:
    def __init__(self):
        self.read_files = {}
        self.write_files = {}

    def readline(self, fname):
        if fname not in self.read_files:
            self.read_files = open(fname, "r", encoding="utf-8")
        return self.read_files[fname].readline()

    def read(self, fname):
        if fname not in self.read_files:
            self.read_files = open(fname, "r", encoding="utf-8")
        return self.read_files[fname].read()

    def write(self, fname, data):
        if fname not in self.write_files:
            self.write_files[fname] = open(fname, "w", encoding="utf-8")
        return self.write_files[fname].write(data)

    def close_all(self):
        for f in self.read_files.values():
            f.close()
        for f in self.write_files.values():
            f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()


async def read_jsonl_async(filepath):
    async with aiofiles.open(filepath, "r") as f:
        async for line in f:
            try:
                yield line, json.loads(line)
            except json.JSONDecodeError:
                continue
