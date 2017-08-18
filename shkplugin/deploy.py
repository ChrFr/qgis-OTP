import os, shutil
import zipfile

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

path_self, fn_self = os.path.split(__file__)
zipped_dir = 'shkplugin'

EXCLUDE = [fn_self, zipped_dir, '.gitignore', 'config.txt']
EXLUDE_EXT = ['.pyc']

zip_file = os.path.join(path_self, 'shkplugin.zip')
tmp_p = os.path.join(os.path.join(path_self, zipped_dir))

if os.path.exists(tmp_p):
    shutil.rmtree(tmp_p)
if os.path.exists(zip_file):
    os.remove(zip_file)
    
os.mkdir(tmp_p)
for n in os.listdir(path_self):
    fp = os.path.join(path_self, n)
    if (n not in EXCLUDE and
        os.path.splitext(n)[1] not in EXLUDE_EXT):
        if os.path.isdir(fp):
            shutil.copytree(fp, os.path.join(tmp_p, n))
        else:
            shutil.copy2(fp, tmp_p)

zip_f = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED)
zipdir(zipped_dir, zip_f)
zip_f.close()

shutil.rmtree(tmp_p)