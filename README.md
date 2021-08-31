# Climate Chamber Controller
*Climate Chamber Controller* (*CCC*) is a project developed to communicate with older and newer Voetsch and Weisstechnik climate chambers. If the climate chamber supports S!MPATI software, CCC is compatible with it.

# Setup

## Dependencies
CCC depends on three python packages, which are listed in `requirements.txt`. These are:
- [configparser](https://docs.python.org/3/library/configparser.html)
- [streamlit](https://docs.streamlit.io/)
- [fasteners](https://fasteners.readthedocs.io/)

These can be installed by running:
```
pip install -r requirements.txt
```

## Climate chamber parameters
In order to communicate with a climate chamber, this should be first of all connected to the local network.

Three parameters of the climate chamber configuration are then needed:
- **address**: the address of the climate chamber; this can be retrieved in the climate chamber *configuration* menu, under *network*;
- **port**: the climate chamber port (usually 2049);
- **ID**: the climate chamber ID (usually 1);
- **dry air channel**: the climate chamber channel used to switch the dry air on or off.

# Use
CCC allows communicating with climate chambers in three different ways.

## Python
At the core of CCC is the `climatechambercontroller` Python module. 
This module can be used from the command line or it can be imported into scripts.

For a full list of options, run the script without any options or using the `--help` flag:
```
python -m climatechambercontroller --help
```

For example, to get the climate chamber status, run:
```
python -m climatechambercontroller -a ADDRESS -p PORT -i ID --status
```

To set the climate chamber temperature to 20 C, run:
```
python -m climatechambercontroller -a ADDRESS -p PORT -i ID --settemp 20
```

To run a thermal cycling program going for 2 times from 15 C to 25 C and the finally to 20 C, each time for 5 minutes, run:
```
python -m climatechambercontroller -a ADDRESS -p PORT -i ID --cycle 2 15 5 25 5 20 5
```

To stop the climate chamber temperature, run:
```
python -m climatechambercontroller -a ADDRESS -p PORT -i ID --stop
```

## Graphic User Interface
A GUI has been developed using the [streamlit](https://docs.streamlit.io/) Python library.

In order to use the GUI, the climate chamber parameters need to be set in `ccc.conf`.
These include the climate chamber address, port, ID and dry air channel listed above, plus a few additional ones:
- **minimum temperature**: the lowest temperature (in Celsius) allowed to be set;
- **maximum temperature**: the highest temperature (in Celsius) allowed to be set;
- **refresh**: the refresh interval (in seconds) when checking the temperature in a program;
- **iframe**: an optional iframe to be included at the top of the page;
- **iframe height**: the height if the optional iframe (in pixels);
- **verbose**: to automatically enable or disable the verbose mode at startup.

A set of thermal cycling programs can be defined in `programs.conf`. The following parameters should be specified:
- `[name]`: the program name;
- `n_cycles`: the number of cycles;
- `temperature_1`: the first temperature (in Celsius) in the cycle;
- `dwell_time_1`: the interval (in minutes) for which the first temperature in the cycle should be maintained constant;
- `temperature_2`: the second temperature (in Celsius) in the cycle;
- `dwell_time_2`: the interval (in minutes) for which the second temperature in the cycle should be maintained constant;
- `temperature_3`: the final temperature (in Celsius) to be reached at the end of the cycling; this is usually the room temperature;
- `dwell_time_3`: the interval (in minutes) for which the final temperature at the end of the cycling should be maintained constant;
- `tolerance`: the tolerance (in Celsius) on the temperature measurement.

The GUI can be launched by running the command:
```
streamlit run gui.py
```
This will open a browser page on `localhost:8501`.


## Online GUI
The CCC GUI can be made available online. This has some practical advantages.
- Avoid clashes between users trying to control the same climate chamber at the same time.
- The climate chamber can be controlled from any computer, with some configurable restrictions:
  - restrict the access to a limited set of IPs;
  - use password protection.
- There is no need to run the CCC locally.


### Setup
In order to put the CCC GUI online, a host running [Docker](https://docs.docker.com/) is required.

The configuration of the online CCC GUI is based on [reverse-proxy](https://github.com/guescio/reverse-proxy/).

Once the reverse proxy is up and running, edit the CCC `.env` file and provide the `HOSTNAME`:
```
HOST = "HOSTNAME"
```

If you wish to apply password protection or restrict the range of allowed IPs, make sure that in `docker-compose.yml` the `allowed-ips@docker` and `auth@docker` Traefik middlewares are used. These are used in the default configuration. The authentication credentials and the allowed IPs are those set in the [reverse-proxy](https://github.com/guescio/reverse-proxy/) configuration.

Now get the CCC GUI up and running by using the command:
```
docker-compose up -d
```

That's it. Open `HOSTNAME/ccc` in a browser to use the CCC GUI.


# Documentation

- https://docs.streamlit.io/
- https://docs.docker.com/
- https://doc.traefik.io/traefik/
- https://doc.traefik.io/traefik/providers/docker/
