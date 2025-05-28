
---
在项目根目录下运行脚本。

## JuiceFs py SDK

```python
check_quota(self, path, repair=False, strict=False)
    Check the quota of a directory.


chmod(self, path, mode)
    Change the mode of a file.
 |
 |  chown(self, path, uid, gid)
 |      Change the owner and group id of a file.
 |
 |  clone(self, src, dst, preserve=False)
 |      Clone a file.
 |
 |  del_quota(self, path)
 |      Delete the quota of a directory.
 |
 |  exists(self, path)
 |      Check if a file exists.
 |
 |  get_quota(self, path)
 |      Get the quota of a directory.
 |
 |  getxattr(self, path, name)
 |      Get an extended attribute on a file.
 |
 |  info(self, path, recursive=False, strict=False)
 |      Get the information of a file or a directory.
 |
 |  link(self, src, dst)
 |      Create a hard link to a file.
 |
 |  list_quota(self)
 |      List the quota of all directories.
 |
 |  listdir(self, path, detail=False)
 |      Return a list containing the names of the entries in the directory given by path.
 |
 |  listxattr(self, path)
 |      List extended attributes on a file.
 |
 |  lstat(self, path)
 |      Like stat(), but do not follow symbolic links.
 |
 |  makedirs(self, path, mode=511, exist_ok=False)
 |      Create a directory and all its parent components if they do not exist.
|
 |  mkdir(self, path, mode=511)
 |      Create a directory.
 |
 |  open(self, path, mode='r', buffering=-1, encoding=None, errors=None)
 |      Open a file, returns a filelike object.
 |
 |  readlink(self, path)
 |      Return a string representing the path to which the symbolic link points.
 |
 |  remove(self, path)
 |      Remove a file.
 |
 |  removexattr(self, path, name)
 |      Remove an extended attribute from a file.
 |
 |  rename(self, old, new)
 |      Rename the file or directory old to new.
 |
 |  rmdir(self, path)
 |      Remove a directory. The directory must be empty.
 |
 |  rmr(self, path)
 |      Remove a directory and all its contents recursively.
 |
 |  set_quota(self, path, capacity=0, inodes=0, create=False, strict=False)
 |      Set the quota of a directory.
 |
 |  setxattr(self, path, name, value, flags=0)
 |      Set an extended attribute on a file.
 |
 |  stat(self, path)
 |      Get the status of a file or a directory.
 |
 |  status(self, trash=False, session=0)
 |      Get the status of the volume and client sessions.
 |
 |  summary(self, path, depth=0, entries=1)
 |      Get the summary of a directory.
 |
 |  symlink(self, src, dst)
 |      Create a symbolic link.
 |
 |  truncate(self, path, size)
 |      Truncate a file to a specified size.

 |  unlink(self, path)
 |      Remove a file.
 |
 |  utime(self, path, times=None)
 |      Set the access and modified times of a file.
 |
 |  walk(self, top, topdown=True, onerror=None, followlinks=False)
 |
 |  warmup(self, paths, numthreads=10, background=False, isEvict=False, isCheck=False)
 |      Warm up a file or a directory.
 |
 |  ----------------------------------------------------------------------
 |  Data descriptors defined here:
 |
 |  __dict__
 |      dictionary for instance variables (if defined)
 |
 |  __weakref__
 |      list of weak references to the object (if defined)
 ```