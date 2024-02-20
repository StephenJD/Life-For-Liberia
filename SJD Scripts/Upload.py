import subprocess
from pathlib import Path

def updateWebsite(webRootPath):
  ParmsAdd = ("add", ".")
  ParmsCommit = ("commit","-m", "Upload new content")
  ParmsPush = ("push", "origin", "main")
  Git = "git"
  subprocess.run([Git, *ParmsAdd], shell=False, cwd=webRootPath)
  subprocess.run([Git, *ParmsCommit], shell=False, cwd=webRootPath)
  subprocess.run([Git, *ParmsPush], shell=False, cwd=webRootPath)

webRootPath =  Path.cwd().parent
updateWebsite(webRootPath)
