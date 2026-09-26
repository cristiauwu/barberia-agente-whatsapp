import sys
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q
print(q("SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='barber_servicios' ORDER BY ordinal_position")[1])
print(q("SELECT * FROM barber_servicios")[1])