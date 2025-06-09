# print("JuiceFS version:", juicefs.__version__)
"""
print(
    "Shared lib :",
    os.path.exists(os.path.join(os.path.dirname(juicefs_local.__file__), "libjfs.so")),
)
from juicefs_local import Client

print("Client OK →", Client(name="iosys", meta="sqlite3://./data/jfs.db").listdir("/"))
"""

import juicefs

jfs = juicefs.Client(
    "iosysfilesystem", token="7af3ac7e6a485dfbd49156ce886c5a999f986836"
)

print(jfs.listdir("/"))
# help(juicefs.Client)
