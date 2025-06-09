import juicefs_local
import os

# print("JuiceFS version:", juicefs.__version__)
print(
    "Shared lib :",
    os.path.exists(os.path.join(os.path.dirname(juicefs_local.__file__), "libjfs.so")),
)
from juicefs_local import Client

print("Client OK →", Client(name="iosys", meta="sqlite3://./data/jfs.db").listdir("/"))

#import juicefs

#jfs = juicefs.Client("iosysfilesystem")



# help(juicefs.Client)
