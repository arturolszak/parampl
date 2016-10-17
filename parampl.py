#!/usr/bin/env python

# Parampl
# Author: Artur Olszak
# Institute of Computer Science, Warsaw University of Technology
# Version: 1.0.3 (21.05.2016)
#
# Copyright (c) 2013, Artur Olszak, Institute of Computer Science, Warsaw University of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL ARTUR OLSZAK BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



import os
import re
import sys
import time
import py_compile
import subprocess




# *** constants ***

PYTHON = "python"
PARAMPL_FILE = "parampl.py"
PARAMPL_FILE_COMPILED = "parampl.pyc"
PARAMPL_PYTHON_OPTIONS = "-S"

PARAMPL_PROBLEM_FILE_PREFIX = "parampl_problem"
PARAMPL_JOB_FILE_PREFIX = "parampl_jobfile"
PARAMPL_JOB_PROBLEM_FILE_PREFIX = "parampl_job"

#etension for the notification files (notification that the solver process terminated)
PARAMPL_NL_FILE_EXT = "nl"
PARAMPL_SOL_FILE_EXT = "sol"
PARAMPL_NOT_FILE_EXT = "not"

PARAMPL_PARAM_SUBMIT = "submit"
PARAMPL_PARAM_RETRIEVE = "retrieve"
PARAMPL_PARAM_RUN_SOLVER_WITH_NOTIFY = "runsolverwithnotify"
PARAMPL_PARAM_INSTALL = "install"
PARAMPL_PARAM_INSTALL_C = "installc"


PARAMPL_OPTIONS_VAR_NAME = "parampl_options"
PARAMPL_QUEUE_ID_VAR_NAME = "parampl_queue_id"

PARAMPL_OPTION_KEY_SOLVER = "solver"
PARAMPL_OPTION_KEY_UNIX_BKG_METHOD = "unix_bkg_method"



# *** default configuration ***

PARAMPL_CONF_SHARED_FS_DEFAULT = False

PARAMPL_CONF_UNIX_BKG_METHOD_SPAWN_NOWAIT = "spawn"
PARAMPL_CONF_UNIX_BKG_METHOD_SCREEN = "screen"
#PARAMPL_CONF_UNIX_BKG_METHOD_DEFAULT = PARAMPL_CONF_UNIX_BKG_METHOD_SCREEN
PARAMPL_CONF_UNIX_BKG_METHOD_DEFAULT = PARAMPL_CONF_UNIX_BKG_METHOD_SPAWN_NOWAIT

PARAMPL_CONF_NOT_FILE_RECHECK_WAIT_TIME = 0.01

PARAMPL_CONF_IO_OP_RETRIES = 10
PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME = 0.1



# *** parampl scripts ***

PARAMPLSUB_FILE = "paramplsub"
PARAMPLSUB_CONTENT = \
"""write ("b""" + PARAMPL_PROBLEM_FILE_PREFIX + """_" & $""" + PARAMPL_QUEUE_ID_VAR_NAME + """);
shell '""" + PYTHON + """ """ + ("" if (len(PARAMPL_PYTHON_OPTIONS) == 0) else (PARAMPL_PYTHON_OPTIONS+" ")) + __file__ + """ """ + PARAMPL_PARAM_SUBMIT + """';"""

PARAMPLRET_FILE = "paramplret"
PARAMPLRET_CONTENT = \
"""shell '""" + PYTHON + """ """ + ("" if (len(PARAMPL_PYTHON_OPTIONS) == 0) else (PARAMPL_PYTHON_OPTIONS+" ")) + __file__ + """ """ + PARAMPL_PARAM_RETRIEVE + """';
if shell_exitcode == 0 then {
    solution (\"""" + PARAMPL_PROBLEM_FILE_PREFIX + """_" & $""" + PARAMPL_QUEUE_ID_VAR_NAME + """ & ".""" + PARAMPL_SOL_FILE_EXT + """");
    remove (\"""" + PARAMPL_PROBLEM_FILE_PREFIX + """_" & $""" + PARAMPL_QUEUE_ID_VAR_NAME + """ & ".""" + PARAMPL_SOL_FILE_EXT + """");
}"""





def generateFiles():

    paramplsubFile = open(PARAMPLSUB_FILE, 'w')
    paramplsubFile.write(PARAMPLSUB_CONTENT)
    paramplsubFile.close()

    paramplretFile = open(PARAMPLRET_FILE, 'w')
    paramplretFile.write(PARAMPLRET_CONTENT)
    paramplretFile.close()




def compile():
    py_compile.compile(PARAMPL_FILE, PARAMPL_FILE_COMPILED)





class Parampl:


  def problemfile(self):
    return PARAMPL_PROBLEM_FILE_PREFIX

  def problemfile(self, queueId):
    return PARAMPL_PROBLEM_FILE_PREFIX + "_" + queueId

    

  def submit(self, queueId):
    jobNumber = 0

    if (os.path.isfile(PARAMPL_JOB_FILE_PREFIX + "_" + queueId)):
      try:
        jobfile = self.openFile(PARAMPL_JOB_FILE_PREFIX + "_" + queueId,'r')
      except IOError:
        sys.stdout.write("Error, could not open the job file.\n")
        sys.stdout.write("Did you use paramplsub?\n")
        sys.exit(1)
    else:
      jobNumber = 1

    if jobNumber == 0:
      m = re.match(r'(\d+)',jobfile.readline())
      while m:
        tempJobNumber = int(m.groups()[0])
        if jobNumber < tempJobNumber:
          jobNumber = tempJobNumber
        m = re.match(r'(\d+)',jobfile.readline())
      jobfile.close()
      jobNumber = jobNumber + 1

    if jobNumber == 0:
      sys.stdout.write("Error: Job not submitted.\n")
      sys.exit(1)
    
    self.renameFile(self.problemfile(queueId) + "." + PARAMPL_NL_FILE_EXT, PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_NL_FILE_EXT)


    #start the job:

    solverName = self.getSolverName()
    if solverName is None or solverName == "":
      sys.stdout.write("No solver name selected.\n")
      sys.stdout.write('To choose: option parampl_options "solver=xxx";\n\n')
      sys.exit(1)

    self.runSolverWithNotifyInBkg(solverName, queueId, jobNumber)

    jobfile = self.openFile(PARAMPL_JOB_FILE_PREFIX + "_" + queueId,'a')
    jobfile.write("%d\n" % (jobNumber))
    jobfile.flush()
    os.fsync(jobfile)
    jobfile.close()


    sys.stdout.write("Job %d submitted\n" % jobNumber)
    return jobNumber





  def retrieve(self,queueId):
    try:
      jobfile = self.openFile(PARAMPL_JOB_FILE_PREFIX + "_" + queueId,'r')
    except:
      sys.stdout.write("Error, could not open the job file.\n")
      sys.stdout.write("Did you use paramplsub?\n")
      sys.exit(1)
      
    m = re.match(r'(\d+)',jobfile.readline())
    if m:
      jobNumber = int(m.groups()[0])
    else:
      sys.stdout.write("Error, invalid job file.\n")
      sys.stdout.write("Did you use paramplsub?\n")
      sys.exit(1)

    restofstack = jobfile.read()
    jobfile.close()

    
    solReceived = False

    while solReceived == False:

      if (os.path.isfile(PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_NOT_FILE_EXT)):
        if (os.path.isfile(PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_SOL_FILE_EXT)):
          try:
            self.renameFile(PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_SOL_FILE_EXT, self.problemfile(queueId) + "." + PARAMPL_SOL_FILE_EXT)
            solReceived = True
          except (Exception, BaseException) as e:
            sys.stdout.write("Error, could not rename the solution file.\n")
            sys.stdout.write("Error({0}): {1}".format(e.errno, e.strerror))
            sys.exit(1)
        else:
          sys.stdout.write("Error, the notification file was created, but the solution file does not exists.\n")
          sys.exit(1)
      else:
          time.sleep(PARAMPL_CONF_NOT_FILE_RECHECK_WAIT_TIME)

    try:
      self.unlinkFile(PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_NL_FILE_EXT);
    except (Exception, BaseException) as e:
      sys.stdout.write("Error, could not delete the problem file.\n")
      sys.stdout.write("Error({0}): {1}".format(e.errno, e.strerror))
      sys.exit(1)

    try:
      self.unlinkFile(PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_NOT_FILE_EXT);
    except (Exception, BaseException) as e:
      sys.stdout.write("Error, could not delete the notification file.\n")
      sys.stdout.write("Error({0}): {1}".format(e.errno, e.strerror))
      sys.exit(1)



    if restofstack:
      try:
        sys.stdout.write("Updating the jobfile\n")
        jobfile = self.openFile(PARAMPL_JOB_FILE_PREFIX + "_" + queueId,'w')
      except (Exception, BaseException) as e:
        sys.stdout.write("Error, could not open the job file for writing.\n")
        sys.stdout.write("Error({0}): {1}".format(e.errno, e.strerror))
        sys.exit(1)
      jobfile.write(restofstack)
      jobfile.flush()
      os.fsync(jobfile)
      jobfile.close()
    else:
      sys.stdout.write("Removing the jobfile\n")
      self.unlinkFile(PARAMPL_JOB_FILE_PREFIX + "_" + queueId)

    sys.stdout.write("Retrieved stub\n")




  def openFile(self,fileName,mode):
    ioRetries = 0
    while ioRetries < PARAMPL_CONF_IO_OP_RETRIES:
      try:
        ioRetries = ioRetries + 1
        file = open(fileName,mode)
        return file
      except:
        if (ioRetries == PARAMPL_CONF_IO_OP_RETRIES):
          raise
        else:
          sys.stdout.write("Error opening file: " + fileName + ", mode: " + mode + ". Retrying #" + str(ioRetries) + " in " + str(PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME) + " sec... \n")
          time.sleep(PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME)


  def renameFile(self,old,new):
    ioRetries = 0
    while ioRetries < PARAMPL_CONF_IO_OP_RETRIES:
      try:
        ioRetries = ioRetries + 1
        os.rename(old, new)
        return file
      except:
        if (ioRetries == PARAMPL_CONF_IO_OP_RETRIES):
          raise
        else:
          sys.stdout.write("Error renaming file: " + old + " to: " + new + ". Retrying #" + str(ioRetries) + " in " + str(PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME) + " sec... \n")
          time.sleep(PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME)


  def unlinkFile(self,fileName):
    ioRetries = 0
    while ioRetries < PARAMPL_CONF_IO_OP_RETRIES:
      try:
        ioRetries = ioRetries + 1
        os.unlink(fileName);
        return file
      except:
        if (ioRetries == PARAMPL_CONF_IO_OP_RETRIES):
          raise
        else:
          sys.stdout.write("Error deleting file: " + fileName + ". Retrying #" + str(ioRetries) + " in " + str(PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME) + " sec... \n")
          time.sleep(PARAMPL_CONF_IO_OP_RETRY_WAIT_TIME)


  def getTask(self):
    """
    Read in the parampl_queue_id option to get the queueId
    """

    queueId=""
    queueId=os.getenv(PARAMPL_QUEUE_ID_VAR_NAME)
    return queueId




    
  def getSolverName(self):
    return self.getStringOption(PARAMPL_OPTION_KEY_SOLVER, "")




  def getStringOption(self, option, default=""):
    self.options = None
    options = os.getenv(PARAMPL_OPTIONS_VAR_NAME)    
    optionValue = default
  
    if options is not None:
      m = re.search(option + '\s*=*\s*(\S+)',options,re.IGNORECASE)
      if m:
        optionValue=m.groups()[0]
    else:
      optionValue = default

    optionValue = optionValue.strip()

    return optionValue


  def getBooleanOption(self, option, default=False):
    self.options = None

    options = os.getenv(PARAMPL_OPTIONS_VAR_NAME)    
    optionValue = default
  
    if options is not None:
      m = re.search(option + '\s*=*\s*(\S+)',options,re.IGNORECASE)
      if m:
        optionValue=m.groups()[0]
        if optionValue is not None and optionValue.lower() == "true":
          optionValue = True
        elif optionValue is not None and optionValue.lower() == "false":
          optionValue = False
        else:
          optionValue = default
    else:
      optionValue = default

    return optionValue


  def runSolverWithNotifyInBkg(self, solver, queueId, jobNumber):
    if os.name == "posix":
      paramplConfUnixBkgMethod = self.getStringOption(PARAMPL_OPTION_KEY_UNIX_BKG_METHOD, PARAMPL_CONF_UNIX_BKG_METHOD_DEFAULT)
      if paramplConfUnixBkgMethod != PARAMPL_CONF_UNIX_BKG_METHOD_SPAWN_NOWAIT and paramplConfUnixBkgMethod != PARAMPL_CONF_UNIX_BKG_METHOD_SCREEN:
        paramplConfUnixBkgMethod = PARAMPL_CONF_UNIX_BKG_METHOD_DEFAULT
      if paramplConfUnixBkgMethod == PARAMPL_CONF_UNIX_BKG_METHOD_SPAWN_NOWAIT:
        os.spawnvp(os.P_NOWAIT, sys.executable, (sys.executable, PARAMPL_PYTHON_OPTIONS, os.path.abspath(__file__),  PARAMPL_PARAM_RUN_SOLVER_WITH_NOTIFY, solver, queueId, str(jobNumber)))
      elif paramplConfUnixBkgMethod == PARAMPL_CONF_UNIX_BKG_METHOD_SCREEN:
        os.spawnvp(os.P_WAIT, "screen", ("screen", "-dm", sys.executable, PARAMPL_PYTHON_OPTIONS, os.path.abspath(__file__),  PARAMPL_PARAM_RUN_SOLVER_WITH_NOTIFY, solver, queueId, str(jobNumber)))
    elif os.name == "nt":
      os.spawnv(os.P_NOWAIT, sys.executable, (sys.executable, PARAMPL_PYTHON_OPTIONS, os.path.abspath(__file__),  PARAMPL_PARAM_RUN_SOLVER_WITH_NOTIFY, solver, queueId, str(jobNumber)))



  def runSolverWithNotify(self, solver, queueId, jobNumber):
    if os.name == "posix":
      os.spawnvp(os.P_WAIT, solver, (solver, PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber), "-AMPL"))
    elif os.name == "nt":
      #os.spawnv(os.P_WAIT, solver, (solver, PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber), "-AMPL"))
      subprocess.call([solver, PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber), "-AMPL"], shell=True);
    else:
      sys.stdout.write("Parampl should be executed under Unix or Windows operating system.\n");
      sys.exit(1)

    notifyFile = self.openFile(PARAMPL_JOB_PROBLEM_FILE_PREFIX + "_" + queueId + "_" + str(jobNumber) + "." + PARAMPL_NOT_FILE_EXT, 'w')
    notifyFile.flush()
    os.fsync(notifyFile)
    notifyFile.close()



USAGE =\
"""
Parampl v.1.0.3
Usage: python parampl.py args
  install               # creates all files required by parampl
  installc              # creates all files required by parampl (compiled)
  submit                # submit
  retrieve              # retrieve
  runSolverWithNotify   # runs the solver, creates the .not file when finished
"""

if __name__=="__main__":
  parampl = Parampl()

  if len(sys.argv) < 2:
    print(USAGE)
    sys.exit(1)

  if sys.argv[1].lower() == PARAMPL_PARAM_SUBMIT.lower():
    queueId = parampl.getTask()
    jobNumber = parampl.submit(queueId)
    
  elif sys.argv[1].lower() == PARAMPL_PARAM_RETRIEVE.lower():
    queueId = parampl.getTask()
    parampl.retrieve(queueId)
    
  elif sys.argv[1].lower() == PARAMPL_PARAM_RUN_SOLVER_WITH_NOTIFY.lower():
    solver = sys.argv[2]
    queueId = sys.argv[3]
    jobNumber = sys.argv[4]
    parampl.runSolverWithNotify(solver, queueId, jobNumber)

  elif sys.argv[1].lower() == PARAMPL_PARAM_INSTALL.lower():
    generateFiles()

  elif sys.argv[1].lower() == PARAMPL_PARAM_INSTALL_C.lower():
    compile()
    os.system(sys.executable + " " + PARAMPL_FILE_COMPILED + " " + PARAMPL_PARAM_INSTALL)

  else:
    print(USAGE)
    sys.exit(1)


