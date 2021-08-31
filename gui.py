#!/usr/bin/env python3

#******************************************
#An graphic user interface for the Climate Chamber Controller.

#******************************************
__author__ = "Francesco Guescini"
__version__ = "0.0.0"
__lockfile__ = "lock"

#******************************************
#import stuff
import streamlit as st
import streamlit.components.v1 as components
import configparser, logging, time, sys, os, fasteners, multiprocessing, signal
import climatechambercontroller
from streamlit.report_thread import REPORT_CONTEXT_ATTR_NAME
from threading import current_thread
from contextlib import contextmanager
from io import StringIO
from copy import deepcopy

#******************************************
#page setup
#NOTE this must be the first streamlit command to be run
st.set_page_config(
    page_title = "Climate Chamber Controller",
    #page_icon = "",
    layout = "wide",
    initial_sidebar_state = "expanded")

#******************************************
#redirect standard streams
#https://discuss.streamlit.io/t/cannot-print-the-terminal-output-in-streamlit/6602
#https://github.com/BugzTheBunny/streamlit_logging_output_example/blob/main/app.py
@contextmanager
def st_redirect(src, dst):
    """Redirect a source to an output."""
    placeholder = st.empty()
    output_func = getattr(placeholder, dst)

    with StringIO() as buffer:
        old_write = src.write

        def new_write(b):
            if getattr(current_thread(), REPORT_CONTEXT_ATTR_NAME, None):
                buffer.write(b + "")
                output_func(buffer.getvalue() + "")
            else:
                old_write(b)

        try:
            src.write = new_write
            yield
            
        finally:
            src.write = old_write

#******************************************
#redirect standard output
#https://discuss.streamlit.io/t/cannot-print-the-terminal-output-in-streamlit/6602
#https://github.com/BugzTheBunny/streamlit_logging_output_example/blob/main/app.py
@contextmanager
def st_stdout(dst):
    """Redirect standard output."""
    with st_redirect(sys.stdout, dst):
        yield

#******************************************
#redirect standard error
#https://discuss.streamlit.io/t/cannot-print-the-terminal-output-in-streamlit/6602
#https://github.com/BugzTheBunny/streamlit_logging_output_example/blob/main/app.py
@contextmanager
def st_stderr(dst):
    """Redirect standard error."""
    with st_redirect(sys.stderr, dst):
        yield

#******************************************
#run program
#need to acquire lock on __lockfile__ to run the program
@fasteners.interprocess_locked(__lockfile__)
def runProgram(address, port, id, args, tolerance, refresh, verbose, force):

    #new climate chamber controller instance
    ccc = climatechambercontroller.climatechambercontroller(address, port, id)

    #start cycle
    ccc.cycle(args, tolerance, refresh, verbose, force)

    #finally clean up the lock file
    with open(__lockfile__, "w") as f:
        f.truncate(0)

    return

#******************************************
#stop climate chamber activities
def stop(ccc, container, verbose):

    #------------------------------------------
    #kill any running program
    with open(__lockfile__, "r+") as f:

        #open the lock file to read the PID
        pid = f.readline().strip()
        if pid != "":
            pid = int(pid)

            #kill the process
            container.text("killing process: %s"%pid)
            os.kill(pid, signal.SIGKILL)

            #clean up the lock file
            f.truncate(0)

    #------------------------------------------
    #stop the climate the chamber itself
    output = ccc.stop(verbose = verbose)

    if output[0] == "1":
        container.text("climate chamber stopped")                
    else:
        container.warning("there was an error while stopping the climate chamber: %s"%" ".join(output))

    return

#******************************************
#check whether the climate chamber is available
def isAvailable(ccc, force, forcestop, container, verbose):

    #------------------------------------------
    #program running

    #check whether the lock is available
    if not fasteners.InterProcessLock(__lockfile__).acquire(blocking = False):

        #get PID
        with open(__lockfile__, "r") as f:
            pid = f.readline().strip()
            program = f.readline().strip()
        
        if force:
            container.warning("a program is currently running with PID %s:  \n%s  \nforcing"%(pid, program))
            if forcestop:
                stop(ccc, container, verbose)
            return True
        else:
            container.warning("a program is currently running with PID %s:  \n%s  \nwill not proceed"%(pid, program))
            return False

    #------------------------------------------
    #not available
    elif not ccc.isAvailable():
        if force:
            container.warning("the climate chamber is currently busy  \nforcing")
            if forcestop:
                stop(ccc, container, verbose)
            return True
        else:
            container.warning("the climate chamber is currently busy  \nwill not proceed")
            return False
    #------------------------------------------
    #available
    return True

#******************************************
#climate chamber controller GUI
def main():

    #------------------------------------------
    #title
    st.sidebar.title("Climate Chamber Controller")
    #st.sidebar.write("An interface to control climate chambers.")

    #------------------------------------------
    #select a climate chamber from those available in the config file
    config = configparser.ConfigParser()
    config.read("ccc.conf")
    climatechamber = st.sidebar.selectbox("climate chamber", config.sections())

    #get climate chamber configuration parameters
    ccconfig = config[climatechamber]

    #------------------------------------------
    #draw climate chamber iframe
    if ccconfig["iframe"] != "":
        components.iframe(ccconfig["iframe"], height = int(ccconfig["iframe_height"]), scrolling = True)

    #------------------------------------------
    #redirect standard output and error to streamlit code
    #NOTE after the iframe
    with st_stdout("code"), st_stderr("code"):

        #------------------------------------------
        #add items below the iframe
        #NOTE at this time it is not yet possible to indicate the container maximum height
        #https://github.com/streamlit/streamlit/issues/2169
        container = st.container()

        #------------------------------------------
        #climate chamber controller instance

        #check address, port and ID are not empty
        if ccconfig["address"] == "" or ccconfig["port"] == "" or ccconfig["id"] == "":
            container.error("climate chamber address, port or ID invalid")
            return
        
        ccc = climatechambercontroller.climatechambercontroller(
            ccconfig["address"],
            int(ccconfig["port"]),
            int(ccconfig["id"]))
    
        #------------------------------------------
        #session state variables

        #dry air
        if "dryair" not in st.session_state:
            st.session_state.dryair = bool( int(ccc.getChannel( int(ccconfig["dry_air_channel"]) )[1]))
    
        #temperature
        if "temperature" not in st.session_state:
            st.session_state.temperature = float(ccc.getNominalTemperature()[1])

        #tempmin
        if "temperaturemin" not in st.session_state:
            st.session_state.temperaturemin = float(ccconfig["temperature_min"])

        #tempmax
        if "temperaturemax" not in st.session_state:
            st.session_state.temperaturemax = float(ccconfig["temperature_max"])

        #read programs settings
        programs = configparser.ConfigParser()
        programs.read("programs.conf")
            
        #number of cycles
        if "ncycles" not in st.session_state:
            st.session_state.ncycles = int(programs["DEFAULT"]["n_cycles"])

        #temperature 1
        if "temperature1" not in st.session_state:
            st.session_state.temperature1 = float(programs["DEFAULT"]["temperature_1"])

        #temperature 2
        if "temperature2" not in st.session_state:
            st.session_state.temperature2 = float(programs["DEFAULT"]["temperature_2"])

        #temperature 3
        if "temperature3" not in st.session_state:
            st.session_state.temperature3 = float(programs["DEFAULT"]["temperature_3"])

        #dwell time 1
        if "dwelltime1" not in st.session_state:
            st.session_state.dwelltime1 = int(programs["DEFAULT"]["dwell_time_1"])

        #dwell time 2
        if "dwelltime2" not in st.session_state:
            st.session_state.dwelltime2 = int(programs["DEFAULT"]["dwell_time_2"])

        #dwell time 3
        if "dwelltime3" not in st.session_state:
            st.session_state.dwelltime3 = int(programs["DEFAULT"]["dwell_time_3"])

        #tolerance
        if "tolerance" not in st.session_state:
            st.session_state.tolerance = float(programs["DEFAULT"]["tolerance"])

        #------------------------------------------
        #sidebar columns
        col1of2, col2of2 = st.sidebar.columns(2)

        #------------------------------------------
        #verbose mode
        verbose = col1of2.checkbox("verbose", value = bool( int(ccconfig["verbose"])))

        #------------------------------------------
        #force commands
        force = col2of2.checkbox("force", value = False)
        
        #==========================================
        #get status
        if col1of2.button("get status"):
    
            status = ccc.getStatus(verbose = verbose)[1]

            if status == "1":
                container.text("status: available")
            elif status == "2":
                container.text("status: run")
            elif status == "4":
                container.text("status: warning")
            elif status == "8":
                container.text("status: error")
            else:
                container.text("status: unknown (%s)"%status)

            container.text("actual temperature:  %.2f C"%float(ccc.getActualTemperature(verbose)[1]))
            container.text("nominal temperature: %.2f C"%float(ccc.getNominalTemperature(verbose)[1]))
            container.text("dry air: %s"%("ON" if int(ccc.getChannel(ccconfig["dry_air_channel"], verbose)[1]) else "OFF"))
            if os.path.getsize(__lockfile__):
                with open(__lockfile__, "r") as f:
                    container.text("program PID: %s"%f.readline().strip())
                    container.text("program: %s"%f.readline().strip())

        #==========================================
        #stop operations
        if col2of2.button("stop"):
            stop(ccc, container, verbose)

        #==========================================
        #toggle dry air
        if col2of2.button("toggle"):

            #------------------------------------------
            #check whether the climate chamber is available
            if isAvailable(ccc, force, False, container, verbose):

                #------------------------------------------
                #store initial value
                initialvalue = deepcopy(st.session_state.dryair)

                #------------------------------------------
                #send dry air setting to the climate chamber
                output = ccc.setChannel(
                    int(ccconfig["dry_air_channel"]),
                    int(not st.session_state.dryair),
                    verbose,
                    force)

                #give it some time
                time.sleep(0.2)

                if output[0] != "1" or len(output) != 1:
                    container.error("there was an error setting the dry air: %s"%" ".join(output))

                #------------------------------------------
                #read back dry air channel status
                st.session_state.dryair = bool( int(ccc.getChannel( int(ccconfig["dry_air_channel"]) )[1]))

                #------------------------------------------
                #check whether the dry air status has changed since the beginning
                if initialvalue == st.session_state.dryair:
                    container.error("there was an error setting the dry air: status unchanged")
                else:
                    container.text("dry air turned %s"%("ON" if st.session_state.dryair else "OFF"))

        #------------------------------------------
        #dry air status
        col1of2.markdown("dry air: **%s**"%("ON" if st.session_state.dryair else "OFF"))

        #==========================================
        #mode selection
        mode = st.sidebar.selectbox(
            "operation mode",
            ["set", "program"])

        #==========================================
        #set temperature
        if mode == "set":

            #settings
            settings = st.sidebar.form(key = "settings")
            st.session_state.temperature = settings.slider(
                "temperature",
                st.session_state.temperaturemin,
                st.session_state.temperaturemax,
                st.session_state.temperature,
                1.0,
                format = "%f C")

            #set
            if settings.form_submit_button(label = "set"):

                #------------------------------------------
                #check whether the climate chamber is available
                if isAvailable(ccc, force, True, container, verbose):

                    #------------------------------------------
                    #set nominal temperature
                    output = ccc.setNominalTemperature(st.session_state.temperature, verbose, force)

                    if output[0] == "1":
                        container.text("nominal temperature set to %.2f C"%st.session_state.temperature)
                    else:
                        container.error("there was an errorsetting the nominal temperature: %s"%" ".join(output))

                    #------------------------------------------
                    #start climate chamber
                    output = ccc.start(verbose, force)

                    if output[0] == "1":
                        container.text("climate chamber started")
                    else:
                        container.error("there was an error starting the climate chamber: %s"%" ".join(output))

        #==========================================
        #thermal cycling program
        elif mode == "program":

            #select program from those available in the program config file
            program = st.sidebar.selectbox("program", programs.sections())

            #------------------------------------------
            #program values
            if program == "default":
                #load sessions state values
                ncycles = st.session_state.ncycles
                temperature1 = st.session_state.temperature1
                temperature2 = st.session_state.temperature2
                temperature3 = st.session_state.temperature3
                dwelltime1 = st.session_state.dwelltime1
                dwelltime2 = st.session_state.dwelltime2
                dwelltime3 = st.session_state.dwelltime3
                tolerance = st.session_state.tolerance

            else:
                #load values from programs config file
                ncycles = int(programs[program]["n_cycles"])
                temperature1 = float(programs[program]["temperature_1"])
                temperature2 = float(programs[program]["temperature_2"])
                temperature3 = float(programs[program]["temperature_3"])
                dwelltime1 = int(programs[program]["dwell_time_1"])
                dwelltime2 = int(programs[program]["dwell_time_2"])
                dwelltime3 = int(programs[program]["dwell_time_3"])
                tolerance = float(programs[program]["tolerance"])
            
            #------------------------------------------
            #program settings
            settings = st.sidebar.form(key = "settings")

            #number of cycles
            ncycles = settings.slider(
                "number of cycles",
                0,
                100,
                ncycles)
            settings.markdown("---")

            #step 1
            temperature1 = settings.slider(
                "temperature 1",
                st.session_state.temperaturemin,
                st.session_state.temperaturemax,
                temperature1,
                1.0,
                format = "%f C")
            dwelltime1 = settings.slider(
                "dwell time 1",
                0,
                60,
                dwelltime1,
                format = "%f minutes")
            settings.markdown("---")

            #step 2
            temperature2 = settings.slider(
                "temperature 2",
                st.session_state.temperaturemin,
                st.session_state.temperaturemax,
                temperature2,
                1.0,
                format = "%f C")
            dwelltime2 = settings.slider(
                "dwell time 2",
                0,
                60,
                dwelltime2,
                format = "%f minutes")
            settings.markdown("---")

            #final step
            temperature3 = settings.slider(
                "final temperature",
                st.session_state.temperaturemin,
                st.session_state.temperaturemax,
                temperature3,
                1.0,
                format = "%f C")
            dwelltime3 = settings.slider(
                "final dwell time",
                0,
                60,
                dwelltime3,
                format = "%f minutes")
            settings.markdown("---")

            #temperature tolerance
            tolerance = settings.slider(
                "tolerance",
                0.,
                1.,
                tolerance,
                format = "%f C")
            settings.markdown("---")

            #------------------------------------------
            #store values in session state
            if program == "default":
                st.session_state.ncycles = ncycles
                st.session_state.temperature1 = temperature1
                st.session_state.temperature2 = temperature2
                st.session_state.temperature3 = temperature3
                st.session_state.dwelltime1 = dwelltime1
                st.session_state.dwelltime2 = dwelltime2
                st.session_state.dwelltime3 = dwelltime3
                st.session_state.tolerance = tolerance

            #------------------------------------------
            #run program
            if settings.form_submit_button(label = "start"):

                #------------------------------------------
                #check whether the climate chamber is available
                if isAvailable(ccc, force, True, container, verbose):

                    #------------------------------------------
                    #launch program
                    programstring = \
                        "cycling %s times between %s C (%s') and %s C (%s') and finally going to %s C (%s')"%(
                            ncycles,
                            temperature1,
                            dwelltime1,
                            temperature2,
                            dwelltime2,
                            temperature3,
                            dwelltime3)
                    container.text(programstring)
                    
                    #------------------------------------------
                    #start dedicated process

                    #args
                    args = (
                        ccconfig["address"],
                        int(ccconfig["port"]),
                        int(ccconfig["id"]),
                        (
                            ncycles,
                            temperature1,
                            dwelltime1,
                            temperature2,
                            dwelltime2,
                            temperature3,
                            dwelltime3
                        ),
                        tolerance,
                        float(ccconfig["refresh"]),
                        verbose,
                        force)

                    #create process
                    p = multiprocessing.Process(target = runProgram, args = args)
                    p.start()
                    container.text("created process with ID %s"%p.pid)
                    with open(__lockfile__, "w") as f:
                        f.write( str(p.pid) + "\n")
                        f.write(programstring)

        #==========================================
        #version
        st.sidebar.markdown("---")
        st.sidebar.markdown('<a href="https://github.com/guescio/climate-chamber-controller/" style="font-size:12px;">version %s</a>'%__version__, unsafe_allow_html=True)

#******************************************
if __name__ == "__main__":

    #start the Climate Chamber Controller GUI
    main()
