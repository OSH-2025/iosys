import juicefs
import os

# print("JuiceFS version:", juicefs.__version__)
print(
    "Shared lib :",
    os.path.exists(os.path.join(os.path.dirname(juicefs.__file__), "libjfs.so")),
)
from juicefs import Client

print("Client OK →", Client(name="myjfs", meta="sqlite3://./jfs/jfs.db").listdir("/"))


# help(juicefs.Client)
