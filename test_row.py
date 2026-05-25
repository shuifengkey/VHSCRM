class RowProxy:
    def __init__(self, columns, row):
        self._columns = columns
        self._row = row
        self._dict = dict(zip(columns, row))
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        return self._dict[key]
        
    def keys(self):
        return self._dict.keys()

r = RowProxy(["id", "name"], [1, "John"])
print(r[0])
print(r["name"])
print(dict(r))
