import zipfile, os, sys

zf = zipfile.ZipFile(os.path.join(os.environ['TEMP'], 'lambda-deploy.zip'), 'w', zipfile.ZIP_DEFLATED)
count = 0
for root, dirs, files in os.walk('.'):
    for f in files:
        if f == '_zip.py':
            continue
        fp = os.path.join(root, f)
        zf.write(fp, os.path.relpath(fp, '.'))
        count += 1
zf.close()
size = os.path.getsize(os.path.join(os.environ['TEMP'], 'lambda-deploy.zip'))
print(f"Zipped {count} files, size: {size/1024/1024:.1f} MB")
