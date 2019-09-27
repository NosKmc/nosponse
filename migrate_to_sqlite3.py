from typing import Any, Dict, List, Sequence, TypeVar, Union
import sqlite3
import nosponse
DB_PATH = 'responses.sqlite3'

T = TypeVar
def response_to_list(response: Union[T, Sequence[T]]) -> List[T]:
    """
    'A': B があるとき
    B=[C, D, E, ...] -> [C, D, E, ...]
    B=C -> [C]
    """
    if isinstance(response, list):
        return list(response)
    else:
        return [response]

def load_responses() -> Dict[str, Any]:
    return nosponse.j_file2dic("responses.json")

def main():
    conn = sqlite3.connect(DB_PATH)
    json_data = load_responses()
    for msg, res in json_data.items():
        with conn as c:
            c.execute('insert into message values (?)', [msg])
        res = response_to_list(res)
        responses = [(msg, r) for r in res]
        with conn as c:
            c.executemany('''
                insert into response
                values (?, ?)
            ''', responses)

if __name__ == "__main__":
    main()
