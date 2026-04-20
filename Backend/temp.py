'''from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pkmngame.sqlite"

print("Creating DB at:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")

conn.execute("""
CREATE TABLE IF NOT EXISTS species (
    species_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS species_gen3 (
    species_id INTEGER PRIMARY KEY,
    type1 TEXT NOT NULL,
    type2 TEXT,
    type3 TEXT,
    FOREIGN KEY (species_id) REFERENCES species(species_id)
);
""")

conn.commit()

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables now:", tables)

conn.close()
'''

# lst = [1,2,2,3,4,5,6,6,6,7,8,8]
#
# pass
import time
memory = {}
def memoize(f):
    def inner(num):
        if num not in memory:
            memory[num] = f(num)
        return memory[num]
    return inner

@memoize
def factorial(num):
    if num == 1:
        return 1
    else:
        return num * factorial(num-1)

def ffactorial(num):
    if num == 1:
        return 1
    else:
        return num * ffactorial(num-1)

@memoize
def fib_memo(n):
    if n <= 1:
        return n
    return fib_memo(n-1) + fib_memo(n-2)

def fib_regular(n):
    if n <= 1:
        return n
    return fib_regular(n-1) + fib_regular(n-2)

# start = time.perf_counter()
# for i in range(1, 500):
#     print(f'factorial = {factorial(i)}')
# time1 = time.perf_counter()
#
# for i in range(1, 500):
#     print(f'factorial = {ffactorial(i)}')
# time2 = time.perf_counter()

start = time.perf_counter()
for i in range(1, 30):
    print(f'fib = {fib_memo(i)}')
time1 = time.perf_counter()

for i in range(1, 30):
    print(f'fib2 = {fib_regular(i)}')
time2 = time.perf_counter()

print('times')
print(time1 - start)
print(time2 - time1)
