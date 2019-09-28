import sqlite3
import nosponse
DB_PATH = 'responses.sqlite3'

def response_to_list(response):
    """
    'A': B があるとき
    B=[C, D, E, ...] -> [C, D, E, ...]
    B=C -> [C]
    """
    if isinstance(response, list):
        return response
    else:
        return [response]

def load_responses():
    return nosponse.j_file2dic(nosponse.responses_json_path)

def main():
    json_data = load_responses()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE response (msg, response)')
    for msg, res in json_data.items():
        res = response_to_list(res)
        responses = [(msg, r) for r in res]
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.executemany('''
                insert into response
                values (?, ?)
            ''', responses)

if __name__ == "__main__":
    main()
