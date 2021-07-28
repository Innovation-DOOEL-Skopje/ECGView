import os


def clearcache(mydir):
    filelist = [ f for f in os.listdir(mydir) if f.endswith(".svg") or f.endswith(".png") ]
    for f in filelist:
        os.remove(os.path.join(mydir, f))
        
def clearcache_all(mydir):
    filelist = [ f for f in os.listdir(mydir)]
    for f in filelist:
        os.remove(os.path.join(mydir, f))