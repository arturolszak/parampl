Parampl
Author: Artur Olszak
Institute of Computer Science, Warsaw University of Technology                                                                                          
Version: 2.0.0 (21.10.2018)

Copyright (c) 2018, Artur Olszak, Institute of Computer Science, Warsaw University of Technology
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARTUR OLSZAK BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


*** 1. Parampl ***

Parampl is a simple tool for parallel and distributed execution of AMPL programs. Parampl introduces explicit asynchronous execution of AMPL subproblems from within the program code. The mechanism allows dispatching subproblems to separate threads of execution, synchronization of  the threads and coordination of the results in the AMPL program flow. It is able to take advantage of multiple processing units while computing the solutions, as well as distribute the processing of tasks to multiple machines. A modeller is able to define complex optimization tasks in a decomposed way, taking advantage of the problem structure and formulate algorithms solving optimization problems as subtasks.


*** 2. Installation ***

Execute "parampl.py install" to generate the files required by Parampl:
- paramplsub
- paramplret
- paramplrsub
- paramplrret


*** 3. Design and use of Parampl ***

Let us consider a very simple AMPL program, which solves sequentially the same problem for two sets of parameters p1, p2 and stores the results in one vector res:

var x{i in 1..3} >= 0;

param res {i in 1..6};
param p1 {iter in 1..2};    param p2 {iter in 1..2};
param iter;

minimize obj:
   p1[iter] - x[1]^2 - 2*x[2]^2 - x[3]^2 - x[1]*x[2] - x[1]*x[3];

subject to c1:
   8*x[1] + 14*x[2] + 7*x[3] - p2[iter] = 0;

subject to c2:
   x[1]^2 + x[2]^2 + x[3]^2 -25 >= 0;

let p1[1] := 1000;     let p1[2] := 500;
let p2[1] := 56;       let p2[2] := 98;

for {i in 1..2} {
   let {k in 1..3} x[k] := 2;     # define the initial point.
   let iter := i;
   solve;
   for {j in 1..3} {              # store the solution
      let res[(i-1)*3 + j] := x[j];
   };
};

display res;


Individual calls of the solve command will block until the solution is calculated. Using Parampl, it is possible to solve multiple problems in parallel. Parampl is a program written in Python programming language, which is accessed from AMPL programs by calling two AMPL commands:

- paramplsub   - submits the current problem to be processed in a separate thread of execution and returns:

write ("bparampl_problem_" & $parampl_queue_id);
shell 'python parampl.py submit'; 


- paramplret   - retrieves the solution (blocking operation) of the first submitted task, not yet retrieved:

shell 'python parampl.py retrieve';
if shell_exitcode == 0 then {
  solution ("parampl_problem_" & $parampl_queue_id & ".sol");
  remove ("parampl_problem_" & $parampl_queue_id & ".sol");
}


Before calling these scripts, Parampl must be configured within the AMPL program - the solver to be used and the queueId should be set. The queueId is a unique identifier of the task queue, which is a part of the names of temporary files created by Parampl, which allows executing Parampl in the same working directory for different problems and ensures that the temporary problem, solution and jobs files are not overwritten. The options for the chosen solver should be set in the standard way, e.g.:

option  parampl_options  'solver=ipopt';
option  parampl_queue_id  'powelltest';
option  ipopt_options  'mu_init=1e-6 max_iter=10000';


The paramplsub script saves the current problem to a .nl file (using AMPL command write) and executes Parampl with the parameter submit. When executed with the parameter submit, Parampl generates a unique identifier for the task, the generated .nl file is renamed to a temporary file, and the solver is executed in a separate process passing the .nl file to it. The tasks submitted in this way are executed in parallel in separate processes. After calculating the solution, the solver creates a solution (.sol) file with the file name corresponding to the temporary problem file passed to the solver upon execution.

Information about the tasks being currently processed by Parampl is stored in the jobs file - new tasks are appended to this file. The file simply stores the list of the task identifiers being currently executed (jobs that have been submitted and have not yet been retrieved):

2 3 4 5


The temporary file names for the problem (.nl) and solution (.sol) files are composed of the queueId and the task identifier. The jobs file name also contains the queueId, so multiple problems may be solved using Parampl at the same time as long as the queueId value is different for each of them.

The paramplret script executes Parampl with the parameter retrieve, which is a blocking call, waiting for the first submitted task from the jobs file (not yet retrieved) to finish. The solution file is then renamed to the .sol file known by the paramplret script and is then passed to AMPL using AMPL command solution. At this point, the temporary .nl file is deleted, and the task id is removed from the jobs file. After calling the script paramplret, the solution is loaded to the main AMPL program flow as if the solve command was called.

When the solver generates the solution file, the paramplret command does not immediately load the solution back to AMPL. Depending on the solver and the problem size, the file generation may take more time, and the file might be incomplete if the AMPL solution command is called immediately after the solution file is created. The blocking call parampl retrieve does not wait for the solution file itself to be generated, but for the notification (.not) file which is created after the solver process terminates. Calling Parampl with parameter submit does not directly run the solver process, but creates another instance of Parampl (executed in background) which executes the solver and generates the notification (.not) file after the solver process returns. This ensures that the solution file is complete before reading it back to AMPL. The logic of Parampl is presented below:

parampl submit:
  jobs = loadJobsFromFile("parampl_jobfile_queueId")
  taskId = generateNextTaskId(jobs)
  jobs.append(taskId)
  saveJobsToFile("parampl_jobfile_queueId", jobs)
  rename("parampl_problem_queueId.nl", "parampl_job_queueId_taskId.nl")
  executeInBackground("parampl executeSolver queueId taskId")
  # "submit" terminates, but "parampl executeSolver"
  # is still being executed in the background

parampl retrieve:
  jobs = loadJobsFromFile("parampl_jobfile_queueId")
  taskId = jobs.getAndRemoveFirst()
  saveJobsToFile("parampl_jobfile_queueId", jobs)
  waitForFile("parampl_job_queueId_taskId.not")  # blocking
  rename("parampl_job_queueId_taskId.sol", "parampl_problem_queueId.sol")
  delete("parampl_job_queueId_taskId.nl")
  delete("parampl_job_queueId_taskId.not")

parampl executeSolver:
  # execute the solver and wait until the solver process returns:
  execBlocking("solver parampl_job_queueId_taskId.nl -AMPL")
  # generate notification file after the solver returns:
  generateNotfiticationFile("parampl_job_queueId_taskId.not")


The sequential problem presented before may be run in parallel as follows:

for {i in 1..2} {
    # Define the initial point.
    let x[1] := 2;
    let x[2] := 2;
    let x[3] := 2;

    let iter := i;

    # execute solver (non blocking execution):
    commands paramplsub;
};

# the tasks are now being executed in parallel...

for {i in 1..2} {
    # retrieve solution from the solver:
    commands paramplret;

    # store the solution
    for {j in 1..3} {
        let res[(i-1)*3 + j] := x[j];
    };
};

In the above scenario, both problems are first submitted to Parampl, which creates a separate process for solving each of them (parallel execution of the solvers). In the second loop, the solutions for both subtasks are retrieved back to AMPL and may be then processed.


*** 4. Distributed Parampl ***

As for very complex problems, solving them on one machine might be not sufficient, and, in practice, memory is often the limiting resource, Parampl is also able to execute solvers for subproblems on remote machines. However, the modeler should be aware that the subproblems executed on remote machines should be relatively long compared to the time of sending the tasks and retrieving the solution to/from the remote machines. Even within a local network, the overhead is significantly more prominent compared to running Parampl locally. The remote executions were implemented only for Unix-based operating systems - SSH protocol is used to reach the remote machines) - ssh and scp programs (OpenSSH). It is required that the users are authenticated using keys (the password does not have to be provided upon every remote execution and copy operation). To distribute the execution to remote machines, two additional AMPL scripts are provided:

- paramplrsub   - submits the current problem for execution on a remote machine and returns:

write ("bparampl_problem_" & $parampl_queueId);
shell 'python parampl.py rsubmit'; 


- paramplrret   - retrieves the solution (blocking operation) of the first submitted task from a remote machine, not yet retrieved:

shell 'python parampl.py rretrieve';
if shell_exitcode == 0 then {
  solution ("parampl_problem_" & $parampl_queueId & ".sol");
  remove ("parampl_problem_" & $parampl_queueId & ".sol");
}


Both of the above scripts perform the same operations as the corresponding paramplsub and paramplret commands, but Parampl is executed with parameters rsubmit and rretrieve respectively. Calling Parampl with parameter rsubmit moves the problem file to the remote machine and calls Parampl with parameter submit on the remote machine, whereas parameter rretrieve causes execution of parampl retrieve on the remote machine and moves the retrieved solution file to the local machine, which is then ready to be loaded to AMPL.

The parampl_options, parampl_queue_id options, as well as the solver options should be set in AMPL, and additionally, Parampl requires three configuration files for distributed execution:

- parampl_cluster_queueId (queueId is the identifier of the task queue) - specifies the machines of the cluster - the machines are defined in separate lines. Each line contains three values separated by a white character: the hostname or the IP address of the remote machine, the user name on the remote machine, on which behalf Parampl will be executed and the working directory on the remote machine - this should be the path where the Parampl program is located. New tasks are submitted to the machines according to the round-robin strategy. The exemplary cluster definition is presented below:

#hostname	username	dir
ux1		aolszak		/home/users/s/aolszak/parampl
ux3		aolszak		/home/users/s/aolszak/parampl
ux5		aolszak		/home/users/s/aolszak/parampl
ux6		aolszak		/home/users/s/aolszak/parampl


parampl_remote_queueId - contains three numbers separated by the space character: the index of the machine to which the next task will be submitted, the index of the machine from which the next paramplrret command should retrieve the solution and the number of the tasks being currently executed. When absent, this file with default values will be created automatically:

0 0 0

- parampl_envs_queueId - this file should contain the list of all environment variables (one variable name per line), which should be copied to the remote machines before the Parampl execution. Copying certain environment variables to the remote machines is essential because the environment variables mechanism is used for passing configuration to solvers, as well as the options of Parampl. That is why this file should always contain the variables parampl_options, parampl_queue_id and all options required by the solver. The exemplary content of this file:

parampl_options
parampl_queue_id
# this is a comment
ipopt_options


The listing below presents the logic of the distributed Parampl:

parampl rsubmit:
  machines = loadMachinesFromFile("parampl_cluster_queueId")
  (nextSub, nextRet, numTasks) = 
     readTaskInfoFromFile("parampl_remote_queueId")
     # default values (0, 0, 0), if the file does not exist
  envs = getEnvVarNamesFromFile("parampl_envs_queueId)
  scp("parampl_problem_queueId.nl", machines[nextSub])
  setEnvs(envs, machines[nextSub])
  ssh(machines[nextSub], "parampl submit")
  nextSub = mod(nextSub + 1, machines.count)
  numTasks = numTasks + 1
  saveTaskInfoToFile(nextSub, nextRet, numTasks,
      "parampl_remote_queueId")

parampl rretrieve:
  machines = loadMachinesFromFile("parampl_cluster_queueId")
  (nextSub, nextRet, numTasks) = 
     readTaskInfoFromFile("parampl_remote_queueId")
  envs = getEnvVarNamesFromFile("parampl_envs_queueId)
  setEnvs(envs, machines[nextRet])
  ssh(machines[nextRet], "parampl submit")  # blocking
  scp(machines[nextRet] + "/parampl_problem_queueId.sol", ".")
  nextRet = mod(nextRet + 1, machines.count)
  numTasks = numTasks - 1;
  saveTaskInfoToFile(nextSub, nextRet, numTasks,
      "parampl_remote_queueId")


Parampl is also capable to distribute subproblems to multiple machines sharing a common file system. In such cases, additional time may be saved as the problem file and the solution file do not have to be copied over the network. Even if the machines are located in the same local network, and the physical connection between them is very fast, copying larger files might cause significant delays, especially if the main problem is split into many small (in terms of calculation time) subproblems. In case of running Parampl in a directory shared between the machines, the shared_fs parameter should be set to true (if not specified, the default value for shared_fs is false).

option parampl_options='solver=ipopt shared_fs=true';

In case the value of shared_fs is true, Parampl will not copy the problem and solution files to the remote machines, assuming that all the file system operations are immediately propagated on the remote machines and will only perform the remote execution of Parampl on the cluster nodes. Synchronized file systems which introduce delays between the file system operations and propagating them to other machines, may cause problems when using Parampl with shared_fs=true, because the instances of Parampl operate on the same files.

By default, the Unix shell (run in non-interactive mode) waits for all commands in the pipeline to terminate before returning and, with no tty, ssh connects to stdin/stdout/stderr of the shell process via pipes (which are then inherited by the child processes). Depending on the implementation, ssh may wait for them to close before exiting, which would result in remote task submission returning no sooner than the solver process terminates. In such a case, the tasks on the remote machines would be executed sequentially, not in parallel. Ssh may force a pseudo-tty allocation (ssh -t), in which case the shell will return immediately after the remote call "parampl submit" returns. However, the solver process, which is supposed to continue running in the background, would then receive the SIGHUP signal and terminate (when the parent shell process exits, the kernel sends the SIGHUP signal to its process group).
Parampl may detach the solver process from the shell (not terminating "parampl executeSolver ..." process running in the background) in several ways:

- Detaching "parampl executeSolver ..." using the screen program - when screen is used to detach the process from the shell, it doesn't matter whether the pseudo-tty allocation is forced or not (ssh -t).

- Forcing pseudo-tty allocation (ssh -t) and enabling the monitor mode by calling $set -m$ shell built-in. If the monitor mode is enabled, all processes are run in their own process groups.

- Forcing pseudo-tty allocation (ssh -t) and wrapping "parampl submit" execution in the nohup command call (nohup parampl submit). The nohup command will prevent sending the SIGHUP signal to the solver process.

- Redirecting pipes (of the remote call to "parampl submit") to /dev/null, so that the shell process returns immediately after "parampl submit" returns.

The method of creating the background process ("parampl executeSolver ...") is determined by the value of the unix_bkg_method Parampl option (option parampl_options), which may take one of the following values: 

- spawn_nowait - creates the subprocess in the background by calling the Python spawn function with the parameter os.P_NOWAIT

- screen - executes "screen -dm parampl executeSolver ...", and the screen process is created by the spawn function call with the parameter os.P_WAIT

The remote call behavior is configurable by setting the values of the following Parampl options: 

remote_submit_ssh_allocate_pseudo_tty
remote_submit_shell_monitor_mode_enabled
remote_submit_run_with_nohup
remote_submit_redirect_pipes_to_devnull

By default, the solver process is created without the use of the screen program, the pseudo-tty is not allocated by ssh, the monitor mode is not forced, nohup call is not used and stdin/strout/stderr of the remote call "parampl submit" are redirected to /dev/null.


*** 5. Important information ***

The Parampl scripts require Python to be accessible from the working directory.

