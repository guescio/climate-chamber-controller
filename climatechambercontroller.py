#!/usr/bin/env python3

#******************************************
#A module designed to communicate with Voetsch and Weisstechnik climate chambers using SIMSERV.

#******************************************
__author__ = "Francesco Guescini"
__version__ = "0.0.0"

#******************************************
#delimiter and carriage return as ASCII code
DELIM = b"\xb6"
CR = b"\r"

#******************************************
#import stuff
import socket, sys, logging, time

#******************************************
class climatechambercontroller:
    """Climate Chamber Controller is a module designed to communicate with Voetsch and Weisstechnik climate chambers using SIMSERV."""

    #******************************************
    def __init__(self, address, port, id):
        """Initialize climate chamber controller."""

        #set address, port and ID
        self.address = address
        self.port = port
        self.id = id

        #create stream socket
        self.client = None
        
        return

    #******************************************
    def connect(self, verbose=False):
        """Connect to the climate chamber."""

        try:
            self.client.connect((self.address, self.port))
        except:
            logging.error("there was an error while connecting to the climate chamber:\n%s"%sys.exc_info()[1])
            sys.exit(1)

        return

    #******************************************
    def encode(self, arglist):
        """Create SIMSERV command string."""
  
        commandstring = "".encode("ascii")
        for arg in arglist:
            commandstring += DELIM + arg.encode("ascii")

        return commandstring + CR

    #******************************************
    def decode(self, data):
        """Decode SIMSERV data."""
        return [item.decode().strip() for item in data.split(DELIM)]
    
    #******************************************
    def send(self, arglist, verbose=False, force=False):
        """Send command."""
    
        #connect
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(verbose)

        #encode command string
        commandstring = self.encode(arglist)

        #send command
        if verbose:
            logging.info("sending: %s"%" ".join(self.decode(commandstring)))
        self.client.send(commandstring)

        #get data
        data = self.client.recv(512)
        self.client.close()
        output = self.decode(data)

        #verbose
        if verbose:
            logging.info("received: %s"%" ".join(output))

        #check for errors
        if output[0] != "1":
            if output[0] == "-1":
                logging.error("the receipt string was empty")
            elif output[0] == "-2":
                logging.error("missing chamber ID")
            elif output[0] == "-3":
                logging.error("chamber ID is in an invalid range")
            elif output[0] == "-4":
                logging.error("chamber not present")
            elif output[0] == "-5":
                logging.error("unknown command ID")
            elif output[0] == "-6":
                logging.error("too few or incorrect parameters")
            elif output[0] == "-7":
                logging.error("no server")
            elif output[0] == "-8":
                logging.error("control variables etc. with this ID not found")
            elif output[0] == "-9":
                logging.error("error while executing commands")
            elif output[0] == "-10":
                logging.error("index error while executing the command")
            elif output[0] == "-11":
                logging.error("no command execution possible because no user is logged in (with encrypted communication only)")
            elif output[0] == "-12":
                logging.error("the user logged in to the SIMSERV does not have command execution priviliges")
            elif output[0] == "-13":
                logging.error("duplicate login (the user is attempting to log in himself back into the open session)")
            else:
                logging.error("undefined error")

        return output

    #******************************************
    def isAvailable(self, verbose=False):
        """Check climate chamber availability."""
        return True if self.send(["10012", str(self.id)], verbose)[1] == "1" else False
    
    #******************************************
    def stop(self, verbose=False):
        """Stop climate chamber."""
        #NOTE this is the same as setting digital channel 1 to 0 (off)
        return self.send(["14001", str(self.id), "1", "0"], verbose)

    #******************************************
    def getStatus(self, verbose=False):
        """Get climate chamber status."""
        return self.send(["10012", str(self.id)], verbose)

    #******************************************
    def getActualTemperature(self, verbose=False):
        """Get climate chamber actual temperature."""
        #NOTE apperently an additional argument is needed before the ID
        return self.send(["11004", "1", str(self.id)], verbose)

    #******************************************
    def getNominalTemperature(self, verbose=False):
        """Get climate chamber nominal temperature."""
        #NOTE apperently an additional argument is needed before the ID
        return self.send(["11002", "1", str(self.id)], verbose)

    #******************************************
    def setNominalTemperature(self, temperature, verbose=False, force=False):
        """Set climate chamber nominal temperature."""
        #NOTE apperently an additional argument is needed before the ID

        #------------------------------------------
        #check whether the climate chamber is available
        if not self.isAvailable():
            logging.warning("the climate chamber is currently busy")
            
            #force
            if force:
                logging.warning("forcing temperature setting")
                self.stop(verbose)
            else:
                logging.warning("will not set temperature")
                return ["0"]
        
        return self.send(["11001", "1", str(self.id), str(temperature)], verbose)

    #******************************************
    def getChannel(self, channel, verbose=False):
        """Get digital channel status."""
        #NOTE channel 1 is the climate chamber status (on/off)
        return self.send(["14003", str(self.id), str(channel)], verbose)

    #******************************************
    def setChannel(self, channel, value, verbose=False, force=False):
        """Set digital channel status."""
        #NOTE channel 1 is the climate chamber status (on/off)

        #------------------------------------------
        #check whether the climate chamber is available
        if not self.isAvailable():
            logging.warning("the climate chamber is currently busy")
            
            #force
            if force:
                logging.warning("forcing channel setting")
            else:
                logging.warning("will not set channel")
                return ["0"]
        
        return self.send(["14001", str(self.id), str(channel), str(value)], verbose)

    #******************************************
    def start(self, verbose=False, force=False):
        """Start climate chamber."""
        #NOTE this is the same as setting digital channel 1 to 1 (on)

        #------------------------------------------
        #check whether the climate chamber is available
        if not self.isAvailable():
            logging.warning("the climate chamber is currently busy")
            
            #force
            if force:
                logging.warning("forcing start")
                self.stop(verbose)
            else:
                logging.warning("will not start")
                return ["0"]

        return self.send(["14001", str(self.id), "1", "1",], verbose)

    #******************************************
    def __rampAndDwell__(self, temp, interval, tolerance=0.1, refresh=2.0, verbose=False):
        """Ramp to a temperature and dwell for a given interval.

        NOTE The time interval is measured in minutes.
        """
        
        #ramp to temperature
        if verbose:
            logging.info("ramping to %.2f C"%temp)
        self.setNominalTemperature(temp, verbose, force = True)
        self.start(verbose, force = True)
    
        #wait until temperature is reached (within tolerance)
        while abs( float(self.getActualTemperature()[1]) - temp) > tolerance:
            time.sleep(refresh)

        #dwell
        if verbose:
            logging.info("reached %.2f C"%float(self.getActualTemperature()[1]))
            logging.info("dwelling for %.0f\'"%interval)
        time.sleep(interval*60)

        return

    #******************************************
    def cycle(self, arglist, tolerance=0.1, refresh=2.0, verbose=False, force=False):
        """Thermal cycle.

        Thermal cycling is controlled entirely through this Python module.
        While the climate chamber itself may have the ability to run programs, this functionality is not used here.
        No programs are saved to nor loaded from the climate chamber.
        """

        #------------------------------------------
        #check whether the climate chamber is available
        if not self.isAvailable():
            logging.warning("the climate chamber is currently busy")
            
            #force
            if force:
                logging.warning("forcing the thermal cycling")
                self.stop(verbose)
            else:
                logging.warning("will not perform the thermal cycling")
                return ["0"]

        #------------------------------------------
        #set variables
        ncycles = int(arglist[0])
        temp1 = int(arglist[1])
        interval1 = int(arglist[2])
        temp2 = int(arglist[3])
        interval2 = int(arglist[4])
        temp3 = int(arglist[5])
        interval3 = int(arglist[6])

        logging.info("thermal cycling")
        logging.info("tolerance: %.2f C"%tolerance)

        #------------------------------------------
        #thermal cycle
        try:

            #cycle
            for ii in range(ncycles):
                
                logging.info("cycle %s"%ii)

                #step 1
                if interval1 > 0:
                    self.__rampAndDwell__(temp1, interval1, tolerance, refresh, verbose)

                #step 2
                if interval2 > 0:
                    self.__rampAndDwell__(temp2, interval2, tolerance, refresh, verbose)

            #final step
            if interval3 > 0:
                logging.info("final step")
                self.__rampAndDwell__(temp3, interval3, tolerance, refresh, verbose)
            
        except: #KeyboardInterrupt:
            logging.warning("thermal cycling interrupted")
            logging.warning("stopping climate chamber")
            self.stop(verbose)

        #------------------------------------------
        #finally stop
        self.stop(verbose)
    
        return

#******************************************
if __name__ == "__main__":

    #------------------------------------------
    #import stuff
    import argparse

    #------------------------------------------
    #logging setup
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    #------------------------------------------
    #input arguments
    parser = argparse.ArgumentParser(description="%prog [options]")

    #configuration
    parser.add_argument("-a", "--address", dest="address", type=str, required=True, help="climate chamber address")
    parser.add_argument("-p", "--port", dest="port", type=int, required=False, default=2049, help="climate chamber port")
    parser.add_argument("-i", "--id", dest="id", type=int, required=False, default=1, help="climate chamber ID")
    parser.add_argument("-t", "--tolerance", dest="tolerance", type=float, required=False, default=0.1, help="temperature tolerance [C]")
    parser.add_argument("-r", "--refresh", dest="refresh", type=float, required=False, default=2.0, help="refresh interval [s]")
    
    #other
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose mode")
    parser.add_argument("-f", "--force", dest="force", action="store_true", default=False, help="force command")

    #------------------------------------------
    #mutually excusive commands
    command_parser = parser.add_mutually_exclusive_group(required=True)

    #status (default): --status
    command_parser.add_argument("--status", "-s", dest="status", action="store_true", default=False, help="get status")

    #get temperature (actual and nominal): --gettemp
    command_parser.add_argument("--gettemp", dest="gettemp", action="store_true", default=False, help="get actual and nominal temperatures [C]")

    #set nominal temperature and start: --settemp <temperature>
    command_parser.add_argument("--settemp", dest="temp", type=float, default=None, help="set nominal temperature and start [C]")

    #get digital channel status
    command_parser.add_argument("--getchannel", dest="getchannel", type=int, default=None, help="get channel status")

    #set digital channel status
    command_parser.add_argument("--setchannel", dest="setchannel", nargs=2, default=None, help="set channel status: <channel> <status>")
    
    #start: --start
    command_parser.add_argument("--start", dest="start", action="store_true", default=False, help="start")

    #stop: --stop
    command_parser.add_argument("--stop", dest="stop", action="store_true", default=False, help="stop")

    #custom command: --command <values>
    command_parser.add_argument("--command", "-c", dest="command", nargs="+", default=None, help="custom command: command, ID, arguments")

    #cycle: --cycle <n> <t1> <i1> <t2> <i2> <t3> <i3>
    command_parser.add_argument("--cycle", dest="cycle", nargs=7, default=None, help="thermal cylcing: n, t1 [C], i1 ['], t2 [C], i2 ['], t3 [C], i3 [']")
        
    #------------------------------------------
    #parse input arguments
    args = parser.parse_args()
    
    #------------------------------------------
    #create climate chamber controller instance
    ccc = climatechambercontroller(args.address, args.port, args.id)

    #------------------------------------------
    #run

    #stop
    if args.stop:
        output = ccc.stop(args.verbose)

        if output[0] == "1":
            print("climate chamber stopped")
        else:
            logging.error("there was an error: %s"%" ".join(output))
    
    #status
    elif args.status:
        status = ccc.getStatus(args.verbose)[1]
        if status == "1":
            print("status: available")
        elif status == "2":
            print("status: run")
        elif status == "4":
            print("status: warning")
        elif status == "8":
            print("status: error")
        else:
            print("status: unknown (%s)"%status)
        print("available: %s"%ccc.isAvailable(args.verbose))
        print("actual temperature:  %.2f C"%float(ccc.getActualTemperature(args.verbose)[1]))
        print("nominal temperature: %.2f C"%float(ccc.getNominalTemperature(args.verbose)[1]))

    #get temperature (actual and nominal)
    elif args.gettemp:
        print("actual temperature:  %.2f C"%float(ccc.getActualTemperature(args.verbose)[1]))
        print("nominal temperature: %.2f C"%float(ccc.getNominalTemperature(args.verbose)[1]))

    #set nominal temperature and start
    elif args.temp is not None:

        #set nominal temperature
        output = ccc.setNominalTemperature(args.temp, args.verbose, args.force)

        if output[0] == "1":
            print("nominal temperature set")
        else:
            logging.error("there was an error: %s"%" ".join(output))
            sys.exit(1)

        #start
        output = ccc.start(args.verbose, args.force)

        if output[0] == "1":
            print("climate chamber started")
        else:
            logging.error("there was an error: %s"%" ".join(output))

    #get channel status
    elif args.getchannel is not None:
        output = ccc.getChannel(args.getchannel, args.verbose)

        if output[0] == "1":
            print("channel status: %s"%output[1])
        else:
            logging.error("there was an error: %s"%" ".join(output))

    #set channel status
    elif args.setchannel is not None:
        output = ccc.setChannel(args.setchannel[0], args.setchannel[1], args.verbose, args.force)

        if output[0] == "1":
            print("channel set")
        else:
            logging.error("there was an error: %s"%" ".join(output))

    #start
    elif args.start:
        output = ccc.start(args.verbose, args.force)

        if output[0] == "1":
            print("climate chamber started")
        else:
            logging.error("there was an error: %s"%" ".join(output))

    #custom command
    elif args.command is not None:
        
        #check number of arguments
        if len(args.command) < 2:
            logging.error("not enough arguments")
        else:
            output = ccc.send(args.command, args.verbose, args.force)

            #check whether the command was successful
            if output[0] == "1":
                print("command output: %s"%" ".join(output))
            else:
                logging.error("there was an error: %s"%" ".join(output))

    #thermal cycling
    elif args.cycle is not None:
        ccc.cycle(args.cycle, tolerance=args.tolerance, refresh=args.refresh, verbose=args.verbose, force=args.force)
